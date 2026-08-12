# Catálogo de fuentes

Qué hay en el corpus, de dónde salió y por qué está. Este archivo y
`backend/ingestion/registry.py` deben contar lo mismo: el registry es la
verdad que ejecuta el código, este documento es la versión legible.

**Última verificación: 2026-08-12** (`ingestion.validate`: 701 unidades,
0 problemas · `rag.eval`: 8/8).

## Qué hay cargado hoy

| Norma | Materia | Unidades | Documentos incluidos | Estado del texto |
|---|---|---|---|---|
| **Ley 29733** — Protección de Datos Personales | `proteccion_datos` | 194 | Ley (51) + DS aprobatorio (4) + Reglamento DS 003-2013-JUS (139) | Consolidado (Editora Perú). Texto nativo, sin OCR |
| **Ley 29783** — Seguridad y Salud en el Trabajo | `sst_laboral` | 252 | Ley (113) + DS aprobatorio (2) + Reglamento DS 005-2012-TR (137) | Consolidado al 28/04/2022 según portada. Texto nativo |
| **Ley 27693** — Crea la UIF-Perú | `laft` | 21 | Ley (21) | ⚠ Escaneo, 4/4 páginas por OCR. Requiere cotejo |
| **Ley 30424** — Responsabilidad admin. de personas jurídicas | `anticorrupcion` | 30 | Ley (19 art. + 11 disposiciones) | ⚠⚠ Texto **original de 2016** + OCR 4/4 páginas |
| **ISO 37001:2016** — Antisoborno | `antisoborno` | 204 | Requisitos, cláusulas 1–10 (97) + Anexo A (107) | Traducción oficial. Texto nativo. Copyright ISO |

**Total: 701 unidades citables.** Una "unidad" es un artículo, una disposición
complementaria o una cláusula ISO — la granularidad a la que el asistente cita.

Los cinco PDFs de origen viven en `backend/data/raw/normativas/` y están
versionados, así que el corpus se puede reconstruir entero desde cero.

## Las dos fuentes que hay que mirar con cuidado

Esto es lo que más fácil se olvida, y es justo lo que importa en compliance.

### Ley 30424 está desactualizada, no incompleta

Se parseó completa: 19 artículos y 11 disposiciones, sin huecos. Lo que pasa es
que el PDF es el **texto original publicado el 21/04/2016**, anterior a sus
modificatorias (Ley 30835 de 2018, Ley 31740 de 2023).

Se nota en el propio nombre que lleva en el corpus: *"…por el delito de cohecho
activo transnacional"*. Ese era el alcance de 2016. La versión vigente cubre
bastante más que cohecho transnacional, así que **una respuesta sobre el ámbito
de aplicación de la 30424 puede quedarse corta sin que el sistema lo note**.

El asistente sí avisa: la nota viaja en `advertencias` con cada respuesta que
cite esta norma. Pero el aviso no corrige el contenido.

→ *Acción pendiente:* conseguir el texto consolidado (SPIJ) y reingerir.

### Ley 27693 y Ley 30424 vienen de escaneo

Ambas son escaneos de El Peruano sin capa de texto: las 4 páginas de cada una
pasaron por OCR (Tesseract, español). El OCR va bien —`ingestion.validate` no
detecta huecos ni duplicados en la numeración— pero puede haber errores de
reconocimiento dentro del cuerpo del artículo.

`extraccion.requiere_cotejo: true` lo marca por norma, y el frontend lo muestra
en el panel lateral con el icono de escaneo.

## Cómo se registra una fuente

El registro vive en `backend/ingestion/registry.py`, en la lista `REGISTRY`.
Cada entrada es un `NormaMeta`:

| Campo | Qué es | Ejemplo |
|---|---|---|
| `norma_id` | Identificador interno. Da nombre al JSON y prefija los IDs de unidad | `ley_29733` |
| `archivo` | Nombre del PDF en `data/raw/normativas/` | `ley_29733.pdf` |
| `tipo` | `ley` o `norma_tecnica` | `ley` |
| `numero` | Número oficial | `29733` |
| `nombre` | Nombre completo, tal como aparece en la fuente | `Ley de Protección de Datos Personales` |
| `materia` | Agrupa el corpus y alimenta el filtro de la interfaz | `proteccion_datos` |
| `entidad_reguladora` | Quién fiscaliza | `["ANPD", "MINJUSDH"]` |
| `parser` | `ley` (Título→Capítulo→Artículo) o `iso` (cláusulas decimales) | `ley` |
| `fecha_publicacion` | **Solo si se lee del documento.** Si no, `None` | `2016-04-21` |
| `url_fuente` | Igual: solo si es verificable | `None` |
| `metadata_verificada` | `False` mientras no se coteje con SPIJ / El Peruano | `False` |
| `notas` | Estado del texto y advertencias. **Se muestra al usuario final** | ver abajo |

### La regla que gobierna el registro

**Nada se afirma de memoria.** `fecha_publicacion` y `url_fuente` quedan en
`None` salvo que se lean del propio documento, y `metadata_verificada` deja
constancia de en qué estado está. En un producto de compliance una fecha
inventada es peor que una fecha ausente.

Hoy las cinco normas tienen `metadata_verificada: false`. Cotejarlas contra
SPIJ es trabajo pendiente y está pensado como tarea aparte de la ingesta.

### `notas` es el campo que llega al usuario

No es un comentario interno. `rag/answer.py` lo lee y, si contiene la palabra
"original", lo emite como advertencia junto a la respuesta:

```
Advertencias:
  ! Ley 30424: Texto ORIGINAL publicado el 21/04/2016, sin las modificatorias
    posteriores (p. ej. Ley 30835, Ley 31740). No usar como texto vigente.
```

Escribe `notas` pensando en que un abogado lo va a leer al pie de una respuesta.

## Lo que el registro todavía no captura

Tres cosas que hoy no tienen dónde guardarse, y que conviene añadir antes de
que el corpus crezca — porque reconstruirlas después, con cuarenta normas
cargadas, es mucho más caro que anotarlas al ingerir:

1. **Por qué esta norma está en el corpus.** Hoy se deduce de `materia`, que no
   es lo mismo. "La 29783 está porque el cliente tiene obligaciones de SST como
   empleador" es información que no sobrevive en la cabeza de nadie seis meses.

2. **Qué relación tiene con las demás.** Qué norma modifica a cuál, cuál
   reglamenta a cuál, cuál derogó a cuál. Hoy existe a medias: cada unidad
   guarda `modificatorias` parseadas de su propio texto, pero no hay relación a
   nivel de norma.

3. **Qué versión del texto es.** `notas` lo dice en prosa, que sirve para el
   aviso al usuario pero no para filtrar ni consultar.

Los tres son el mismo dato que necesita el **grafo de trazabilidad**. Ver
[GRAFO.md](GRAFO.md) para el esquema propuesto.

## Materias en uso

Las materias agrupan el corpus y son lo que el usuario filtra en la interfaz.
Añadir una nueva no requiere tocar el frontend: sale de `/api/normas`.

| Materia | Normas |
|---|---|
| `proteccion_datos` | Ley 29733 |
| `sst_laboral` | Ley 29783 |
| `laft` | Ley 27693 |
| `anticorrupcion` | Ley 30424 |
| `antisoborno` | ISO 37001 |

## Cobertura que falta

Del plan de producto original, sigue sin cargarse:

- **Reglamento de la Ley 30424** (DS 002-2019-JUS) — especialmente relevante
  porque define el modelo de prevención, que es la parte accionable de la ley.
- **Resoluciones SBS** de gestión de riesgos LA/FT — el corpus de LA/FT hoy son
  21 unidades, con diferencia el más flaco.
- **Texto consolidado de la Ley 30424** (ver arriba).

Para añadir cualquiera de ellos: [INGESTA.md](INGESTA.md).

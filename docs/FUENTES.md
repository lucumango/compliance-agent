# Catálogo de fuentes

Qué hay en el corpus, de dónde salió y por qué está. Este archivo y
`backend/ingestion/registry.py` deben contar lo mismo: el registry es la
verdad que ejecuta el código, este documento es la versión legible.

**Última verificación: 2026-08-27** (`ingestion.validate`: 824 unidades,
0 problemas · `rag.eval`: 12/12).

Ninguna norma está cotejada contra SPIJ. `metadata_verificada` es `false` en
las once.

## Qué hay cargado hoy

| Norma | Materia | Unidades | Documentos incluidos | Estado del texto |
|---|---|---|---|---|
| **Ley 29783** — Seguridad y Salud en el Trabajo | `sst_laboral` | 252 | Ley (113) + DS aprobatorio (2) + Reglamento DS 005-2012-TR (137) | Consolidado al 28/04/2022 |
| **ISO 37001:2016** — Antisoborno | `antisoborno` | 204 | Requisitos, cláusulas 1–10 (97) + Anexo A (107) | Traducción oficial. Copyright ISO |
| **DS 016-2024-JUS** — Reglamento de la Ley de Protección de Datos | `proteccion_datos` | 148 | Decreto (5) + Reglamento (143) | El Peruano, 30/11/2024 |
| **Ley 29733** — Protección de Datos Personales | `proteccion_datos` | 55 | Ley (51) + DS aprobatorio (4) | Consolidado (Editora Perú) |
| **Res. SBS 789-2018** — Sujetos obligados ante la UIF | `laft` | 45 | Resolución | Portal SBS, vigente a 04/2026 |
| **DL 1106** — Lucha contra el lavado de activos | `laft` | 33 | Decreto Legislativo | Consolidado |
| **Ley 30424** — Responsabilidad admin. de personas jurídicas | `anticorrupcion` | 33 | Ley | Concordado a 12/2024 (SPIJ) |
| **DL 1372** — Beneficiario final | `laft` | 19 | Decreto Legislativo | Consolidado |
| **Ley 27693** — Crea la UIF-Perú | `laft` | 18 | Ley | Consolidado al 01/10/2025 (SPIJ) |
| **DS 003-2019-EF** — Reglamento del DL 1372 | `laft` | 13 | Decreto (3) + Reglamento (10) | El Peruano, 08/01/2019 |
| **Ley 29038** — Incorpora la UIF a la SBS | `laft` | 4 | Ley | Consolidado |

**Total: 824 unidades citables** en 11 normas. Una "unidad" es un artículo, una
disposición complementaria o una cláusula ISO — la granularidad a la que el
asistente cita.

Los PDFs de origen viven en `backend/data/raw/normativas/` y están versionados,
así que el corpus se puede reconstruir entero desde cero.

## El formato SPIJ y por qué importa

La Ley 27693 se carga desde una **descarga concordada del SPIJ**, no desde el
diario oficial. Ese formato no trae el articulado una vez: trae el texto
original y, detrás, cada versión que lo fue sustituyendo, todas con el mismo
número y entrecomilladas.

**El corpus se queda siempre con la última**, que es la vigente. Sin ese
tratamiento el parser conservaba la primera, dejando el texto de 2002 en un
documento cuya portada dice *"Actualizado al 1 de octubre de 2025"* — un texto
ya sustituido presentado como vigente, y sin ninguna señal de serlo.

Se activa con `formato="spij"` en el registro. Para el diario oficial se deja
`"el_peruano"`, que es el valor por defecto.

## Las modificatorias absorbidas no se cargan aparte

Las leyes 28009, 28306 y 29038 modifican la 27693, y su articulado **ya vive
dentro del texto concordado**. Cargarlas además como normas propias duplicaría
los mismos artículos en dos redacciones distintas, y la recuperación devolvería
la vieja tan a menudo como la vigente.

Se registran como **relaciones en el grafo**, no como texto citable. La
excepción es la Ley 29038, que sí está cargada porque tiene contenido propio
—la adscripción de la UIF a la SBS— además de modificar la 27693.

## Lo que se excluye del corpus a propósito

**El reglamento de la Ley 29733 de 2013 (DS 003-2013-JUS).** Viene anexo en el
mismo PDF de la ley y eran 139 de sus 194 unidades. Lo derogó el DS
016-2024-JUS. Se excluye con `documentos_excluidos=["reglamento"]` en el
registry.

No se marca como "no vigente" y ya: el aviso llega después de que la
recuperación gastó una plaza en texto derogado. Una cita correcta de una norma
que no rige es más difícil de detectar que un "no lo sé".

**Las modificatorias absorbidas.** Ver la sección de arriba.

## Lo que hay que mirar con cuidado

**Nada del corpus está cotejado.** Las once normas tienen
`metadata_verificada: false`, y `fecha_publicacion` y `url_fuente` están en
`null` salvo donde se leyeron del propio documento. Nadie ha confirmado que lo
que citamos sea el derecho vigente.

**Ninguna norma viene ya de OCR.** La 27693 y la 30424 se sustituyeron por
texto concordado del SPIJ con capa nativa. `requiere_cotejo` está en `false` en
todo el corpus.

**Los PDF del SPIJ traen el texto original y detrás cada versión que lo
sustituyó.** El parser se queda con la última, tanto en artículos como en
disposiciones. Si al revisar aparece una redacción vieja, es un fallo del
parser, no del PDF.

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
| `formato` | `el_peruano` (por defecto) o `spij` — ver arriba | `spij` |
| `fecha_publicacion` | **Solo si se lee del documento.** Si no, `None` | `2016-04-21` |
| `url_fuente` | Igual: solo si es verificable | `None` |
| `metadata_verificada` | `False` mientras no se coteje con SPIJ / El Peruano | `False` |
| `notas` | Estado del texto y advertencias. **Se muestra al usuario final** | ver abajo |

### La regla que gobierna el registro

**Nada se afirma de memoria.** `fecha_publicacion` y `url_fuente` quedan en
`None` salvo que se lean del propio documento, y `metadata_verificada` deja
constancia de en qué estado está. En un producto de compliance una fecha
inventada es peor que una fecha ausente.

Hoy las ocho normas tienen `metadata_verificada: false`. Cotejarlas contra
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

## Campos de trazabilidad

Además de los anteriores, cada norma declara por qué está y con qué se
relaciona. Son el insumo del [grafo de trazabilidad](GRAFO.md), y la razón de
anotarlos al ingerir es que reconstruirlos después, con cuarenta normas
cargadas, es mucho más caro.

| Campo | Qué es |
|---|---|
| `por_que_relevante` | Una o dos frases: a quién obliga y a qué. **Obligatorio** para toda norma nueva |
| `estado_texto` | `consolidado`, `original` o `parcial`. Lo mismo que cuenta `notas`, pero como dato consultable |
| `consolidado_a` | Fecha a la que está actualizado el texto, si se lee del documento |
| `relaciones` | Lista de `Relacion(tipo, destino, nota, en_corpus)` |

Tipos de relación: `modifica_a` / `modificada_por`, `reglamenta_a` /
`reglamentada_por`, `deroga_a` / `derogada_por`, `sustituye_a`, `complementa_a`.

Las formas pasivas no sobran: **la norma que modifica suele ser justo la que no
está cargada**, así que la relación solo se puede anotar desde el lado que sí
tenemos. Una relación con `en_corpus: false` deja constancia del hueco — que la
Ley 30835 modifica a la 30424 se sabe, y anotarlo lo convierte en algo
consultable en vez de una frase enterrada en una nota.

El grafo actual (`GET /api/grafo`) son 10 nodos y 5 aristas, de los cuales
**tres nodos son normas que faltan**: Ley 30835, Ley 31740 y DS 002-2019-JUS,
las tres colgando de la Ley 30424.

ISO 37001 va deliberadamente sin relaciones: su conexión con la Ley 30424 es
real pero editorial, no normativa —ISO no modifica ni reglamenta una ley
peruana—, y anotarla exige decidir con la fuente delante qué se está afirmando.

## Materias en uso

Las materias agrupan el corpus y son lo que el usuario filtra en la interfaz.
Añadir una nueva no requiere tocar el frontend: sale de `/api/normas`.

| Materia | Normas |
|---|---|
| `laft` | Ley 27693, Ley 29038, DL 1106, DL 1372, DS 003-2019-EF, Res. SBS 789-2018 |
| `proteccion_datos` | Ley 29733, DS 016-2024-JUS |
| `sst_laboral` | Ley 29783 |
| `anticorrupcion` | Ley 30424 |
| `antisoborno` | ISO 37001 |

## Cobertura que falta

- **Reglamento de la Ley 30424** (DS 002-2019-JUS y DS 002-2025-JUS) — define
  el modelo de prevención.
- **ISO 37002** y el **régimen laboral de hostilidad y represalia** — lo mínimo
  para el agente de línea ética.
- **Código Penal y Código Procesal Penal**, en secciones acotadas: delitos
  económicos, delitos contra la administración pública, y la parte de prueba.
  Para el agente de investigación.
- **DL 1034** — libre competencia. Materia sin cubrir.
- **TUO de la Ley 27444** — la potestad sancionadora. La necesita el estimador
  de multas para graduar dentro del rango.
- **Normativa sectorial** — se carga por encargo, no de entrada.

Para añadir cualquiera: [INGESTA.md](INGESTA.md).

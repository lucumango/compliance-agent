# Asistente de Normativa y Compliance (Perú)

Responde consultas sobre normativa peruana **citando artículo por artículo**, a
partir de un corpus cerrado de 701 unidades extraídas de 5 documentos
normativos. Cuando el corpus no cubre la consulta, lo dice en vez de improvisar.

```
$ python -m rag.cli "¿Cuál es la multa máxima por una infracción muy grave?"

1. Monto máximo en UIT: ... hasta cien unidades impositivas tributarias [F1].
2. Límite según ingresos: no puede exceder del diez por ciento de los
   ingresos brutos anuales ... [F1].
3. Referencia temporal: la UIT vigente a la fecha en que se cometió la
   infracción ... [F6].

Fuentes:
  [F1] Ley 29733, Artículo 39  (similitud 0.757)
  [F6] Reglamento de la Ley 29733, Artículo 124  (similitud 0.677)
```

## Documentación

| Documento | Para qué |
|---|---|
| **[docs/SISTEMA.md](docs/SISTEMA.md)** | Cómo funciona de punta a punta y **dónde está el prompt del agente** |
| **[docs/FUENTES.md](docs/FUENTES.md)** | Qué normas hay cargadas, en qué estado, y cómo se registra una fuente |
| **[docs/INGESTA.md](docs/INGESTA.md)** | Paso a paso para cargar PDFs nuevos al corpus |
| [docs/PENDIENTE.md](docs/PENDIENTE.md) | Lo que falta, con el contexto para retomarlo |
| [docs/GRAFO.md](docs/GRAFO.md) | Grafo de trazabilidad entre normas |
| [docs/DATOS.md](docs/DATOS.md) | Esquema de BD para el historial de chats (propuesta) |
| [docs/DESIGN.md](docs/DESIGN.md) | Sistema de diseño y modo oscuro |
| [EJECUTAR.md](EJECUTAR.md) | Levantar el proyecto en local |
| [backend/DEPLOY.md](backend/DEPLOY.md) | Desplegar |

## Dónde vive el repo

El monorepo está espejado en **tres** sitios con el mismo contenido:

| Repo | Papel |
|---|---|
| `gitlab.com/lonelynode/compliance-agent` | **Principal** |
| `github.com/lucumango/compliance-agent` | Espejo |
| `gitlab.com/lonelynode/compliance-back` | Espejo — es el que despliega Vercel |

Empuja siempre a los tres, o divergirán:

```bash
git push origin main \
  && git push github main \
  && git push https://gitlab.com/lonelynode/compliance-back.git main
```

**El tercero tiene el nombre equivocado y es a propósito, por ahora.** Era el
repo del backend cuando el proyecto vivía en dos repositorios; el proyecto de
Vercel quedó conectado a él y no se ha repuntado todavía, así que se mantiene
sincronizado para que los despliegues sigan saliendo. Lo correcto es reconectar
Vercel a `compliance-agent` y dejar este de escribir.

> ⚠ **`github.com/lucumango/compliance-back` está obsoleto.** Se quedó en el
> commit `28e06ad` del 5 de agosto, con la estructura vieja de solo backend. No
> empujes ahí.

Antes el frontend y el backend vivían en repos separados, y el backend además
duplicado entre GitLab y GitHub. Eso ya costó tres despliegues fallidos: Vercel
clonaba el repo del backend y buscaba en él un frontend que no existía.

## Qué hace hoy

- **Chat con respuestas ancladas.** Cada afirmación normativa cita la etiqueta
  del artículo del que sale; el panel lateral abre el texto íntegro de cada uno.
- **Streaming.** Las citas aparecen a ~1 s y el texto empieza a escribirse
  enseguida, en vez de esperar los ~12 s de la respuesta completa.
- **Advertencias que viajan con la respuesta.** Si una fuente viene de un
  escaneo con OCR, o es un texto sin sus modificatorias, la respuesta lo declara.
- **Diagramas Mermaid** cuando la consulta es procedimental ("¿qué hago si…?").
  Para una consulta de definición sería ruido, así que primero se decide si toca.
- **Estimador de multas** por gravedad, parametrizado por la UIT vigente y con
  el artículo que fija cada rango.
- **Filtro por materia** sobre el corpus.

## Corpus

| Norma | Unidades | Notas |
|---|---|---|
| Ley 29733 — Protección de Datos Personales | 194 | Ley + DS aprobatorio + Reglamento |
| Ley 29783 — Seguridad y Salud en el Trabajo | 252 | Ley + DS aprobatorio + Reglamento |
| Ley 30424 — Responsabilidad admin. de PJ | 30 | ⚠ Texto original de 2016 · OCR |
| Ley 27693 — Crea la UIF-Perú | 21 | ⚠ OCR |
| ISO 37001:2016 — Antisoborno | 204 | Cláusulas 1–10 + Anexo A |

Detalle y advertencias por norma en **[docs/FUENTES.md](docs/FUENTES.md)**.

## Arranque rápido

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # o requirements-ingesta.txt para procesar PDFs
cp .env.example .env                       # y coloca tu clave de Google AI Studio

uvicorn api:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Sin interfaz: `python -m rag.cli "tu consulta"`.

## Verificación

```bash
python -m ingestion.validate    # 701 unidades, 0 problemas
python -m rag.eval              # 8/8 casos de recuperación
```

## El caso negativo es el que importa

Ante *"¿en cuántas horas debo notificar una brecha a la ANPD?"*, el sistema
responde que el corpus no lo contiene y remite al reglamento y a las directivas
de la ANPD. Un RAG sin esa restricción contesta "72 horas" copiando el GDPR,
que no es derecho peruano.

## Limitaciones

No es asesoría legal. La anonimización no reconoce nombres de persona. La API
no tiene autenticación. Los textos con OCR requieren cotejo. La lista completa
está en [docs/SISTEMA.md](docs/SISTEMA.md#limitaciones-conocidas).

## Estructura

```
backend/    API, ingesta de PDFs, capa RAG y corpus
frontend/   interfaz React
docs/       documentación del sistema
```

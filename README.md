# Asistente de Normativa y Compliance (Perú)

Responde consultas sobre normativa peruana **citando artículo por artículo**, a
partir de un corpus cerrado de 754 unidades extraídas de 8 documentos
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
| [docs/DEPLOY.md](docs/DEPLOY.md) | Desplegar en Vercel y Render |

## Dónde vive el repo

| Repo | Papel |
|---|---|
| `gitlab.com/lonelynode/compliance-agent` | **Principal** |
| `github.com/lucumango/compliance-agent` | Espejo |

```bash
git push origin main && git push github main
```

Ambas plataformas despliegan de este mismo repo, cada una con su carpeta:

| | Repo | Root Directory | Config en el repo |
|---|---|---|---|
| Frontend | `compliance-agent` | `./` | `vercel.json` |
| Backend | `compliance-agent` | `backend` | `render.yaml` |

> ⚠ **Los repos `compliance-back` están obsoletos** — el de GitHub congelado en
> el commit del 5 de agosto, el de GitLab sincronizado solo como parche
> temporal mientras Vercel apuntaba a él. No empujes a ninguno de los dos.

Al principio el frontend y el backend vivían en repos separados, y el backend
además duplicado entre GitLab y GitHub. Costó tres despliegues fallidos: Vercel
clonaba el repo del backend y buscaba dentro un frontend que no existía.

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

| Norma | Materia | Unidades | Estado del texto |
|---|---|---|---|
| **Ley 29783** — Seguridad y Salud en el Trabajo | `sst_laboral` | 252 | Consolidado al 28/04/2022 |
| **ISO 37001:2016** — Antisoborno | `antisoborno` | 204 | Traducción oficial |
| **Ley 29733** — Protección de Datos Personales | `proteccion_datos` | 194 | Consolidado |
| **DL 1106** — Lucha contra el lavado de activos | `laft` | 33 | Consolidado |
| **Ley 30424** — Responsabilidad admin. de personas jurídicas | `anticorrupcion` | 30 | ⚠⚠ Original de 2016 · OCR |
| **DL 1372** — Beneficiario final | `laft` | 19 | Consolidado |
| **Ley 27693** — Crea la UIF-Perú | `laft` | 18 | Consolidado al 01/10/2025 (SPIJ) |
| **Ley 29038** — Incorpora la UIF a la SBS | `laft` | 4 | Consolidado |

**Total: 754 unidades citables** en 8 normas.

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
python -m ingestion.validate    # 754 unidades, 0 problemas
python -m rag.eval              # 11/11 casos de recuperación
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

# Cómo funciona el sistema

Recorrido de una consulta de punta a punta, y dónde tocar cada cosa.

## En una frase

Convierte PDFs normativos en un corpus de unidades citables (artículo por
artículo), recupera las relevantes por similitud vectorial, y hace que el
modelo redacte la respuesta **usando solo esas unidades**, citando cada
afirmación. Si el corpus no cubre la consulta, lo dice en vez de improvisar.

## El recorrido de una consulta

```
Usuario escribe en el chat
   │
   ├─ 1. anonimizar.py      enmascara PII antes de que nada salga de la máquina
   │                        "DNI 45678912" -> "[DNI_1]"
   │
   ├─ 2. gemini.py          embed_query(consulta)  ->  vector de 3072 dims
   │                        (taskType RETRIEVAL_QUERY, distinto al del índice)
   │
   ├─ 3. retrieval.py       producto punto contra los 824 vectores del índice
   │                        -> las k unidades más parecidas (k=6 por defecto)
   │
   ├─ 4. answer.py          arma el prompt: reglas + FUENTES + consulta
   │                        y calcula las advertencias de las normas citadas
   │
   ├─ 5. gemini.py          generar_stream(prompt) -> fragmentos de texto
   │
   ├─ 6. anonimizar.restaurar()   devuelve la PII real a la respuesta
   │
   └─ 7. api.py             lo emite como SSE: primero las fuentes, luego el
                            texto fragmento a fragmento, luego el cierre
```

El diagrama Mermaid, si la consulta es procedimental, va en una **segunda
petición** a `/api/diagrama` una vez terminado el texto. Meterlo en el mismo
flujo duplicaba el tiempo total (12 s → 30 s) para algo que el usuario todavía
no está mirando.

## Dónde está el prompt del agente

Hay **dos** prompts en el sistema, y ninguno está en el frontend:

### 1. El prompt principal — `backend/rag/answer.py`, constante `_SISTEMA` (línea 21)

Es el que gobierna todas las respuestas del chat. Un f-string con dos huecos,
`{fuentes}` y `{consulta}`, que se rellenan en `answer.py:100` (modo normal) y
`answer.py:141` (modo streaming). Contiene las cinco reglas duras:

1. Cada afirmación normativa cita su etiqueta exacta (`[F1]`, `[F3]`…).
2. Si las fuentes no responden, decirlo explícitamente y no completar con
   conocimiento propio.
3. No dar asesoría legal.
4. Plazos, montos y porcentajes se transcriben literales, nunca se estiman.
5. Responder en español, estructurado.

**La regla 2 es la que hace que el producto sea usable en compliance.** Sin
ella, ante "¿en cuántas horas notifico una brecha a la ANPD?" el modelo
contesta "72 horas" copiando el GDPR, que no es derecho peruano.

Si cambias este prompt, corre `python -m rag.cli` con varias consultas antes de
dar nada por bueno: `rag.eval` **no** lo cubre — solo evalúa recuperación, que
ocurre antes de que el prompt exista.

### 2. El prompt del diagrama — `backend/rag/diagrama.py`, constante `_PROMPT` (línea 18)

Convierte una respuesta ya redactada en un flowchart de Mermaid. Recibe la
respuesta, no las fuentes: no puede introducir pasos nuevos. Devuelve
`NO_APLICA` si el texto no describe un procedimiento.

### Parámetros del modelo

En `rag/config.py`:

- `MODEL_GENERACION` — `gemini-3.5-flash` por defecto
- `MODEL_RAPIDO` — `gemini-3.5-flash-lite`, respaldo
- `MODEL_EMBEDDING` — `gemini-embedding-2`, 3072 dimensiones
- Temperatura **0.2** (`gemini.py:138`): en compliance interesa la fidelidad al
  texto recuperado, no la variedad.

Los tres se pueden sobrescribir por variable de entorno sin tocar código.
`MODELOS_GENERACION` es una cadena de respaldo: si el principal agota su cuota
(429), el cliente degrada al siguiente y marca el agotado durante 15 minutos,
en vez de gastar reintentos contra un modelo caído en cada petición.

## Por qué la recuperación funciona

Cada unidad se vectoriza con un `texto_para_embedding` que **antepone el nombre
de la norma y su ubicación jerárquica** al texto del artículo:

```
Ley de Protección de Datos Personales (Ley 29733) · Título VII —
INFRACCIONES Y SANCIONES ADMINISTRATIVAS · Artículo 39

Sanciones administrativas...
```

Repetir ese contexto es lo que permite recuperar el artículo con preguntas
formuladas *en términos de la ley* ("¿qué dice la ley de datos personales
sobre…?"), no solo con las palabras que el articulado usa por dentro.

El índice es un `numpy.ndarray` de 824 × 3072 normalizado al construirlo, así
que la similitud coseno es un producto punto. A esta escala una búsqueda
exhaustiva tarda menos de un milisegundo; migrar a pgvector o Qdrant tiene
sentido cuando el corpus crezca mucho o haya multi-tenancy, no antes.

## Autenticación

Se activa con la variable de entorno `API_KEY`. Si no está definida, la API
arranca abierta —lo que quieres en local— y lo avisa por consola.

Con ella puesta, todos los endpoints exigen la cabecera `X-API-Key` **salvo
`/api/salud`**, que las plataformas de despliegue sondean sin cabeceras. Se
suma un límite por IP en ventana deslizante (30 peticiones / 60 s por defecto,
configurable con `RATE_LIMIT_PETICIONES` y `RATE_LIMIT_VENTANA`).

Lo que esto resuelve y lo que no está en la cabecera de `backend/auth.py`. En
corto: **una clave compartida que viaja en el bundle del frontend es visible
para cualquiera que abra las herramientas de desarrollo.** Frena el abuso de
paso —bots, alguien que da con la URL— no a alguien decidido, y no hay usuarios
ni permisos. El punto de enganche para cuentas de verdad es `verificar_clave`.

El límite de uso vive en memoria y por proceso: con varias réplicas, cada una
lleva su cuenta. Para una sola instancia basta.

## Estructura del código

```
backend/
  api.py                FastAPI. Endpoints /api/consultar[/stream], /diagrama,
                        /multa, /normas, /regimenes, /grafo, /salud
  auth.py               clave compartida y límite por IP
  ingestion/
    extract.py          PDF -> texto. PyMuPDF, u OCR si la página es imagen
    parser.py           leyes: Título → Capítulo → Artículo + disposiciones
    iso_parser.py       ISO: cláusulas decimales + Anexo A
    registry.py         ← declaración de cada fuente del corpus
    ingest.py           orquesta todo -> data/parsed/<norma>.json
    validate.py         controles de calidad sobre el corpus
  rag/
    config.py           claves, modelos, rutas
    gemini.py           cliente HTTP de la API: embeddings y generación
    anonimizar.py       enmascara PII antes de llamar al modelo
    index.py            construye y carga el índice vectorial
    retrieval.py        búsqueda por similitud coseno
    answer.py           ← el prompt principal y la composición de la respuesta
    diagrama.py         ← el prompt del diagrama
    multas.py           estimador de multas parametrizado por UIT
    cli.py              chat en terminal
    eval.py             evaluación de recuperación
  data/
    raw/normativas/     los PDFs de origen (versionados)
    parsed/             el corpus estructurado, un JSON por norma
    index/              vectors.npy + unidades.json
    uit.json            valor de la UIT por año, con la norma que lo fija

frontend/src/
  App.jsx               chat, panel de fuentes, filtro por materia
  api.js                cliente HTTP, incluido el consumidor de SSE
  Mermaid.jsx           render del diagrama (securityLevel strict)
  CalculadoraMultas.jsx estimador por gravedad
  App.css               sistema de diseño
```

## Decisiones que conviene no deshacer sin querer

**OCR sobre escaneos con subrayado.** Los encabezados de artículo de la 27693 y
la 30424 van subrayados, y esa línea horizontal arruina el reconocimiento:
`Artículo 3º.-` se leía `lo 39.-`, perdiendo el límite del artículo.
`extract.py` detecta las líneas por morfología y las borra por *inpainting*
antes de pasar a Tesseract.

**Desambiguación por monotonicidad.** La numeración de artículos siempre crece.
Cuando una coincidencia rompe la secuencia —una referencia cruzada partida por
un salto de línea, o un artículo de otro código citado dentro de una
disposición modificatoria— se pliega al artículo anterior en vez de crear uno
falso. El mismo criterio recupera el ordinal `º` leído como dígito
(`Artículo 9º` → `92` → `9`).

**Metadatos conservadores.** Ver [FUENTES.md](FUENTES.md): nada se afirma de
memoria.

**Anonimización antes de la llamada.** La consulta puede traer datos reales del
caso; no necesitan salir del entorno para que el modelo responda una pregunta
normativa. Es una defensa de superficie: reconoce patrones estructurados (DNI,
RUC, correos, teléfonos, montos, tarjetas), **no nombres de persona**.

**El diagrama se dibuja con `securityLevel: "strict"`.** El código Mermaid lo
genera un modelo: no es contenido de confianza.

**La UIT es configuración, no constante.** Vive en `data/uit.json` con la norma
que fija cada valor. Una multa calculada con la UIT de otro año está mal.

## Verificación

| Comando | Qué comprueba | Estado (2026-08-27) |
|---|---|---|
| `python -m ingestion.validate` | Numeración sin huecos ni duplicados, texto de página filtrado, unidades vacías, citas presentes | **824 unidades, 0 problemas** |
| `python -m rag.eval` | 12 consultas de referencia recuperan el artículo que deben, cubriendo las materias del corpus | **12/12** |
| `npm run build` (frontend) | Compila | OK |
| `npm run lint` (frontend) | oxlint | Limpio |

Un control cruzado útil: el DS 003-2013-JUS declara en su preámbulo que el
reglamento tiene 3 disposiciones complementarias finales y 3 transitorias, y el
parser extrae exactamente 3 y 3.

**Lo que no está cubierto:** no hay pruebas unitarias (`pytest`) de ningún
módulo, y ninguna verificación automática toca los prompts ni la calidad de la
respuesta generada — solo la recuperación que la precede.

## Limitaciones conocidas

- **No es asesoría legal.** El corpus informa; un abogado valida.
- **La anonimización no reconoce nombres de persona.** "Juan Pérez" viaja al
  modelo tal cual. Hace falta un NER si eso importa para el caso de uso.
- **Fechas y URLs sin verificar:** `metadata_verificada: false` en las 11 normas.
  Nadie ha cotejado todavía el corpus contra SPIJ.
- **La autenticación es una clave compartida, no cuentas.** Va en el bundle del
  frontend, así que es visible en las herramientas de desarrollo. Y no
  distingue quién es quién.
- **Un solo régimen en la calculadora de multas:** protección de datos
  (Ley 29733, Art. 39). Los rangos de SST y LA/FT están en normas no cargadas.
- **`titulo` está truncado en buena parte de las 824 unidades.** El parser toma la
  primera línea *visual* del PDF, que corta a media frase. Hoy es latente —el
  frontend no lo muestra— pero está en el contrato de la API y en los
  embeddings de ISO.

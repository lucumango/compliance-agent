# Mantenimiento

Cómo se toca este código sin romperlo. Escrito para quien lo herede.

---

## Arrancar en local

Dos procesos, dos terminales.

```bash
# terminal 1 — API
cd backend
source .venv/bin/activate
uvicorn api:app --reload --port 8000

# terminal 2 — interfaz
npm --prefix frontend run dev
```

| | |
|---|---|
| Interfaz | <http://localhost:5173> |
| API | <http://127.0.0.1:8000> |
| Salud | <http://127.0.0.1:8000/api/salud> |
| Documentación de la API | <http://127.0.0.1:8000/docs> |
| Esquema OpenAPI | <http://127.0.0.1:8000/openapi.json> |
| Documentación del proyecto | `mkdocs serve` → <http://127.0.0.1:8000> (usa otro puerto: `-a 127.0.0.1:8001`) |

`/api/salud` es la comprobación rápida. Tiene que devolver `unidades_indexadas:
824` y `cuentas: true`. Si `cuentas` sale en `false`, falta `SUPABASE_URL` en el
`.env` y el login no aparecerá.

Sin interfaz: `python -m rag.cli "tu consulta"`.

---

## Los cinco comandos

```bash
python -m ingestion.ingest      # PDFs -> data/parsed/*.json
python -m ingestion.validate    # controles de calidad -> 0 problemas
python -m rag.index             # parsed -> vectores  (~6 min, gasta cuota)
python -m rag.eval              # recuperación -> 12/12
python -m rag.eval_prompt       # las reglas del prompt -> 6/6
```

`rag.eval_prompt` va aparte porque cada caso llama al modelo: gasta cuota y
tarda. Se corre al tocar `_SISTEMA`, al cambiar de modelo, y antes de un
despliegue que importe.

El orden importa y la dependencia es en cadena: tocar el parser obliga a
reingerir, reingerir obliga a reindexar, reindexar obliga a reevaluar.

`rag.index --solo-metadatos` reescribe `unidades.json` sin tocar los vectores.
Es lo que se usa al cambiar `registry.py` sin cambiar ningún texto: tarda
segundos en vez de minutos y no gasta cuota.

---

## Antes de cada push

```bash
python -m ingestion.validate    # si tocaste parser, registry o los PDFs
python -m rag.eval              # si tocaste recuperación, índice o embeddings
python -m rag.eval_prompt       # si tocaste el prompt o el modelo
npm --prefix frontend run lint
npm --prefix frontend run build # el build falla por cosas que dev no ve
mkdocs build --strict           # un enlace roto tumba el pipeline
```

No hay pruebas unitarias. `validate` y `eval` son lo único que hay, y solo
cubren el corpus y la recuperación.

**Empujar a los dos remotos.** El repositorio tiene dos y los despliegues
cuelgan de distintos:

```bash
git push origin main && git push github main
```

Vercel escucha a GitHub. Si solo se empuja a GitLab, el frontend se queda atrás
sin avisar de nada.

---

## Las trampas

Cosas que ya han roto el despliegue una vez.

**Un módulo nuevo en el backend hay que añadirlo al `Dockerfile`.** Lista los
ficheros uno a uno. El build sale verde y el contenedor muere al arrancar con
`ModuleNotFoundError`. Sin Docker en local se comprueba reconstruyendo a mano
lo que producen los `COPY` en una carpeta temporal e importando `api` desde
ahí.

**macOS no distingue mayúsculas y Linux sí.** Un `Historial.jsx` y un
`historial.js` conviven en local y rompen el build de Vercel. Los módulos de
datos van en minúscula, los componentes en mayúscula, y nunca con el mismo
nombre.

**Las variables `VITE_*` se hornean en el build.** Añadir una en Vercel no hace
nada hasta redesplegar, y hay que hacerlo **sin caché de build**.

**Todo lo que empieza por `VITE_` es público.** Va al bundle y se lee con las
herramientas de desarrollo. Ahí solo van la URL de Supabase, la clave `anon` y
la clave compartida de la API. La clave `service_role` no baja al navegador
bajo ningún concepto.

**`documento_fragmentos` no tiene índice ANN y es a propósito.** `ivfflat` y
`hnsw` admiten 2.000 dimensiones y el embedding tiene 3.072. Reducir la
dimensión haría incomparables los scores con los del corpus. A esta escala el
barrido exacto tarda milisegundos.

**El corpus no se toca desde Postgres.** Vive en `data/index/` como numpy y se
despliega ya construido. Los documentos del usuario sí están en Postgres. No
son el mismo almacén y no deben mezclarse.

---

## Añadir una norma al corpus

Los pasos completos están en [INGESTA.md](INGESTA.md). El resumen:

1. El PDF en `backend/data/raw/normativas/`, con el nombre que dicta la
   convención.
2. Una entrada en `registry.py`. **Nada se afirma de memoria**:
   `fecha_publicacion` y `url_fuente` se quedan en `None` salvo que se lean del
   propio documento. `cita_como` sí es obligatorio, o la respuesta saldrá con
   una cita inventada tipo "Ley 1372".
3. `ingest` → `validate` → `index` → `eval`.
4. Un caso de evaluación nuevo para la norma nueva. Sin él, nadie sabrá cuándo
   deja de recuperarse.

Si una modificatoria ya está absorbida en un texto consolidado, **no se carga
aparte**. Siempre la última versión, una sola vez.

---

## Añadir un endpoint

1. El modelo Pydantic de entrada y el de salida, con `Field` acotado.
2. `dependencies=PROTEGIDO`, salvo que haya una razón escrita para lo
   contrario. `/api/salud` es la única excepción, porque las plataformas lo
   sondean sin cabeceras.
3. `usuario_requerido` si el dato tiene dueño; `usuario_opcional` si solo
   mejora la respuesta.
4. Si escribe en Supabase, pasa el token del usuario. Nunca una credencial del
   servidor.
5. Códigos de error: 422 si el contenido no vale, 502 si falla el modelo o
   Supabase, 401 si falta la sesión, 503 si el servidor no tiene cuentas.

---

## Migraciones

`backend/supabase/*.sql`, numeradas, y se ejecutan en orden en el editor SQL de
Supabase. **Nunca se editan las ya aplicadas**: se añade una nueva.

Hoy van tres: `001_historial.sql`, `002_documentos.sql` y `003_gobernanza.sql`.
La tercera añade `mensajes.prompt_version` y la tabla `eventos_auditoria`, y
hay que ejecutarla para que el registro de auditoría funcione: sin ella la API
avisa por consola y sigue, que es lo correcto, pero no queda constancia de
nada.

Toda tabla nueva lleva `enable row level security` y su política en la misma
migración. Una tabla con RLS y sin política no se puede leer, lo que es un
fallo ruidoso y por tanto seguro. Una tabla sin RLS se lee entera desde
cualquier navegador, lo que es silencioso.

Después de cada migración, comprobar el aislamiento: sin sesión, cero filas en
todas las tablas.

---

## Claves

| Clave | Dónde vive | Quién la tiene |
|---|---|---|
| `GOOGLE_API_KEY` | `.env` local, variable en Render | Cada persona la suya |
| `SUPABASE_ANON_KEY` | `.env`, Render y Vercel | Pública por diseño |
| `API_KEY` | Render y Vercel | Compartida del despliegue |
| `service_role` | **Solo el panel de Supabase** | Nadie más |

Se rotan desde el panel de Supabase o de Google AI Studio, se actualizan en
Render y en Vercel, y se redespliega. Vercel además necesita el redespliegue
sin caché.

Una clave que ha pasado por un chat, un correo o una captura está quemada. Se
rota, no se reutiliza.

---

## Ritmo

**En cada cambio del parser o del corpus:** `validate` y `eval`.

**Cada mes:** `npm audit` y `pip-audit` a mano, hasta que estén en el CI.
Comprobar que la UIT del año sigue siendo la de `data/uit.json` —cambia cada
enero por decreto supremo—.

**Cada trimestre:** revisar si alguna norma cargada tiene modificatoria nueva.
El corpus no se entera solo. Y actualizar el estado de cotejo contra SPIJ en
[FUENTES.md](FUENTES.md).

**Cuando cambie el modelo de embeddings:** reindexar entero. Los vectores
viejos y los nuevos no son comparables, y la degradación es silenciosa: sigue
respondiendo, peor.

---

## Señales de que algo va mal

| Síntoma | Causa habitual |
|---|---|
| `unidades_indexadas: 0` | `data/index/` no llegó a la imagen |
| `cuentas: false` en producción | Faltan `SUPABASE_URL` o `SUPABASE_ANON_KEY` en Render |
| CORS bloqueado en el navegador | `ALLOWED_ORIGINS` no incluye el dominio de Vercel |
| 401 en todo | `VITE_API_KEY` no coincide con la `API_KEY` del backend |
| 502 "Error del modelo" | Cuota de Gemini agotada. Degrada solo, y si no quedan modelos, falla |
| Respuestas que citan bien pero contestan mal | Sube `k`. Con 11 normas, ocho plazas se llenan antes de llegar al artículo que enumera |
| El login parpadea al recargar | `resuelta` en `sesion.js` no está esperando a `getSession` |
| Todo se responde desde ISO 37001 | Falta corpus de esa materia, no falla el recuperador. Ver [CORRECCIONES.md](CORRECCIONES.md) |

---

## Lo que no hay

Y conviene saberlo antes de confiar en el sistema:

- Cero pruebas unitarias. `validate`, `eval` y `eval_prompt` son todo lo que hay.
- Cero análisis de dependencias en el CI.
- Las reglas 2 y 6 del prompt no tienen control automático: se leen a mano.
- Ninguna de las 11 normas está cotejada contra SPIJ.

El detalle está en [ESTANDARES.md](ESTANDARES.md), [GOBERNANZA.md](GOBERNANZA.md)
y [PENDIENTE.md](PENDIENTE.md).

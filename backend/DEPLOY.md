# Despliegue

## Por qué NO todo en Vercel/Netlify

Una consulta tarda **12 s** sin diagrama y **30 s** con diagrama (medido). Las
funciones serverless de Vercel Hobby y de Netlify cortan alrededor de los 10 s,
así que la mayoría de las consultas devolvería un timeout. Además el índice son
9 MB que hay que cargar en memoria: en un proceso largo se lee una vez al
arrancar, mientras que en serverless se recarga en cada arranque en frío.

El backend quiere ser un **proceso largo**, no una función.

## Arquitectura recomendada

```
Frontend (estático)  ->  Vercel        gratis, ideal para Vite/React
Backend  (contenedor) ->  Render/Railway/Fly  proceso largo, sin timeouts
```

### 1. Backend

El `Dockerfile` incluido solo empaqueta la capa de runtime: la ingesta de PDFs
(PyMuPDF, OpenCV, Tesseract) se queda fuera, porque el corpus se procesa en
local y se despliega ya indexado. La imagen lleva ~9 MB de datos y cuatro
dependencias de Python.

En Render:

1. New → Web Service → conecta el repo, raíz `backend/`, runtime Docker.
2. Variable de entorno: `GOOGLE_API_KEY` (y `ALLOWED_ORIGINS`, ver abajo).
3. Deploy. El plan gratuito duerme tras inactividad: el primer request tras la
   siesta tarda ~1 min.

Railway y Fly.io funcionan igual con el mismo Dockerfile.

### 2. Frontend

Conecta el repositorio en Vercel y **deja el Root Directory en la raíz** (`./`).

> **Si el Root Directory apunta a `backend/`, el despliegue falla así:**
>
> ```
> + uvicorn==0.52.1
> + uvloop==0.22.1
> sh: line 1: vite: command not found
> Error: Command "vite build" exited with 127
> ```
>
> Vercel encuentra `backend/requirements.txt`, deduce que es un proyecto
> Python, instala las dependencias del backend y luego intenta construir un
> frontend que en esa carpeta no existe. La pista es que instale paquetes de
> Python: si los ves, el Root Directory está mal.

El `vercel.json` de la raíz le dice todo lo que necesita:

```json
{
  "installCommand": "npm --prefix frontend ci",
  "buildCommand":   "npm --prefix frontend run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/" }],
  "ignoreCommand": "git diff --quiet HEAD^ HEAD -- frontend/"
}
```

Hay además un `package.json` en la raíz. No tiene dependencias: existe para que
Vercel reconozca la raíz como proyecto Node en vez de ponerse a adivinar. Sin
él, la raíz solo contenía `vercel.json` y la detección automática se iba al
backend.

**Comprueba también que en el panel, en *Build & Development Settings*, los
interruptores de Override estén apagados.** Si alguien escribió ahí un comando
a mano, ese gana y el `vercel.json` se ignora.

Dos cosas que hace ese fichero y conviene entender:

- **`rewrites`** manda cualquier ruta a `/`. Sin eso, recargar una URL que no
  sea la raíz devuelve 404: es una SPA y el enrutado vive en el cliente.
- **`ignoreCommand`** cancela el despliegue cuando el commit no tocó
  `frontend/`. Sin él, cada cambio en el corpus o en la documentación
  dispararía un despliegue del frontend idéntico al anterior. `git diff
  --quiet` sale con 0 si no hay cambios, que es justamente lo que Vercel
  interpreta como "no construyas".

Si prefieres poner *Root Directory* = `frontend` en el panel, también funciona:
en ese caso Vercel lee `frontend/vercel.json`, que está puesto y hace lo mismo
sin los prefijos. Solo uno de los dos ficheros se aplica — el del directorio
raíz configurado.

Configura `VITE_API_URL` en Vercel apuntando a la URL pública del backend, y
`VITE_API_KEY` con el mismo valor que la `API_KEY` del backend. Sin la primera
el frontend llama a `127.0.0.1:8000` y en producción falla.

**El backend en Render:** *Root Directory* = `backend`, runtime Docker. El
`Dockerfile` está ahí dentro y no necesita nada más.

## Antes de exponerlo al público

Dos cosas que hoy **bloquean** un despliegue abierto:

### La API ya tiene clave y límite de uso — configúralos

Define `API_KEY` en el backend y `VITE_API_KEY` en el frontend, con el mismo
valor. **Sin `API_KEY` la API arranca abierta** y cualquiera con la URL consume
tu cuota de Gemini.

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Todos los endpoints la exigen en la cabecera `X-API-Key` salvo `/api/salud`,
que Render y compañía sondean sin cabeceras. El límite por IP va aparte
(`RATE_LIMIT_PETICIONES`, `RATE_LIMIT_VENTANA`; por defecto 30/60 s).

Ten claro su alcance: la clave viaja en el bundle del frontend y es visible
para cualquiera que abra las herramientas de desarrollo. Sirve contra el abuso
de paso, no contra alguien decidido, y no hay usuarios ni permisos.

### ISO 37001 tiene copyright

El corpus incluye la traducción oficial completa, y la API devuelve el texto
íntegro de la cláusula en `fuentes[].texto`. Publicarlo es redistribución, y la
licencia del PDF es de usuario único. Opciones antes de exponerlo:

- excluir `iso_37001` del índice desplegado, o
- devolver solo la cita y un extracto corto, no la cláusula completa.

Sería irónico que una herramienta de compliance infringiera una licencia.

## Streaming (ya implementado)

30 s sin feedback era mucho, y lo que lo arregló fue el **streaming**:
`/api/consultar/stream` emite la respuesta por fragmentos con SSE y el diagrama
se pide aparte, en una segunda petición a `/api/diagrama`. El usuario empieza a
leer a los ~2 s en vez de esperar 30.

Es el endpoint que usa el frontend. `/api/consultar` sigue existiendo para
integraciones que prefieran una respuesta única.

Al desplegar detrás de un proxy, comprueba que no acumule la respuesta: el
endpoint ya manda `Cache-Control: no-cache` y `X-Accel-Buffering: no`, pero
algunos CDN necesitan además desactivar el buffering por configuración.

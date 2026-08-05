# Asistente de Normativa y Compliance (Perú) — Frontend

Interfaz de chat para consultar normativa peruana con respuestas ancladas a la
fuente. Backend: [compliance-back](https://github.com/lucumango/compliance-back).

## Qué hace

- Chat con la respuesta **en streaming**: las citas aparecen a los ~0.9 s y el
  texto empieza a escribirse a los ~2 s, en vez de esperar la respuesta entera.
- Panel de fuentes desplegable: cada cita abre el texto íntegro del artículo.
- Diagramas Mermaid cuando la consulta es procedimental.
- Estimador de multas por gravedad, parametrizado por la UIT vigente.
- Filtro por materia (protección de datos, SST, LA/FT, anticorrupción,
  antisoborno).

## Desarrollo

```bash
npm install
npm run dev          # http://localhost:5173
```

Requiere el backend corriendo en `http://127.0.0.1:8000`.

## Despliegue (Vercel)

```bash
npx vercel --prod
```

Define `VITE_API_URL` con la URL pública del backend. Sin esa variable el
frontend llama a `127.0.0.1:8000` y en producción falla.

## Notas de implementación

**El streaming usa `fetch` + `ReadableStream`, no `EventSource`.** La API
`EventSource` del navegador solo hace peticiones GET y no admite cabeceras
propias, lo que impediría enviar la consulta en el cuerpo y añadir
autenticación más adelante. El formato de mensajes sigue siendo SSE.

**El diagrama se pide aparte.** Necesita la respuesta completa para
estructurarla, así que generarlo dentro del stream duplicaba el tiempo total.
Va en una segunda petición, mientras el usuario ya está leyendo.

**Mermaid corre con `securityLevel: "strict"`** porque el código del diagrama
lo genera un modelo: no es contenido de confianza. Si el diagrama viene
malformado, se muestra el código en un desplegable y el resto de la respuesta
queda intacta.

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

## Diseño

Sigue el sistema de marca **EY** (ver `DESIGN.md`). Puntos que condicionan el
código:

- **Sin `border-radius`.** EY es angular; hay una regla global `* { border-radius: 0 }`
  para que ningún componente lo reintroduzca por descuido.
- **`#FFE600` nunca como texto sobre blanco** (contraste 2.2:1, no pasa WCAG AA).
  El amarillo se usa como *fondo* con texto `#161D23`, como borde, o como color
  de texto solo sobre la cabecera oscura.
- **Tipografía Nunito**, servida desde Google Fonts con `display=swap` para que
  el texto sea legible mientras carga. Sustituye a EYInterstate, que es
  propietaria y no se puede distribuir.
- **Iconos exclusivamente de `lucide-react`**, sin emojis.
- **Superficies oscuras en `#161D23`**, nunca negro puro.

La escala de gravedad de las infracciones (leve / grave / muy grave) reutiliza
los colores semánticos de riesgo del sistema —verde / naranja / rojo— en vez de
definir una paleta propia.

El diagrama Mermaid usa un tema derivado de la misma paleta: nodos en gris
claro con borde `#161D23`, y el amarillo reservado para los rombos de decisión,
donde funciona como fondo con texto oscuro encima.

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

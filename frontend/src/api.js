const BASE = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const CLAVE = import.meta.env.VITE_API_KEY ?? "";

/**
 * Cabeceras comunes. La clave solo se manda si está configurada: en local el
 * backend arranca sin API_KEY y no la pide.
 */
function cabeceras(extra = {}) {
  return CLAVE ? { ...extra, "X-API-Key": CLAVE } : extra;
}

async function pedir(ruta, opciones = {}) {
  const resp = await fetch(`${BASE}${ruta}`, {
    ...opciones,
    headers: cabeceras(opciones.headers),
  });
  if (!resp.ok) {
    // El backend devuelve {detail} en los errores; sin él, el status a secas.
    const cuerpo = await resp.json().catch(() => null);
    throw new Error(cuerpo?.detail ?? `Error ${resp.status}`);
  }
  return resp.json();
}

export const salud = () => pedir("/api/salud");
export const normas = () => pedir("/api/normas");
export const regimenes = () => pedir("/api/regimenes");
export const grafo = () => pedir("/api/grafo");

export const consultar = (consulta, materias) =>
  pedir("/api/consultar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      consulta,
      materias: materias?.length ? materias : null,
    }),
  });

export const calcularMulta = (regimen, gravedad) =>
  pedir("/api/multa", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ regimen, gravedad }),
  });

export const pedirDiagrama = (respuesta) =>
  pedir("/api/diagrama", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ respuesta }),
  });

/**
 * Consume el endpoint SSE llamando a `alEvento(nombre, datos)` por mensaje.
 *
 * Usa fetch + ReadableStream en vez de EventSource porque EventSource solo
 * hace GET y no admite cabeceras propias, lo que impediría enviar la consulta
 * en el cuerpo y, más adelante, añadir autenticación.
 */
export async function consultarStream(consulta, materias, alEvento, señal) {
  const resp = await fetch(`${BASE}/api/consultar/stream`, {
    method: "POST",
    headers: cabeceras({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      consulta,
      materias: materias?.length ? materias : null,
    }),
    signal: señal,
  });

  if (!resp.ok) {
    const cuerpo = await resp.json().catch(() => null);
    throw new Error(cuerpo?.detail ?? `Error ${resp.status}`);
  }

  const lector = resp.body.getReader();
  const decodificador = new TextDecoder();
  let pendiente = "";

  while (true) {
    const { done, value } = await lector.read();
    if (done) break;

    pendiente += decodificador.decode(value, { stream: true });

    // Los mensajes SSE se separan por una línea en blanco. El último trozo
    // puede llegar partido, así que se queda en el buffer hasta completarse.
    const mensajes = pendiente.split("\n\n");
    pendiente = mensajes.pop() ?? "";

    for (const mensaje of mensajes) {
      let nombre = "message";
      const datos = [];
      for (const linea of mensaje.split("\n")) {
        if (linea.startsWith("event:")) nombre = linea.slice(6).trim();
        else if (linea.startsWith("data:")) datos.push(linea.slice(5).trim());
      }
      if (!datos.length) continue;
      try {
        alEvento(nombre, JSON.parse(datos.join("\n")));
      } catch {
        // Un mensaje ilegible no debe cortar el resto del stream.
      }
    }
  }
}

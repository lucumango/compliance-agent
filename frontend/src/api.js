// Se le quitan las barras finales: pegar la URL del backend con la barra que
// añaden los paneles de despliegue al copiarla es lo normal, y dejarla produce
// //api/salud, que el servidor no reconoce como ruta y devuelve 404.
const BASE = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(
  /\/+$/,
  ""
);
const CLAVE = import.meta.env.VITE_API_KEY ?? "";

// Token de la sesión, puesto por `sesion.js` cada vez que cambia. Vive aquí y
// no en el estado de React porque estas funciones no son componentes.
let TOKEN = null;

export function fijarToken(token) {
  TOKEN = token || null;
}

/**
 * Cabeceras comunes. Dos credenciales distintas que no se sustituyen:
 *
 *   X-API-Key     — clave compartida del despliegue. Protege la cuota del
 *                   modelo. Solo si está configurada.
 *   Authorization — sesión del usuario. Dice QUIÉN pregunta, y es lo que
 *                   permite al backend buscar en sus documentos.
 */
function cabeceras(extra = {}) {
  const h = { ...extra };
  if (CLAVE) h["X-API-Key"] = CLAVE;
  if (TOKEN) h.Authorization = `Bearer ${TOKEN}`;
  return h;
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
export const agentes = () => pedir("/api/agentes");
export const detonadores = () => pedir("/api/diego/detonadores");
export const registrosDiego = () => pedir("/api/diego/registros");

/** Cotejo determinista contra listas de sanciones y el padrón de SUNAT. No
 *  pasa por el modelo: el nombre del tercero no sale del servidor. */
export const cotejar = (nombre, ruc) =>
  pedir("/api/diego/cotejo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre: nombre || null, ruc: ruc || null }),
  });
export const normas = () => pedir("/api/normas");
export const regimenes = () => pedir("/api/regimenes");
export const grafo = () => pedir("/api/grafo");

export const consultar = (consulta, materias, agente) =>
  pedir("/api/consultar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      consulta,
      materias: materias?.length ? materias : null,
      agente: agente ?? null,
    }),
  });

/**
 * El cuestionario de debida diligencia. No pasa por el modelo: es una tabla
 * de decisión sobre el artículo 16 de la Resolución SBS, así que la misma
 * entrada da siempre la misma salida y cada requisito trae su inciso.
 */
export const generarCuestionario = (tipo, detonadoresMarcados) =>
  pedir("/api/diego/cuestionario", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tipo, detonadores: detonadoresMarcados }),
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
export async function consultarStream(consulta, materias, alEvento, señal, agente) {
  const resp = await fetch(`${BASE}/api/consultar/stream`, {
    method: "POST",
    headers: cabeceras({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      consulta,
      materias: materias?.length ? materias : null,
      agente: agente ?? null,
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

// ------------------------------------------------------------- documentos
// Exigen sesión: el backend responde 401 sin ella. La subida no lleva
// Content-Type a propósito — el navegador tiene que ponerlo él con el
// `boundary` del multipart, y fijarlo a mano rompe el parseo en el servidor.

export const listarDocumentos = () => pedir("/api/documentos");

export async function subirDocumento(archivo) {
  const cuerpo = new FormData();
  cuerpo.append("archivo", archivo);

  const resp = await fetch(`${BASE}/api/documentos`, {
    method: "POST",
    headers: cabeceras(),
    body: cuerpo,
  });
  if (!resp.ok) {
    const detalle = await resp.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${resp.status}`);
  }
  return resp.json();
}

export async function borrarDocumento(id) {
  const resp = await fetch(`${BASE}/api/documentos/${id}`, {
    method: "DELETE",
    headers: cabeceras(),
  });
  if (!resp.ok && resp.status !== 204) {
    const detalle = await resp.json().catch(() => null);
    throw new Error(detalle?.detail ?? `Error ${resp.status}`);
  }
}

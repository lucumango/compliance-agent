/**
 * Historial de conversaciones, contra Supabase directamente.
 *
 * No pasa por el backend a propósito. Row level security ya garantiza que cada
 * quien solo ve lo suyo —está en 001_historial.sql— así que un proxy en medio
 * solo añadiría una capa que puede equivocarse. El backend interviene donde
 * hace falta algo que el navegador no tiene: la clave de Gemini para
 * vectorizar. Leer y escribir filas propias no lo necesita.
 */
import { supabase } from "./supabase";

const TITULO_MAX = 60;

/** Título a partir de la primera pregunta, que es lo que la identifica. */
export function tituloDe(consulta) {
  const limpio = consulta.replace(/\s+/g, " ").trim();
  if (limpio.length <= TITULO_MAX) return limpio;
  // Corta en la última palabra entera para no dejar una sílaba suelta.
  const corte = limpio.slice(0, TITULO_MAX);
  const espacio = corte.lastIndexOf(" ");
  return `${espacio > 30 ? corte.slice(0, espacio) : corte}…`;
}

export async function listarConversaciones() {
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("conversaciones")
    .select("id, titulo, actualizada_en")
    .is("archivada_en", null)
    .order("actualizada_en", { ascending: false })
    .limit(100);
  if (error) throw new Error(error.message);
  return data ?? [];
}

export async function crearConversacion(usuarioId, titulo) {
  const { data, error } = await supabase
    .from("conversaciones")
    .insert({ usuario_id: usuarioId, titulo })
    .select("id, titulo, actualizada_en")
    .single();
  if (error) throw new Error(error.message);
  return data;
}

export async function renombrar(id, titulo) {
  const { error } = await supabase
    .from("conversaciones")
    .update({ titulo })
    .eq("id", id);
  if (error) throw new Error(error.message);
}

export async function borrarConversacion(id) {
  // Mensajes y fuentes caen en cascada.
  const { error } = await supabase.from("conversaciones").delete().eq("id", id);
  if (error) throw new Error(error.message);
}

/**
 * Guarda un mensaje y, si es del asistente, sus citas.
 *
 * Las citas se copian enteras en vez de referenciar al corpus: el índice vive
 * fuera de Postgres y se reconstruye, así que una referencia apuntaría a algo
 * que puede haber cambiado. Está razonado en docs/DATOS.md.
 */
export async function guardarMensaje({
  conversacionId,
  orden,
  rol,
  contenido,
  advertencias = [],
  diagrama = null,
  fuentes = [],
  documentos = [],
  modelo = null,
  promptVersion = null,
}) {
  if (!supabase || !conversacionId) return null;

  const { data: mensaje, error } = await supabase
    .from("mensajes")
    .insert({
      conversacion_id: conversacionId,
      orden,
      rol,
      contenido,
      advertencias,
      diagrama,
      // Qué produjo esta respuesta. El modelo no es el configurado sino el que
      // contestó: la cadena de respaldo degrada sola al agotarse una cuota.
      // Sin estas dos columnas, una respuesta del historial no se puede
      // explicar seis meses después. Ver docs/GOBERNANZA.md.
      modelo,
      prompt_version: promptVersion,
    })
    .select("id")
    .single();
  if (error) throw new Error(error.message);

  const citas = [
    ...fuentes.map((f) => ({
      mensaje_id: mensaje.id,
      clase: "norma",
      etiqueta: f.etiqueta,
      unidad_id: f.cita,
      norma_id: f.norma,
      cita: f.cita,
      texto: f.texto,
      score: f.score,
      pagina: null,
    })),
    ...documentos.map((d) => ({
      mensaje_id: mensaje.id,
      clase: "documento",
      etiqueta: d.etiqueta,
      unidad_id: d.documento_id,
      norma_id: null,
      cita: d.cita,
      texto: d.texto,
      score: d.score,
      pagina: d.pagina ?? null,
    })),
  ];

  if (citas.length) {
    const { error: e2 } = await supabase.from("mensaje_fuentes").insert(citas);
    // Una cita que no se guarda no debe tumbar el mensaje, que es lo que de
    // verdad hay que conservar.
    if (e2) console.warn("No se guardaron las citas:", e2.message);
  }
  return mensaje.id;
}

/** Reconstruye una conversación en la forma que espera la interfaz. */
export async function cargarMensajes(conversacionId) {
  if (!supabase) return [];

  const { data, error } = await supabase
    .from("mensajes")
    .select(
      "id, orden, rol, contenido, advertencias, diagrama, modelo, prompt_version, " +
        "mensaje_fuentes (clase, etiqueta, cita, norma_id, texto, score, pagina, unidad_id)"
    )
    .eq("conversacion_id", conversacionId)
    .order("orden", { ascending: true });
  if (error) throw new Error(error.message);

  return (data ?? []).map((m) => {
    const citas = m.mensaje_fuentes ?? [];
    if (m.rol === "usuario") return { rol: "usuario", texto: m.contenido };
    return {
      rol: "asistente",
      respuesta: m.contenido,
      advertencias: m.advertencias ?? [],
      diagrama: m.diagrama,
      modelo: m.modelo,
      promptVersion: m.prompt_version,
      fuentes: citas
        .filter((c) => c.clase === "norma")
        .map((c) => ({
          etiqueta: c.etiqueta,
          cita: c.cita,
          norma: c.norma_id,
          texto: c.texto,
          score: c.score,
          vigente: true,
          materia: "",
          titulo: "",
        }))
        .sort((a, b) => a.etiqueta.localeCompare(b.etiqueta)),
      documentos: citas
        .filter((c) => c.clase === "documento")
        .map((c) => ({
          etiqueta: c.etiqueta,
          cita: c.cita,
          documento: c.cita,
          documento_id: c.unidad_id,
          pagina: c.pagina,
          texto: c.texto,
          score: c.score,
        }))
        .sort((a, b) => a.etiqueta.localeCompare(b.etiqueta)),
    };
  });
}

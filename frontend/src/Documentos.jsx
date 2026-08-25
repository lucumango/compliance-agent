import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  FileText,
  Loader2,
  Trash2,
  Upload,
} from "lucide-react";
import { borrarDocumento, listarDocumentos, subirDocumento } from "./api";

const MAX_MB = 20;

function tamano(bytes) {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/**
 * Panel de documentos del usuario.
 *
 * La subida es síncrona y puede tardar: extraer, trocear y vectorizar un PDF
 * de cien páginas son varias llamadas al modelo de embeddings. De ahí que el
 * botón se bloquee y diga en qué anda, en vez de dar por hecho que es
 * instantáneo.
 */
export default function Documentos({ onCambio }) {
  const [lista, setLista] = useState([]);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState(null);
  const entradaRef = useRef(null);

  async function refrescar() {
    try {
      const docs = await listarDocumentos();
      setLista(docs);
      onCambio?.(docs.filter((d) => d.estado === "listo").length);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refrescar();
    // Solo al montar: el resto de recargas las dispara subir o borrar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function alElegir(e) {
    const archivo = e.target.files?.[0];
    // Permite volver a elegir el mismo archivo después de un error; sin esto
    // el input no dispara change la segunda vez.
    e.target.value = "";
    if (!archivo) return;

    if (archivo.size > MAX_MB * 1024 * 1024) {
      setError(`El archivo pesa más de ${MAX_MB} MB.`);
      return;
    }

    setSubiendo(true);
    setError(null);
    try {
      await subirDocumento(archivo);
      await refrescar();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubiendo(false);
    }
  }

  async function quitar(doc) {
    if (!confirm(`¿Quitar "${doc.nombre}"? Deja de poder citarse.`)) return;
    try {
      await borrarDocumento(doc.id);
      await refrescar();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section className="docs">
      <p className="rotulo">
        <FileText size={13} aria-hidden="true" /> Mis documentos
      </p>

      <input
        ref={entradaRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={alElegir}
        hidden
      />

      <button
        type="button"
        className="docs-subir"
        onClick={() => entradaRef.current?.click()}
        disabled={subiendo}
      >
        {subiendo ? (
          <>
            <Loader2 size={14} className="gira" aria-hidden="true" />
            Indexando…
          </>
        ) : (
          <>
            <Upload size={14} aria-hidden="true" />
            Subir PDF o DOCX
          </>
        )}
      </button>

      {error && (
        <p className="docs-error" role="alert">
          <AlertTriangle size={13} aria-hidden="true" /> {error}
        </p>
      )}

      {lista.length === 0 && !subiendo && (
        <p className="pista">
          Sube tus políticas para que el asistente pueda contrastarlas con la
          norma. Se citan marcadas como documento tuyo, nunca como ley.
        </p>
      )}

      <ul className="docs-lista">
        {lista.map((d) => (
          <li key={d.id} className={d.estado === "error" ? "malo" : ""}>
            <div className="docs-datos">
              <span className="docs-nombre" title={d.nombre}>
                {d.nombre}
              </span>
              <span className="meta">
                {d.estado === "listo"
                  ? `${d.fragmentos} fragmentos · ${tamano(d.bytes)}`
                  : d.estado === "error"
                    ? (d.error ?? "No se pudo indexar")
                    : "Procesando…"}
              </span>
            </div>
            <button
              type="button"
              className="docs-quitar"
              onClick={() => quitar(d)}
              aria-label={`Quitar ${d.nombre}`}
            >
              <Trash2 size={13} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>

      <p className="pista docs-nota">
        No se admite escaneo sin capa de texto: este servidor no hace OCR.
      </p>
    </section>
  );
}

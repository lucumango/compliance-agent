import { useState } from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";

/**
 * Lista de conversaciones guardadas.
 *
 * Las fechas se muestran relativas hasta la semana y absolutas después: "hace
 * 2 h" sitúa mejor lo reciente, y "12 mar" sitúa mejor lo viejo.
 */
function cuando(iso) {
  const d = new Date(iso);
  const min = Math.round((Date.now() - d.getTime()) / 60000);
  if (min < 1) return "ahora";
  if (min < 60) return `hace ${min} min`;
  if (min < 60 * 24) return `hace ${Math.round(min / 60)} h`;
  if (min < 60 * 24 * 7) return `hace ${Math.round(min / 1440)} d`;
  return d.toLocaleDateString("es-PE", { day: "numeric", month: "short" });
}

export default function Historial({
  conversaciones,
  activa,
  alAbrir,
  alNueva,
  alBorrar,
}) {
  const [borrando, setBorrando] = useState(null);

  return (
    <section className="historial">
      <p className="rotulo">
        <MessageSquare size={13} aria-hidden="true" /> Conversaciones
      </p>

      <button type="button" className="hist-nueva" onClick={alNueva}>
        <Plus size={14} aria-hidden="true" />
        Nueva consulta
      </button>

      {conversaciones.length === 0 ? (
        <p className="pista">Lo que preguntes se guarda aquí.</p>
      ) : (
        <ul className="hist-lista">
          {conversaciones.map((c) => (
            <li key={c.id} className={c.id === activa ? "activa" : ""}>
              <button
                type="button"
                className="hist-abrir"
                onClick={() => alAbrir(c.id)}
                title={c.titulo}
              >
                <span className="hist-titulo">{c.titulo}</span>
                <span className="meta">{cuando(c.actualizada_en)}</span>
              </button>
              <button
                type="button"
                className="hist-quitar"
                aria-label={`Borrar ${c.titulo}`}
                onClick={async () => {
                  if (!confirm(`¿Borrar "${c.titulo}"? No se puede deshacer.`))
                    return;
                  setBorrando(c.id);
                  await alBorrar(c.id);
                  setBorrando(null);
                }}
                disabled={borrando === c.id}
              >
                <Trash2 size={13} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

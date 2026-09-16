/**
 * Cotejo de un tercero contra registros públicos. Panel de DIEGO.
 *
 * Determinista y sin modelo. Dos clases de resultado, y la interfaz no puede
 * confundirlas:
 *
 *   SUNAT     por RUC es un HECHO: estado y condición de domicilio a la fecha
 *             del padrón.
 *   Sanciones por nombre es una COINCIDENCIA POTENCIAL: se compara texto, no
 *             se identifica a nadie. Por eso cada una enseña su score y los
 *             datos que permiten descartar un homónimo.
 *
 * Y todo "no aparece" lleva lista y fecha. Sin eso no significa nada.
 */
import { useState } from "react";
import { ShieldAlert, Search, CheckCircle2, AlertTriangle } from "lucide-react";
import { cotejar } from "./api";

export default function Cotejo() {
  const [nombre, setNombre] = useState("");
  const [ruc, setRuc] = useState("");
  const [cargando, setCargando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);

  async function enviar(e) {
    e.preventDefault();
    if (!nombre.trim() && !ruc.trim()) return;
    setCargando(true);
    setError(null);
    try {
      setResultado(await cotejar(nombre.trim(), ruc.trim()));
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }

  const sunat = resultado?.sunat;
  const sanciones = resultado?.sanciones;

  return (
    <section className="cotejo">
      <p className="rotulo">
        <ShieldAlert size={14} aria-hidden="true" /> Cotejo de un tercero
      </p>

      <form onSubmit={enviar} className="cotejo-form">
        <input
          type="text"
          placeholder="Razón social o nombre"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          aria-label="Razón social o nombre"
        />
        <input
          type="text"
          inputMode="numeric"
          placeholder="RUC (opcional)"
          value={ruc}
          onChange={(e) => setRuc(e.target.value)}
          aria-label="RUC"
        />
        <button type="submit" disabled={cargando || (!nombre.trim() && !ruc.trim())}>
          <Search size={13} aria-hidden="true" /> {cargando ? "Cotejando…" : "Cotejar"}
        </button>
      </form>

      {error && (
        <p className="docs-error" role="alert">
          {error}
        </p>
      )}

      {sunat && (
        <div className="cotejo-bloque">
          <p className="cuest-grupo">
            SUNAT <span className="meta">padrón del {sunat.fecha_padron}</span>
          </p>
          {!sunat.encontrado ? (
            <p className="aviso-corpus">
              <AlertTriangle size={12} aria-hidden="true" /> Ese RUC no está en el
              padrón. Compruébalo: puede estar mal escrito, o no existir.
            </p>
          ) : (
            <div className={sunat.contribuyente.alertas.length ? "cotejo-sunat alerta" : "cotejo-sunat"}>
              <strong>{sunat.contribuyente.nombre}</strong>
              <span>
                {sunat.contribuyente.estado} · {sunat.contribuyente.condicion}
              </span>
              {sunat.contribuyente.alertas.map((a) => (
                <span key={a} className="cotejo-alerta">
                  <AlertTriangle size={11} aria-hidden="true" /> {a}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {sanciones && (
        <div className="cotejo-bloque">
          <p className="cuest-grupo">
            Listas de sanciones
            <span className="meta">«{sanciones.nombre_cotejado}»</span>
          </p>

          {sanciones.coincidencias.length === 0 ? (
            <p className="cotejo-limpio">
              <CheckCircle2 size={12} aria-hidden="true" /> Sin coincidencias en:{" "}
              {Object.entries(sanciones.listas)
                .map(([k, m]) => `${k} (${m.fecha})`)
                .join(", ")}
            </p>
          ) : (
            <ul className="cotejo-lista">
              {sanciones.coincidencias.map((c) => (
                <li key={c.lista + c.id}>
                  <span className="cotejo-score">{Math.round(c.score)}</span>
                  <div>
                    <strong>{c.nombre}</strong>
                    <span className="meta">
                      {c.lista} · {c.id} · {c.tipo}
                      {c.programa ? ` · ${c.programa}` : ""}
                    </span>
                    {c.paises.length > 0 && <span className="meta">{c.paises.join(", ")}</span>}
                    {c.identificadores.length > 0 && (
                      <span className="meta">{c.identificadores.join(" · ").slice(0, 160)}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {sanciones.vigencia.map((v) => (
            <p key={v} className="aviso-corpus">
              <AlertTriangle size={12} aria-hidden="true" /> {v}
            </p>
          ))}
        </div>
      )}

      {resultado?.osce && (
        <div className="cotejo-bloque">
          <p className="cuest-grupo">
            Inhabilitados para contratar con el Estado
            <span className="meta">OSCE, dataset del {resultado.osce.fecha_dataset}</span>
          </p>
          {(() => {
            const filas = resultado.osce.por_ruc.length
              ? resultado.osce.por_ruc
              : resultado.osce.por_nombre;
            const esHecho = resultado.osce.por_ruc.length > 0;
            if (!filas.length)
              return <p className="cotejo-limpio">Sin sanciones en este dataset.</p>;
            return (
              <ul className="cotejo-lista">
                {filas.map((s) => (
                  <li key={s.resolucion + s.ruc}>
                    <span className="cotejo-score">{esHecho ? "RUC" : Math.round(s.score)}</span>
                    <div>
                      <strong>{s.razon_social}</strong>
                      <span className="meta">
                        {s.ruc} · {s.tipo} · Res. {s.resolucion}
                      </span>
                      <span className="meta">
                        {s.desde} → {s.hasta || "definitiva"} ·{" "}
                        {s.vigente_hoy ? "VIGENTE HOY" : "ya vencida"}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            );
          })()}
          {resultado.osce.avisos.map((v) => (
            <p key={v} className="aviso-corpus">
              <AlertTriangle size={12} aria-hidden="true" /> {v}
            </p>
          ))}
        </div>
      )}

      {resultado && (
        <>
          {resultado.no_comprobado.map((n) => (
            <p key={n} className="pista">
              No comprobado: {n}
            </p>
          ))}
          <p className="aviso-corpus">{resultado.advertencia}</p>
        </>
      )}
    </section>
  );
}

/**
 * Cuestionario de debida diligencia, el panel propio de DIEGO.
 *
 * No llama al modelo. El backend resuelve una tabla de decisión sobre el
 * artículo 16 de la Resolución SBS 789-2018, así que la misma entrada da
 * siempre la misma salida y cada requisito llega con su inciso.
 *
 * La separación que la interfaz NO puede perder: lo que exige la norma lleva
 * cita, y lo que es práctica de la firma no la lleva y va en otro bloque. Es
 * la misma distinción que entre una fuente [F] y una [D], y por el mismo
 * motivo: acabar exigiéndole a un cliente como ley lo que era criterio propio
 * es el error que cuesta caro.
 */
import { useEffect, useState } from "react";
import { ClipboardCheck, Scale, Building2 } from "lucide-react";
import { detonadores as pedirDetonadores, generarCuestionario } from "./api";

const TIPOS = {
  persona_natural: "Persona natural",
  persona_juridica: "Persona jurídica",
  proveedor: "Proveedor",
};

const REGIMENES = {
  general: { nombre: "General", clase: "bajo" },
  reforzado: { nombre: "Reforzado", clase: "alto" },
  simplificado: { nombre: "Simplificado", clase: "bajo" },
};

export default function Cuestionario() {
  const [catalogo, setCatalogo] = useState([]);
  const [tipo, setTipo] = useState("proveedor");
  const [marcados, setMarcados] = useState([]);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    pedirDetonadores()
      .then((d) => setCatalogo(d.detonadores ?? []))
      .catch((e) => setError(e.message));
  }, []);

  // Se recalcula al vuelo: no llama al modelo, así que no hay razón para
  // hacer al usuario pulsar un botón y esperar.
  useEffect(() => {
    if (!catalogo.length) return;
    generarCuestionario(tipo, marcados).then(setResultado).catch((e) => setError(e.message));
  }, [tipo, marcados, catalogo.length]);

  const alternar = (id) =>
    setMarcados((m) => (m.includes(id) ? m.filter((x) => x !== id) : [...m, id]));

  const porOrigen = (o) => catalogo.filter((d) => d.origen === o);
  const regimen = resultado ? REGIMENES[resultado.regimen] ?? REGIMENES.general : null;

  return (
    <section className="cuest">
      <p className="rotulo">
        <ClipboardCheck size={14} aria-hidden="true" /> Cuestionario de debida diligencia
      </p>

      {error && (
        <p className="docs-error" role="alert">
          {error}
        </p>
      )}

      <label className="cuest-tipo">
        <span>Contraparte</span>
        <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
          {Object.entries(TIPOS).map(([id, nombre]) => (
            <option key={id} value={id}>
              {nombre}
            </option>
          ))}
        </select>
      </label>

      <p className="cuest-grupo">
        <Scale size={12} aria-hidden="true" /> Detonadores de la norma
      </p>
      <ul className="cuest-lista">
        {porOrigen("norma").map((d) => (
          <li key={d.id}>
            <label>
              <input
                type="checkbox"
                checked={marcados.includes(d.id)}
                onChange={() => alternar(d.id)}
              />
              <span>
                {d.etiqueta}
                <span className="meta">{d.cita}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>

      <p className="cuest-grupo">
        <Building2 size={12} aria-hidden="true" /> Criterio de la firma
        <span className="meta">no lo exige ninguna norma cargada</span>
      </p>
      <ul className="cuest-lista">
        {porOrigen("practica").map((d) => (
          <li key={d.id}>
            <label>
              <input
                type="checkbox"
                checked={marcados.includes(d.id)}
                onChange={() => alternar(d.id)}
              />
              <span>{d.etiqueta}</span>
            </label>
          </li>
        ))}
      </ul>

      {resultado && (
        <div className="cuest-salida">
          <p className="cuest-regimen">
            Régimen legal
            <span className={`cuest-sello ${regimen.clase}`}>{regimen.nombre}</span>
          </p>

          {resultado.porque.length > 0 && (
            <ul className="cuest-porque">
              {resultado.porque.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}

          <p className="cuest-grupo">
            Información mínima exigida
            <span className="meta">{resultado.requisitos.length} puntos</span>
          </p>
          <ol className="cuest-req">
            {resultado.requisitos.map((r) => (
              <li key={r.cita + r.texto}>
                {r.texto}
                <span className="meta">{r.cita}</span>
              </li>
            ))}
          </ol>

          <p className="cuest-grupo">
            Además, por práctica
            <span className="meta">sin base normativa en el corpus</span>
          </p>
          <ul className="cuest-practica">
            {resultado.practica.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>

          {resultado.avisos.map((a) => (
            <p className="aviso-corpus" key={a}>
              {a}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}

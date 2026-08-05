import { useEffect, useState } from "react";
import { DollarSign, TrendingUp } from "lucide-react";
import { calcularMulta, regimenes as pedirRegimenes } from "./api";

// La escala de gravedad del régimen sancionador mapea sobre los colores
// semánticos de riesgo del sistema EY, así que no hacen falta colores propios.
const NIVELES = {
  leve: { nombre: "Leve", color: "var(--color-risk-low)", clase: "bajo" },
  grave: { nombre: "Grave", color: "var(--color-risk-medium)", clase: "medio" },
  muy_grave: {
    nombre: "Muy grave",
    color: "var(--color-risk-high)",
    clase: "alto",
  },
};

// Proporción de la barra: dónde cae el tramo dentro de la escala del régimen.
const PROPORCION = { leve: 33, grave: 66, muy_grave: 100 };

const soles = (n) =>
  n.toLocaleString("es-PE", {
    style: "currency",
    currency: "PEN",
    maximumFractionDigits: 0,
  });

export default function CalculadoraMultas() {
  const [regimenes, setRegimenes] = useState([]);
  const [regimen, setRegimen] = useState("");
  const [gravedad, setGravedad] = useState("");
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    pedirRegimenes()
      .then((rs) => {
        setRegimenes(rs);
        if (rs.length) {
          setRegimen(rs[0].id);
          setGravedad(rs[0].gravedades[0]);
        }
      })
      .catch(() => setRegimenes([]));
  }, []);

  const actual = regimenes.find((r) => r.id === regimen);

  useEffect(() => {
    if (!regimen || !gravedad) return;
    calcularMulta(regimen, gravedad)
      .then((r) => {
        setResultado(r);
        setError(null);
      })
      .catch((e) => {
        setResultado(null);
        setError(e.message);
      });
  }, [regimen, gravedad]);

  if (!regimenes.length) return null;

  const nivel = NIVELES[gravedad] ?? {
    nombre: gravedad,
    color: "var(--color-risk-none)",
    clase: "neutro",
  };

  return (
    <section className="calculadora">
      <p className="rotulo">
        <DollarSign size={14} aria-hidden="true" />
        Estimador de multas
      </p>

      <select
        value={regimen}
        onChange={(e) => setRegimen(e.target.value)}
        aria-label="Régimen sancionador"
      >
        {regimenes.map((r) => (
          <option key={r.id} value={r.id}>
            {r.nombre}
          </option>
        ))}
      </select>

      <div className="gravedades" role="group" aria-label="Gravedad">
        {actual?.gravedades.map((g) => (
          <button
            key={g}
            className={g === gravedad ? "activo" : ""}
            onClick={() => setGravedad(g)}
            aria-pressed={g === gravedad}
          >
            {NIVELES[g]?.nombre ?? g}
          </button>
        ))}
      </div>

      {error && <p className="pista">{error}</p>}

      {resultado && (
        <div className="tarjeta" style={{ "--nivel": nivel.color }}>
          <span className={`badge ${nivel.clase}`}>
            <TrendingUp size={12} aria-hidden="true" />
            {nivel.nombre}
          </span>

          <p className="monto">
            {soles(resultado.min_soles)} – {soles(resultado.max_soles)}
          </p>

          <div
            className="barra-riesgo"
            role="img"
            aria-label={`Tramo ${nivel.nombre} dentro de la escala del régimen`}
          >
            <span style={{ width: `${PROPORCION[gravedad] ?? 100}%` }} />
          </div>

          <p className="detalle">
            {resultado.rango_uit[0]}–{resultado.rango_uit[1]} UIT · UIT{" "}
            {resultado.anio_uit}: {soles(resultado.valor_uit)}
          </p>
          <p className="detalle fuente">Base legal: {resultado.fuente_rango}</p>
          {resultado.tope_adicional && (
            <p className="detalle">{resultado.tope_adicional}</p>
          )}
          <p className="detalle">{resultado.advertencia}</p>
        </div>
      )}
    </section>
  );
}

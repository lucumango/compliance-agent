import { useEffect, useState } from "react";
import { calcularMulta, regimenes as pedirRegimenes } from "./api";

const NOMBRES = {
  leve: "Leve",
  grave: "Grave",
  muy_grave: "Muy grave",
};

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

  return (
    <section className="calculadora">
      <h2>Estimador de multas</h2>

      <select value={regimen} onChange={(e) => setRegimen(e.target.value)}>
        {regimenes.map((r) => (
          <option key={r.id} value={r.id}>
            {r.nombre}
          </option>
        ))}
      </select>

      <div className="gravedades">
        {actual?.gravedades.map((g) => (
          <button
            key={g}
            className={g === gravedad ? "activo" : ""}
            onClick={() => setGravedad(g)}
          >
            {NOMBRES[g] ?? g}
          </button>
        ))}
      </div>

      {error && <p className="pista">{error}</p>}

      {resultado && (
        <div className="resultado">
          <p className="monto">
            {soles(resultado.min_soles)} – {soles(resultado.max_soles)}
          </p>
          <p className="detalle">
            {resultado.rango_uit[0]}–{resultado.rango_uit[1]} UIT · UIT{" "}
            {resultado.anio_uit}: {soles(resultado.valor_uit)}
          </p>
          <p className="detalle fuente">Base legal: {resultado.fuente_rango}</p>
          {resultado.tope_adicional && (
            <p className="detalle tope">{resultado.tope_adicional}</p>
          )}
          <p className="detalle aviso">{resultado.advertencia}</p>
        </div>
      )}
    </section>
  );
}

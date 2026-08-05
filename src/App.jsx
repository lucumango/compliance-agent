import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import Mermaid from "./Mermaid";
import CalculadoraMultas from "./CalculadoraMultas";
import { consultarStream, normas, pedirDiagrama, salud } from "./api";
import "./App.css";

const EJEMPLOS = [
  "¿Cuál es la multa máxima por una infracción muy grave en protección de datos?",
  "¿Qué debo hacer si ocurre un accidente de trabajo mortal?",
  "¿Cómo se tramita una solicitud de acceso a datos personales y en qué plazo?",
  "¿Qué medidas administrativas se aplican a una persona jurídica por cohecho?",
];

function Fuente({ fuente }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <li className="fuente">
      <button className="fuente-cab" onClick={() => setAbierto((v) => !v)}>
        <span className="etiqueta">{fuente.etiqueta}</span>
        <span className="cita">{fuente.cita}</span>
        <span className="score">{fuente.score.toFixed(3)}</span>
      </button>
      {abierto && <pre className="fuente-texto">{fuente.texto}</pre>}
    </li>
  );
}

function Mensaje({ mensaje }) {
  if (mensaje.rol === "usuario") {
    return <div className="msg usuario">{mensaje.texto}</div>;
  }

  // Un error puede llegar después de haberse emitido parte del texto, así que
  // se muestra junto a lo ya redactado en vez de reemplazarlo.
  if (mensaje.error && !mensaje.respuesta) {
    return <div className="msg error">⚠ {mensaje.error}</div>;
  }

  return (
    <div className="msg asistente">
      {mensaje.respuesta ? (
        <div className="prosa">
          <ReactMarkdown>{mensaje.respuesta}</ReactMarkdown>
          {mensaje.generando && <span className="cursor" />}
        </div>
      ) : (
        <p className="redactando">Redactando…</p>
      )}

      {mensaje.error && <p className="error-parcial">⚠ {mensaje.error}</p>}

      {mensaje.diagrama && <Mermaid codigo={mensaje.diagrama} />}
      {mensaje.cargandoDiagrama && (
        <p className="redactando">Dibujando el diagrama…</p>
      )}

      {mensaje.advertencias?.length > 0 && (
        <div className="advertencias">
          {mensaje.advertencias.map((a, i) => (
            <p key={i}>⚠ {a}</p>
          ))}
        </div>
      )}

      {mensaje.fuentes?.length > 0 && (
        <details className="fuentes" open>
          <summary>{mensaje.fuentes.length} fuentes citadas</summary>
          <ul>
            {mensaje.fuentes.map((f) => (
              <Fuente key={f.etiqueta} fuente={f} />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

export default function App() {
  const [mensajes, setMensajes] = useState([]);
  const [entrada, setEntrada] = useState("");
  const [cargando, setCargando] = useState(false);
  const [corpus, setCorpus] = useState([]);
  const [materias, setMaterias] = useState([]);
  const [estado, setEstado] = useState(null);
  const finRef = useRef(null);

  useEffect(() => {
    salud().then(setEstado).catch(() => setEstado({ ok: false }));
    normas().then(setCorpus).catch(() => setCorpus([]));
  }, []);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensajes, cargando]);

  async function enviar(texto) {
    const consulta = (texto ?? entrada).trim();
    if (!consulta || cargando) return;

    setEntrada("");
    setCargando(true);

    // El hueco del asistente se crea vacío y se va rellenando: primero las
    // fuentes, luego el texto fragmento a fragmento.
    let indice;
    setMensajes((m) => {
      indice = m.length + 1;
      return [
        ...m,
        { rol: "usuario", texto: consulta },
        { rol: "asistente", respuesta: "", fuentes: [], generando: true },
      ];
    });

    const parchear = (cambios) =>
      setMensajes((m) =>
        m.map((msg, i) => (i === indice ? { ...msg, ...cambios } : msg))
      );

    let acumulado = "";
    let llevaDiagrama = false;

    try {
      await consultarStream(consulta, materias, (evento, datos) => {
        if (evento === "fuentes") {
          parchear({
            fuentes: datos.fuentes,
            advertencias: datos.advertencias,
          });
        } else if (evento === "delta") {
          acumulado += datos.texto;
          parchear({ respuesta: acumulado });
        } else if (evento === "error") {
          parchear({ error: datos.mensaje, generando: false });
        } else if (evento === "fin") {
          llevaDiagrama = datos.lleva_diagrama;
        }
      });

      parchear({ generando: false, cargandoDiagrama: llevaDiagrama });

      // El diagrama va en una segunda petición: necesita la respuesta
      // completa, y pedirlo aquí evita que retrase el texto.
      if (llevaDiagrama && acumulado) {
        try {
          const { diagrama } = await pedirDiagrama(acumulado);
          parchear({ diagrama, cargandoDiagrama: false });
        } catch {
          parchear({ cargandoDiagrama: false });
        }
      }
    } catch (e) {
      parchear({ error: e.message, generando: false, cargandoDiagrama: false });
    } finally {
      setCargando(false);
    }
  }

  function alternarMateria(materia) {
    setMaterias((ms) =>
      ms.includes(materia) ? ms.filter((m) => m !== materia) : [...ms, materia]
    );
  }

  return (
    <div className="app">
      <aside className="lateral">
        <h1>Asistente de Compliance</h1>
        <p className="sub">Normativa peruana · respuestas con cita a la fuente</p>

        <h2>Filtrar por materia</h2>
        <ul className="corpus">
          {corpus.map((n) => (
            <li key={n.norma_id}>
              <label>
                <input
                  type="checkbox"
                  checked={materias.includes(n.materia)}
                  onChange={() => alternarMateria(n.materia)}
                />
                <span>
                  {n.nombre}
                  <em>
                    {n.unidades} unidades
                    {n.requiere_cotejo && " · OCR"}
                  </em>
                </span>
              </label>
            </li>
          ))}
        </ul>
        {materias.length === 0 && (
          <p className="pista">Sin filtro: busca en todo el corpus.</p>
        )}

        <CalculadoraMultas />

        {estado && (
          <p className="estado">
            {estado.ok
              ? `${estado.unidades_indexadas} unidades · UIT ${estado.uit.anio}: S/ ${estado.uit.valor.toLocaleString("es-PE")}`
              : "Backend no disponible"}
          </p>
        )}
      </aside>

      <main className="chat">
        <div className="mensajes">
          {mensajes.length === 0 && (
            <div className="bienvenida">
              <h2>¿Qué necesitas consultar?</h2>
              <p>
                Respondo únicamente a partir del corpus normativo cargado, y cito
                el artículo de cada afirmación. Si el corpus no cubre tu consulta,
                te lo digo en vez de improvisar.
              </p>
              <div className="ejemplos">
                {EJEMPLOS.map((e) => (
                  <button key={e} onClick={() => enviar(e)}>
                    {e}
                  </button>
                ))}
              </div>
            </div>
          )}

          {mensajes.map((m, i) => (
            <Mensaje key={i} mensaje={m} />
          ))}
          <div ref={finRef} />
        </div>

        <form
          className="entrada"
          onSubmit={(e) => {
            e.preventDefault();
            enviar();
          }}
        >
          <textarea
            value={entrada}
            onChange={(e) => setEntrada(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                enviar();
              }
            }}
            placeholder="Escribe tu consulta… (Enter para enviar, Shift+Enter para salto de línea)"
            rows={2}
          />
          <button type="submit" disabled={cargando || !entrada.trim()}>
            Consultar
          </button>
        </form>

        <p className="descargo">
          Este asistente informa sobre normativa; no constituye asesoría legal.
          Verifica siempre contra la fuente oficial.
        </p>
      </main>
    </div>
  );
}

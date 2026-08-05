import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  AlertTriangle,
  Building2,
  Clock,
  DollarSign,
  FileSearch,
  Filter,
  Loader2,
  Scale,
  Send,
  Sparkles,
  XCircle,
} from "lucide-react";
import Mermaid from "./Mermaid";
import CalculadoraMultas from "./CalculadoraMultas";
import { consultarStream, normas, pedirDiagrama, salud } from "./api";
import "./App.css";

const EJEMPLOS = [
  {
    icono: DollarSign,
    texto:
      "¿Cuál es la multa máxima por una infracción muy grave en protección de datos?",
  },
  {
    icono: AlertTriangle,
    texto: "¿Qué debo hacer si ocurre un accidente de trabajo mortal?",
  },
  {
    icono: Clock,
    texto:
      "¿Cómo se tramita una solicitud de acceso a datos personales y en qué plazo?",
  },
  {
    icono: Building2,
    texto:
      "¿Qué medidas administrativas se aplican a una persona jurídica por cohecho?",
  },
];

function Fuente({ fuente }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <li className="fuente">
      <button
        className="fuente-cab"
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
      >
        <span className="etiqueta">{fuente.etiqueta}</span>
        <span className="cita">{fuente.cita}</span>
        <span className="score" aria-label={`Similitud ${fuente.score}`}>
          {fuente.score.toFixed(3)}
        </span>
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
    return (
      <div className="msg error">
        <XCircle size={16} aria-hidden="true" />
        <span>{mensaje.error}</span>
      </div>
    );
  }

  return (
    <div className="msg asistente">
      <p className="ia-cab">
        <Sparkles size={14} aria-hidden="true" />
        Respuesta generada · anclada a las fuentes citadas
      </p>

      {mensaje.respuesta ? (
        <div className="prosa">
          <ReactMarkdown>{mensaje.respuesta}</ReactMarkdown>
          {mensaje.generando && <span className="cursor" aria-hidden="true" />}
        </div>
      ) : (
        <div className="skeleton" aria-busy="true" aria-label="Redactando">
          <span />
          <span />
          <span />
        </div>
      )}

      {mensaje.error && <p className="error-parcial">{mensaje.error}</p>}

      {mensaje.diagrama && <Mermaid codigo={mensaje.diagrama} />}
      {mensaje.cargandoDiagrama && (
        <p className="cargando-linea" aria-busy="true">
          <Loader2 size={14} className="gira" aria-hidden="true" />
          Dibujando el diagrama…
        </p>
      )}

      {mensaje.advertencias?.length > 0 && (
        <div className="advertencias">
          {mensaje.advertencias.map((a, i) => (
            <div className="hallazgo" key={i} role="note">
              <AlertTriangle size={16} aria-hidden="true" />
              <p>{a}</p>
            </div>
          ))}
        </div>
      )}

      {mensaje.fuentes?.length > 0 && (
        <details className="fuentes" open>
          <summary>
            <FileSearch size={14} aria-hidden="true" />
            {mensaje.fuentes.length} fuentes citadas
          </summary>
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
    salud()
      .then(setEstado)
      .catch(() => setEstado({ ok: false }));
    normas()
      .then(setCorpus)
      .catch(() => setCorpus([]));
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
          parchear({ fuentes: datos.fuentes, advertencias: datos.advertencias });
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
      <header className="cabecera">
        <div className="marca">
          <Scale size={24} aria-hidden="true" />
          <h1>Asistente de Normativa y Compliance</h1>
        </div>
        <span className="sello">Powered by EY</span>

        {estado && (
          <p className="estado-global">
            {estado.ok ? (
              <>
                <span>{estado.unidades_indexadas} unidades indexadas</span>
                <span aria-hidden="true">·</span>
                <span>
                  UIT {estado.uit.anio}: S/{" "}
                  {estado.uit.valor.toLocaleString("es-PE")}
                </span>
              </>
            ) : (
              <>
                <XCircle size={14} aria-hidden="true" />
                Backend no disponible
              </>
            )}
          </p>
        )}
      </header>

      <div className="cuerpo">
        <aside className="lateral">
          <section>
            <p className="rotulo">
              <Filter size={14} aria-hidden="true" />
              Filtrar por materia
            </p>
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
                      <span className="meta">
                        {n.unidades} unidades
                        {n.requiere_cotejo && " · OCR, requiere cotejo"}
                      </span>
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            {materias.length === 0 && (
              <p className="pista">Sin filtro: busca en todo el corpus.</p>
            )}
          </section>

          <CalculadoraMultas />
        </aside>

        <main className="chat">
          <div className="mensajes">
            {mensajes.length === 0 && (
              <div className="bienvenida">
                <h2>¿Qué necesitas consultar?</h2>
                <p>
                  Respondo únicamente a partir del corpus normativo cargado, y
                  cito el artículo de cada afirmación. Si el corpus no cubre tu
                  consulta, te lo digo en vez de improvisar.
                </p>
                <div className="ejemplos">
                  {EJEMPLOS.map(({ icono: Icono, texto }) => (
                    <button key={texto} onClick={() => enviar(texto)}>
                      <Icono size={16} aria-hidden="true" />
                      {texto}
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
              aria-label="Consulta"
            />
            <button
              type="submit"
              className="btn-primary"
              disabled={cargando || !entrada.trim()}
            >
              {cargando ? (
                <Loader2 size={16} className="gira" aria-hidden="true" />
              ) : (
                <Send size={16} aria-hidden="true" />
              )}
              Consultar
            </button>
          </form>

          <p className="descargo">
            Este asistente informa sobre normativa; no constituye asesoría
            legal. Verifica siempre contra la fuente oficial.
          </p>
        </main>
      </div>
    </div>
  );
}

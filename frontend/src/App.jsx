import { Children, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  AlertTriangle,
  Building2,
  Clock,
  DollarSign,
  FileSearch,
  FileText,
  Filter,
  Landmark,
  Loader2,
  LogOut,
  Moon,
  ScanLine,
  Search,
  Send,
  Sparkles,
  Sun,
  XCircle,
} from "lucide-react";
import Mermaid from "./Mermaid";
import CalculadoraMultas from "./CalculadoraMultas";
import GrafoNormas from "./GrafoNormas";
import Auth from "./Auth";
import Documentos from "./Documentos";
import Historial from "./Historial";
import { hayCuentas } from "./supabase";
import { useSesion } from "./sesion";
import {
  borrarConversacion,
  cargarMensajes,
  crearConversacion,
  guardarMensaje,
  listarConversaciones,
  tituloDe,
} from "./conversaciones";
import { consultarStream, normas, pedirDiagrama, salud } from "./api";
import "./App.css";

const CLAVE_TEMA = "compliance:tema";

/**
 * Tema con tres estados: "claro", "oscuro" y `null` = lo que diga el sistema.
 * Mientras nadie elija, se respeta la preferencia del sistema operativo; en
 * cuanto se elige, `data-theme` en el <html> manda sobre la media query.
 */
function useTema() {
  const [tema, setTema] = useState(() => localStorage.getItem(CLAVE_TEMA));

  useEffect(() => {
    const raiz = document.documentElement;
    if (tema) {
      raiz.setAttribute("data-theme", tema === "oscuro" ? "dark" : "light");
      localStorage.setItem(CLAVE_TEMA, tema);
    } else {
      raiz.removeAttribute("data-theme");
      localStorage.removeItem(CLAVE_TEMA);
    }
  }, [tema]);

  // Solo hace falta saber qué se está pintando para rotular el botón.
  const oscuroAhora =
    tema === "oscuro" ||
    (!tema && window.matchMedia?.("(prefers-color-scheme: dark)").matches);

  return [oscuroAhora, () => setTema(oscuroAhora ? "claro" : "oscuro")];
}

// Margen en px por debajo del cual se considera que el usuario sigue al final
// de la conversación. Holgado a propósito: el cursor de escritura y el salto
// de línea del último fragmento mueven el fondo unos pocos píxeles.
const UMBRAL_PEGADO = 80;

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
  // LA/FT es hoy la materia con más normas del corpus (Ley 27693, Ley 29038,
  // DL 1106 y DL 1372) y no tenía ni un ejemplo.
  {
    icono: Landmark,
    texto: "¿Quién está obligado a declarar el beneficiario final y en qué plazo?",
  },
  {
    icono: Search,
    texto:
      "¿Cuándo debe comunicarse una operación sospechosa a la UIF-Perú?",
  },
];

function Fuente({ fuente, abierto, alAlternar, id }) {
  return (
    <li className="fuente" id={id}>
      <button className="fuente-cab" onClick={alAlternar} aria-expanded={abierto}>
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

// El modelo cita con etiquetas desnudas ([F1], [F3]) porque son las que el
// prompt le impone y las únicas que puede escribir sin equivocarse. Aquí se
// convierten en algo legible: la etiqueta muestra la norma al pasar por
// encima, y al pulsarla abre esa fuente en el panel. El texto visible sigue
// siendo corto para no romper la lectura del párrafo.
// [F1] es una norma; [D1] es un documento que subió el usuario. Se pintan
// distinto a propósito: la diferencia entre "la ley obliga" y "tu política
// dice" es justo lo que no puede quedar a interpretación del lector.
const RE_CITA = /\[([FD]\d+)\]/g;

function ChipCita({ etiqueta, fuente, alPulsar }) {
  if (!fuente) return <span className="cita-chip huerfana">[{etiqueta}]</span>;
  const esDoc = etiqueta.startsWith("D");
  return (
    <button
      type="button"
      className={esDoc ? "cita-chip doc" : "cita-chip"}
      title={esDoc ? `Documento tuyo · ${fuente.cita}` : fuente.cita}
      onClick={() => alPulsar(etiqueta)}
      aria-label={`${esDoc ? "Documento" : "Norma"} ${etiqueta}: ${
        fuente.cita
      }. Pulsa para ver el texto.`}
    >
      {etiqueta}
    </button>
  );
}

/** Sustituye [Fn] por un chip en los nodos de texto, dejando el resto igual. */
function conCitas(hijos, porEtiqueta, alPulsar) {
  return Children.map(hijos, (hijo) => {
    if (typeof hijo !== "string") return hijo;
    const trozos = [];
    let cursor = 0;
    for (const m of hijo.matchAll(RE_CITA)) {
      if (m.index > cursor) trozos.push(hijo.slice(cursor, m.index));
      trozos.push(
        <ChipCita
          key={`${m.index}-${m[1]}`}
          etiqueta={m[1]}
          fuente={porEtiqueta.get(m[1])}
          alPulsar={alPulsar}
        />
      );
      cursor = m.index + m[0].length;
    }
    if (!trozos.length) return hijo;
    if (cursor < hijo.length) trozos.push(hijo.slice(cursor));
    return trozos;
  });
}

function Mensaje({ mensaje, indice }) {
  const [abierta, setAbierta] = useState(null);

  if (mensaje.rol === "usuario") {
    return <div className="msg usuario">{mensaje.texto}</div>;
  }

  const porEtiqueta = new Map(
    [...(mensaje.fuentes ?? []), ...(mensaje.documentos ?? [])].map((f) => [
      f.etiqueta,
      f,
    ])
  );

  const idFuente = (etiqueta) => `fuente-${indice}-${etiqueta}`;

  function abrirFuente(etiqueta) {
    setAbierta(etiqueta);
    // El panel puede estar fuera de la vista tras una respuesta larga.
    requestAnimationFrame(() =>
      document
        .getElementById(idFuente(etiqueta))
        ?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    );
  }

  const conChips = (props) => conCitas(props.children, porEtiqueta, abrirFuente);

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
      {/* Solo mientras redacta. Una vez terminada, la respuesta ya lleva sus
          citas a la vista y el rótulo no aportaba nada. */}
      {mensaje.generando && (
        <p className="ia-cab" aria-live="polite">
          <Sparkles size={14} aria-hidden="true" />
          CARLOS está respondiendo…
        </p>
      )}

      {mensaje.respuesta ? (
        <div className="prosa">
          <ReactMarkdown
            components={{
              p: (props) => <p>{conChips(props)}</p>,
              li: (props) => <li>{conChips(props)}</li>,
              strong: (props) => <strong>{conChips(props)}</strong>,
              em: (props) => <em>{conChips(props)}</em>,
              td: (props) => <td>{conChips(props)}</td>,
            }}
          >
            {mensaje.respuesta}
          </ReactMarkdown>
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
              <Fuente
                key={f.etiqueta}
                id={idFuente(f.etiqueta)}
                fuente={f}
                abierto={abierta === f.etiqueta}
                alAlternar={() =>
                  setAbierta((v) => (v === f.etiqueta ? null : f.etiqueta))
                }
              />
            ))}
          </ul>
        </details>
      )}

      {mensaje.documentos?.length > 0 && (
        <details className="fuentes docs-citados" open>
          <summary>
            <FileText size={14} aria-hidden="true" />
            {mensaje.documentos.length} de tus documentos
            <span className="docs-marca">no es normativa</span>
          </summary>
          <ul>
            {mensaje.documentos.map((d) => (
              <Fuente
                key={d.etiqueta}
                id={idFuente(d.etiqueta)}
                fuente={d}
                abierto={abierta === d.etiqueta}
                alAlternar={() =>
                  setAbierta((v) => (v === d.etiqueta ? null : d.etiqueta))
                }
              />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

export default function App() {
  const { usuario, resuelta, salir } = useSesion();
  const [conversaciones, setConversaciones] = useState([]);
  const [conversacion, setConversacion] = useState(null);
  const [mensajes, setMensajes] = useState([]);
  const [entrada, setEntrada] = useState("");
  const [cargando, setCargando] = useState(false);
  const [corpus, setCorpus] = useState([]);
  const [materias, setMaterias] = useState([]);
  const [estado, setEstado] = useState(null);
  const finRef = useRef(null);
  // Si el usuario sube a releer, deja de estar "pegado" y el autoscroll calla.
  const pegadoAlFinal = useRef(true);
  const [oscuro, alternarTema] = useTema();

  useEffect(() => {
    salud()
      .then(setEstado)
      .catch(() => setEstado({ ok: false }));
    normas()
      .then(setCorpus)
      .catch(() => setCorpus([]));
  }, []);

  const refrescarConversaciones = () =>
    listarConversaciones()
      .then(setConversaciones)
      .catch(() => setConversaciones([]));

  useEffect(() => {
    if (!usuario) {
      setConversaciones([]);
      setConversacion(null);
      setMensajes([]);
      return;
    }
    refrescarConversaciones();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [usuario?.id]);

  async function abrirConversacion(id) {
    setConversacion(id);
    try {
      setMensajes(await cargarMensajes(id));
    } catch {
      setMensajes([]);
    }
  }

  function nuevaConversacion() {
    setConversacion(null);
    setMensajes([]);
  }

  async function quitarConversacion(id) {
    try {
      await borrarConversacion(id);
      if (id === conversacion) nuevaConversacion();
      await refrescarConversaciones();
    } catch {
      /* si falla, la lista se queda como estaba */
    }
  }

  // El streaming reescribe `mensajes` con cada fragmento, varias veces por
  // segundo. Un scroll suave por fragmento no llega a terminar antes de que el
  // siguiente lo reinicie —de ahí el temblor— y encima secuestra al usuario
  // que ha subido a leer una fuente. Así que: solo se auto-desplaza si ya
  // estaba pegado al final, e instantáneo mientras escribe.
  function alScroll(e) {
    const el = e.currentTarget;
    pegadoAlFinal.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < UMBRAL_PEGADO;
  }

  useEffect(() => {
    if (!pegadoAlFinal.current) return;
    finRef.current?.scrollIntoView({
      behavior: cargando ? "auto" : "smooth",
      block: "end",
    });
  }, [mensajes, cargando]);

  async function enviar(texto) {
    const consulta = (texto ?? entrada).trim();
    if (!consulta || cargando) return;

    setEntrada("");
    setCargando(true);
    // Enviar es una acción deliberada: aquí sí queremos seguir la respuesta
    // nueva aunque el usuario estuviera leyendo más arriba.
    pegadoAlFinal.current = true;

    // El hueco del asistente se crea vacío y se va rellenando: primero las
    // fuentes, luego el texto fragmento a fragmento.
    let indice;
    // `orden` en la base de datos es la posición del mensaje del usuario; el
    // del asistente va justo detrás. Se calcula aquí, con la longitud previa,
    // y no al guardar: para entonces el estado ya creció.
    let ordenUsuario;
    setMensajes((m) => {
      ordenUsuario = m.length;
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
    let fuentesFinales = [];
    let documentosFinales = [];
    let advertenciasFinales = [];

    try {
      await consultarStream(consulta, materias, (evento, datos) => {
        if (evento === "fuentes") {
          fuentesFinales = datos.fuentes ?? [];
          documentosFinales = datos.documentos ?? [];
          advertenciasFinales = datos.advertencias ?? [];
          parchear({
            fuentes: fuentesFinales,
            documentos: documentosFinales,
            advertencias: advertenciasFinales,
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
      let diagramaFinal = null;
      if (llevaDiagrama && acumulado) {
        try {
          const { diagrama } = await pedirDiagrama(acumulado);
          diagramaFinal = diagrama;
          parchear({ diagrama, cargandoDiagrama: false });
        } catch {
          parchear({ cargandoDiagrama: false });
        }
      }

      // Se guarda al final y no fragmento a fragmento: escribir en cada delta
      // serían decenas de escrituras por respuesta, y una respuesta a medias
      // no es algo que nadie quiera recuperar.
      await persistir({
        consulta,
        ordenUsuario,
        respuesta: acumulado,
        fuentes: fuentesFinales,
        documentos: documentosFinales,
        advertencias: advertenciasFinales,
        diagrama: diagramaFinal,
      });
    } catch (e) {
      parchear({ error: e.message, generando: false, cargandoDiagrama: false });
    } finally {
      setCargando(false);
    }
  }

  /**
   * Escribe la pareja pregunta/respuesta en el historial.
   *
   * Nunca tumba la conversación en curso: si Supabase falla, la respuesta ya
   * está en pantalla y perderla por no poder archivarla sería el peor de los
   * dos resultados.
   */
  async function persistir({
    consulta,
    ordenUsuario,
    respuesta,
    fuentes,
    documentos,
    advertencias,
    diagrama,
  }) {
    if (!usuario || !respuesta) return;
    try {
      let id = conversacion;
      if (!id) {
        const nueva = await crearConversacion(usuario.id, tituloDe(consulta));
        id = nueva.id;
        setConversacion(id);
      }
      await guardarMensaje({
        conversacionId: id,
        orden: ordenUsuario,
        rol: "usuario",
        contenido: consulta,
      });
      await guardarMensaje({
        conversacionId: id,
        orden: ordenUsuario + 1,
        rol: "asistente",
        contenido: respuesta,
        advertencias,
        diagrama,
        fuentes,
        documentos,
      });
      await refrescarConversaciones();
    } catch (e) {
      console.warn("No se pudo guardar en el historial:", e.message);
    }
  }

  function alternarMateria(materia) {
    setMaterias((ms) =>
      ms.includes(materia) ? ms.filter((m) => m !== materia) : [...ms, materia]
    );
  }

  // Con cuentas configuradas hay tres estados, y saltarse el intermedio hacía
  // parpadear el formulario de login en cada recarga antes de que Supabase
  // restaurase la sesión guardada.
  if (hayCuentas && !resuelta) {
    return (
      <div className="auth-pantalla">
        <Loader2 size={22} className="gira" aria-hidden="true" />
      </div>
    );
  }
  if (hayCuentas && !usuario) return <Auth />;

  return (
    <div className="app">
      <header className="cabecera">
        <div className="marca">
          {/* La marca sola, sin el eslogan: a este tamaño "Building a better
              working world" sería una mancha gris. El lockup completo está en
              public/ey-logo.png para usos con más espacio. */}
          <img
            className="logo-ey"
            src="/ey-logo-marca.png"
            alt="EY"
            width="27"
            height="28"
          />
          <h1>
            <abbr title="Compliance &amp; Audit Regulatory Logic Operational System">
              CARLOS
            </abbr>
            <span className="marca-expansion">
              Compliance Audit Regulatory Logic Operational System
            </span>
          </h1>
        </div>

        {estado && (
          <p className="estado-global">
            {estado.ok ? (
              <>
                <span
                  title="Artículos, disposiciones complementarias y cláusulas que el asistente puede consultar y citar."
                >
                  {estado.unidades_indexadas} artículos consultables
                </span>
                <span aria-hidden="true">·</span>
                <span
                  title={`Unidad Impositiva Tributaria: valor de referencia que fija el Estado cada año y sobre el que se calculan las multas. ${estado.uit.fuente}`}
                >
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

        <button
          className="tema"
          onClick={alternarTema}
          aria-pressed={oscuro}
          title={`Cambiar a modo ${oscuro ? "claro" : "oscuro"}`}
        >
          {oscuro ? (
            <Sun size={14} aria-hidden="true" />
          ) : (
            <Moon size={14} aria-hidden="true" />
          )}
          {oscuro ? "Claro" : "Oscuro"}
        </button>

        {usuario && (
          <div className="sesion">
            <span className="sesion-quien" title={usuario.email}>
              {usuario.email}
            </span>
            <button className="tema" onClick={salir} title="Cerrar sesión">
              <LogOut size={14} aria-hidden="true" />
              Salir
            </button>
          </div>
        )}
      </header>

      <div className="cuerpo">
        <aside className="lateral">
          {usuario && (
            <Historial
              conversaciones={conversaciones}
              activa={conversacion}
              alAbrir={abrirConversacion}
              alNueva={nuevaConversacion}
              alBorrar={quitarConversacion}
            />
          )}

          {usuario && <Documentos />}

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
                        {n.unidades} artículos
                      </span>
                      {n.requiere_cotejo && (
                        <span
                          className="aviso-corpus"
                          title="El PDF de origen es un escaneo sin texto digital. Se leyó con reconocimiento óptico, que puede introducir errores, así que conviene contrastar las citas con la versión oficial."
                        >
                          <ScanLine size={11} aria-hidden="true" />
                          Texto escaneado, contrastar con la fuente oficial
                        </span>
                      )}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
            {materias.length === 0 && (
              <p className="pista">Sin filtro: busca en todo el corpus.</p>
            )}
          </section>

          <GrafoNormas />
          <CalculadoraMultas />
        </aside>

        <main className="chat">
          <div className="mensajes" onScroll={alScroll}>
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
              <Mensaje key={i} mensaje={m} indice={i} />
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

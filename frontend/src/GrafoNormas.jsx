import { useEffect, useState } from "react";
import { Network } from "lucide-react";
import Mermaid from "./Mermaid";
import { grafo as pedirGrafo } from "./api";

// Cómo se lee cada relación en el diagrama. Las formas pasivas se dan la
// vuelta al pintar: "la 30424 es modificada por la 30835" se dibuja como
// "30835 --modifica--> 30424", que es la dirección en la que se lee el efecto.
const ETIQUETAS = {
  modifica_a: { texto: "modifica", invertir: false },
  modificada_por: { texto: "modifica", invertir: true },
  reglamenta_a: { texto: "reglamenta", invertir: false },
  reglamentada_por: { texto: "reglamenta", invertir: true },
  deroga_a: { texto: "deroga", invertir: false },
  derogada_por: { texto: "deroga", invertir: true },
  sustituye_a: { texto: "sustituye", invertir: false },
  complementa_a: { texto: "complementa", invertir: false },
};

/** Mermaid no acepta cualquier cosa como identificador de nodo. */
const id = (s) => "n_" + s.replace(/[^a-zA-Z0-9]/g, "_");

/** Ni corchetes ni comillas dentro de la etiqueta de un nodo. */
const limpiar = (s) => s.replace(/["[\]{}()|]/g, " ").replace(/\s+/g, " ").trim();

function aMermaid({ nodos, aristas }) {
  const lineas = ["flowchart LR"];

  for (const n of nodos) {
    // El nombre completo de una ley no cabe en un nodo: se parte en dos
    // líneas y se recorta, que para orientarse en el grafo basta.
    const nombre = limpiar(n.nombre);
    const corto = nombre.length > 38 ? nombre.slice(0, 36) + "…" : nombre;
    const marcas = [];
    if (!n.en_corpus) marcas.push("no cargada");
    if (n.estado_texto === "original") marcas.push("⚠ texto original");
    if (n.requiere_cotejo) marcas.push("⚠ OCR");

    // Sin HTML en la etiqueta: Mermaid corre con securityLevel "strict" y
    // escapa las etiquetas, así que un <br/> saldría como texto literal.
    const etiqueta = marcas.length ? `${corto} — ${marcas.join(" · ")}` : corto;

    lineas.push(`  ${id(n.id)}["${etiqueta}"]`);
  }

  for (const a of aristas) {
    const meta = ETIQUETAS[a.tipo] ?? { texto: a.tipo, invertir: false };
    const [desde, hasta] = meta.invertir
      ? [a.destino, a.origen]
      : [a.origen, a.destino];
    lineas.push(`  ${id(desde)} -->|${meta.texto}| ${id(hasta)}`);
  }

  // Las normas ausentes van con trazo discontinuo: el grafo sirve también de
  // mapa de cobertura, y lo que falta tiene que verse como tal.
  const ausentes = nodos.filter((n) => !n.en_corpus).map((n) => id(n.id));
  if (ausentes.length) {
    lineas.push(
      `  classDef ausente stroke-dasharray: 4 3, opacity: 0.65;`,
      `  class ${ausentes.join(",")} ausente;`
    );
  }

  return lineas.join("\n");
}

export default function GrafoNormas() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    pedirGrafo()
      .then(setDatos)
      .catch(() => setError(true));
  }, []);

  if (error || !datos || !datos.nodos.length) return null;

  const faltan = datos.nodos.filter((n) => !n.en_corpus).length;

  return (
    <section className="grafo">
      <details>
        <summary className="rotulo">
          <Network size={14} aria-hidden="true" />
          Trazabilidad entre normas
        </summary>

        <p className="pista">
          Qué norma modifica o reglamenta a cuál.
          {faltan > 0 && (
            <>
              {" "}
              <strong>{faltan}</strong>{" "}
              {faltan === 1 ? "está referida" : "están referidas"} por el corpus
              pero {faltan === 1 ? "no está cargada" : "no están cargadas"}: se
              dibujan con trazo discontinuo.
            </>
          )}
        </p>

        <Mermaid codigo={aMermaid(datos)} />
      </details>
    </section>
  );
}

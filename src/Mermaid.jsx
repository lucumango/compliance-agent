import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  securityLevel: "strict",
  themeVariables: {
    primaryColor: "#e7f2f0",
    primaryBorderColor: "#0e6f6b",
    primaryTextColor: "#0a4f4c",
    lineColor: "#5a6b68",
    fontFamily: "system-ui, sans-serif",
  },
});

let contador = 0;

export default function Mermaid({ codigo }) {
  const contenedor = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!codigo) return;
    let cancelado = false;

    // El modelo genera el diagrama, así que puede venir sintácticamente
    // inválido. Renderizar en un try deja el resto de la respuesta intacta.
    mermaid
      .render(`diagrama-${contador++}`, codigo)
      .then(({ svg }) => {
        if (!cancelado && contenedor.current) {
          contenedor.current.innerHTML = svg;
          setError(null);
        }
      })
      .catch(() => {
        if (!cancelado) setError("No se pudo dibujar el diagrama.");
      });

    return () => {
      cancelado = true;
    };
  }, [codigo]);

  if (error) {
    return (
      <details className="diagrama-error">
        <summary>{error} Ver código.</summary>
        <pre>{codigo}</pre>
      </details>
    );
  }

  return <div className="diagrama" ref={contenedor} />;
}

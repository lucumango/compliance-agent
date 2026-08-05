import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  securityLevel: "strict",
  // Paleta EY. Los nodos van en gris claro con borde y texto en EY Black; el
  // amarillo se reserva para los rombos de decisión, donde actúa como fondo
  // con texto oscuro encima (nunca como texto amarillo sobre blanco).
  themeVariables: {
    fontFamily: "EYInterstate, Arial, sans-serif",
    fontSize: "14px",
    primaryColor: "#F2F2F2",
    primaryBorderColor: "#161D23",
    primaryTextColor: "#161D23",
    secondaryColor: "#FFE600",
    secondaryBorderColor: "#161D23",
    secondaryTextColor: "#161D23",
    tertiaryColor: "#FFFFFF",
    tertiaryBorderColor: "#CCCCCC",
    tertiaryTextColor: "#333333",
    lineColor: "#333333",
    textColor: "#161D23",
    mainBkg: "#F2F2F2",
    nodeBorder: "#161D23",
    clusterBkg: "#FFFFFF",
    clusterBorder: "#E8E8E8",
    edgeLabelBackground: "#FFFFFF",
  },
  flowchart: { curve: "linear", useMaxWidth: true },
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

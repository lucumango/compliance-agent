import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";

// Paleta EY. Los nodos van en gris con borde y texto de alto contraste; el
// amarillo se reserva para los rombos de decisión, donde actúa como fondo con
// texto oscuro encima (nunca como texto amarillo sobre claro).
//
// Mermaid no lee variables CSS: resuelve su tema al inicializar y necesita
// valores literales. Por eso la paleta se duplica aquí en vez de reutilizar
// los tokens de App.css, y por eso hay que reinicializar al cambiar de tema.
const TEMA_CLARO = {
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
};

const TEMA_OSCURO = {
  primaryColor: "#2B343C",
  primaryBorderColor: "#8B959E",
  primaryTextColor: "#F2F2F2",
  secondaryColor: "#FFE600",
  secondaryBorderColor: "#FFE600",
  secondaryTextColor: "#161D23",
  tertiaryColor: "#1B2229",
  tertiaryBorderColor: "#3A444D",
  tertiaryTextColor: "#CBD3DA",
  lineColor: "#8B959E",
  textColor: "#F2F2F2",
  mainBkg: "#2B343C",
  nodeBorder: "#8B959E",
  clusterBkg: "#1B2229",
  clusterBorder: "#3A444D",
  edgeLabelBackground: "#1B2229",
};

function esOscuroAhora() {
  const elegido = document.documentElement.getAttribute("data-theme");
  if (elegido) return elegido === "dark";
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

/** Sigue el tema activo, venga del sistema o de la elección del usuario. */
function useEsOscuro() {
  const [oscuro, setOscuro] = useState(esOscuroAhora);

  useEffect(() => {
    const actualizar = () => setOscuro(esOscuroAhora());

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", actualizar);

    // El conmutador escribe data-theme en el <html>; observarlo evita tener
    // que pasar el tema como prop por todo el árbol.
    const observador = new MutationObserver(actualizar);
    observador.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    return () => {
      mq.removeEventListener("change", actualizar);
      observador.disconnect();
    };
  }, []);

  return oscuro;
}

let contador = 0;

export default function Mermaid({ codigo }) {
  const contenedor = useRef(null);
  const [error, setError] = useState(null);
  const oscuro = useEsOscuro();

  useEffect(() => {
    if (!codigo) return;
    let cancelado = false;

    mermaid.initialize({
      startOnLoad: false,
      theme: "base",
      // El código del diagrama lo genera un modelo: no es contenido de
      // confianza y no puede ejecutar scripts ni inyectar HTML.
      securityLevel: "strict",
      themeVariables: {
        fontFamily: "Nunito, Segoe UI, system-ui, sans-serif",
        fontSize: "14px",
        ...(oscuro ? TEMA_OSCURO : TEMA_CLARO),
      },
      flowchart: { curve: "linear", useMaxWidth: true },
    });

    // El modelo genera el diagrama, así que puede venir sintácticamente
    // inválido. Renderizar en un catch deja el resto de la respuesta intacta.
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
  }, [codigo, oscuro]);

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

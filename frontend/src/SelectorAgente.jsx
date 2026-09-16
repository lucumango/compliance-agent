/**
 * Elegir con qué agente se habla.
 *
 * El alcance que se pinta aquí es el MISMO texto que va al prompt del modelo,
 * servido por /api/agentes. No es una versión de marketing escrita aparte: si
 * las dos se escribieran por separado acabarían diciendo cosas distintas, y la
 * que el usuario lee no sería la que gobierna la respuesta.
 */
import { Bot } from "lucide-react";

export default function SelectorAgente({ agentes, activo, alCambiar }) {
  if (agentes.length < 2) return null;
  const actual = agentes.find((a) => a.id === activo);

  return (
    <section className="agentes">
      <p className="rotulo">
        <Bot size={14} aria-hidden="true" /> Agente
      </p>

      <div className="agentes-fila" role="tablist" aria-label="Agente">
        {agentes.map((a) => {
          // Un agente sin su corpus se enseña igual, deshabilitado y diciendo
          // qué le falta. Ocultarlo haría creer que no existe; dejarlo elegir
          // haría que respondiera CARLOS en su nombre sin que se notara.
          const apagado = a.activo === false;
          const clase = ["agente", a.id === activo && "activo", apagado && "apagado"]
            .filter(Boolean)
            .join(" ");
          return (
            <button
              key={a.id}
              type="button"
              role="tab"
              aria-selected={a.id === activo}
              aria-disabled={apagado}
              disabled={apagado}
              className={clase}
              onClick={() => !apagado && alCambiar(a.id)}
              title={apagado ? `Falta corpus: ${a.faltan.join(", ")}` : a.acronimo}
            >
              <span className="agente-nombre">{a.nombre}</span>
              <span className="agente-area">{apagado ? "Falta corpus" : a.area}</span>
            </button>
          );
        })}
      </div>

      {actual && actual.guarda_historial === false && (
        <p className="aviso-corpus">
          Las conversaciones con {actual.nombre} no se guardan en el historial.
          No escribas aquí datos de denunciantes ni de denuncias concretas.
        </p>
      )}

      {actual && (
        <p className="pista agente-alcance">
          <strong>Responde:</strong> {actual.alcance}
          <br />
          <strong>No responde:</strong> {actual.fuera_de_alcance}
        </p>
      )}
    </section>
  );
}

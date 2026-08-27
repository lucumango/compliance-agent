import { useState } from "react";
import { Loader2, LogIn, UserPlus } from "lucide-react";
import { supabase, traducirError } from "./supabase";

/**
 * Entrada y alta de cuenta.
 *
 * Un solo formulario con dos modos en vez de dos pantallas: los campos son los
 * mismos y cambiar de idea es lo más frecuente que hace alguien aquí.
 *
 * Qué NO hace, y conviene tener presente antes de abrirlo a gente de fuera:
 * no valida el dominio del correo, así que cualquiera con la URL puede darse
 * de alta. Restringirlo se hace en Supabase —confirmación por correo activada,
 * o una política de dominio permitido— no en este componente, porque una
 * comprobación en el navegador se salta llamando a la API directamente.
 */
export default function Auth() {
  const [modo, setModo] = useState("entrar");
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [nombre, setNombre] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

  const registrando = modo === "registrar";

  async function enviar(e) {
    e.preventDefault();
    if (cargando) return;
    setCargando(true);
    setError(null);
    setAviso(null);

    try {
      if (registrando) {
        const { data, error } = await supabase.auth.signUp({
          email: correo.trim(),
          password: clave,
          // El trigger de 001_historial.sql lee `nombre` de aquí para rellenar
          // el perfil sin que la aplicación tenga que acordarse.
          options: { data: { nombre: nombre.trim() || correo.trim() } },
        });
        if (error) throw error;
        // Con confirmación por correo activada no hay sesión todavía; sin
        // ella, `onAuthStateChange` entra solo y este aviso ni se ve.
        if (!data.session) {
          setAviso("Cuenta creada. Confirma el correo que te acabamos de enviar.");
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email: correo.trim(),
          password: clave,
        });
        if (error) throw error;
      }
    } catch (e) {
      setError(traducirError(e));
    } finally {
      setCargando(false);
    }
  }

  return (
    <div className="auth-pantalla">
      <form className="auth-caja" onSubmit={enviar}>
        <h1>{registrando ? "Crear cuenta" : "Entrar"}</h1>
        <p className="auth-pie">
          Tu historial y tus documentos quedan asociados a esta cuenta y no son
          visibles para nadie más.
        </p>

        {registrando && (
          <label>
            Nombre
            <input
              type="text"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              autoComplete="name"
              placeholder="Como quieres que te llamemos"
            />
          </label>
        )}

        <label>
          Correo
          <input
            type="email"
            required
            value={correo}
            onChange={(e) => setCorreo(e.target.value)}
            autoComplete="email"
          />
        </label>

        <label>
          Contraseña
          <input
            type="password"
            required
            minLength={6}
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            autoComplete={registrando ? "new-password" : "current-password"}
          />
        </label>

        {error && <p className="auth-error">{error}</p>}
        {aviso && <p className="auth-aviso">{aviso}</p>}

        <button className="btn-primary" type="submit" disabled={cargando}>
          {cargando ? (
            <Loader2 size={16} className="gira" aria-hidden="true" />
          ) : registrando ? (
            <UserPlus size={16} aria-hidden="true" />
          ) : (
            <LogIn size={16} aria-hidden="true" />
          )}
          {registrando ? "Crear cuenta" : "Entrar"}
        </button>

        <button
          type="button"
          className="auth-cambio"
          onClick={() => {
            setModo(registrando ? "entrar" : "registrar");
            setError(null);
            setAviso(null);
          }}
        >
          {registrando
            ? "¿Ya tienes cuenta? Entra"
            : "¿No tienes cuenta? Crea una"}
        </button>
      </form>
    </div>
  );
}

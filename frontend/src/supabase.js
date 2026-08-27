/**
 * Cliente de Supabase, o `null` si el despliegue no lo tiene configurado.
 *
 * Devolver null en vez de lanzar es deliberado: la aplicación funcionaba antes
 * de que existieran las cuentas y tiene que seguir funcionando sin ellas. Con
 * VITE_SUPABASE_URL sin definir hay chat y no hay login, historial ni
 * documentos, que es exactamente el estado en el que corre en local.
 *
 * Aquí solo va la clave `anon`. La `service_role` salta row level security por
 * diseño y no debe existir en el navegador bajo ningún concepto.
 */
import { createClient } from "@supabase/supabase-js";

const URL = (import.meta.env.VITE_SUPABASE_URL ?? "").trim().replace(/\/+$/, "");
const ANON = (import.meta.env.VITE_SUPABASE_ANON_KEY ?? "").trim();

export const hayCuentas = Boolean(URL && ANON);

export const supabase = hayCuentas
  ? createClient(URL, ANON, {
      auth: {
        // La sesión sobrevive a recargar la página y el token se renueva solo
        // antes de caducar; sin esto habría que volver a entrar cada hora.
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;

/** Traduce los mensajes de Supabase Auth, que llegan en inglés. */
export function traducirError(error) {
  const m = (error?.message ?? "").toLowerCase();
  if (m.includes("invalid login credentials"))
    return "Correo o contraseña incorrectos.";
  if (m.includes("email not confirmed"))
    return "Falta confirmar el correo. Revisa tu bandeja.";
  if (m.includes("user already registered"))
    return "Ese correo ya tiene cuenta. Entra en vez de registrarte.";
  if (m.includes("password should be at least"))
    return "La contraseña debe tener al menos 6 caracteres.";
  if (m.includes("rate limit") || m.includes("too many"))
    return "Demasiados intentos. Espera un minuto.";
  return error?.message ?? "No se pudo completar la operación.";
}

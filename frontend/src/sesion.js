/**
 * Sesión del usuario: quién es, y el token que hay que mandarle al backend.
 *
 * El token se guarda además en un módulo aparte (`api.js` lo lee) porque las
 * peticiones se lanzan desde funciones que no son componentes y no pueden
 * llamar a un hook.
 */
import { useEffect, useState } from "react";
import { hayCuentas, supabase } from "./supabase";
import { fijarToken } from "./api";

export function useSesion() {
  const [sesion, setSesion] = useState(null);
  // `null` mientras no se sabe: sin esto la pantalla de login parpadea en cada
  // recarga antes de que Supabase restaure la sesión de localStorage.
  const [resuelta, setResuelta] = useState(!hayCuentas);

  useEffect(() => {
    if (!supabase) return;

    supabase.auth.getSession().then(({ data }) => {
      setSesion(data.session ?? null);
      fijarToken(data.session?.access_token ?? null);
      setResuelta(true);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_evento, s) => {
      setSesion(s ?? null);
      fijarToken(s?.access_token ?? null);
      setResuelta(true);
    });

    return () => sub.subscription.unsubscribe();
  }, []);

  return {
    sesion,
    resuelta,
    usuario: sesion?.user ?? null,
    salir: () => supabase?.auth.signOut(),
  };
}

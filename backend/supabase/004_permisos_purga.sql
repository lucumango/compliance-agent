-- Cierra las funciones de purga al público.
--
-- Se ejecuta después de 003_gobernanza.sql, en el editor SQL de Supabase.
--
-- EL FALLO. Postgres concede EXECUTE a PUBLIC en toda función nueva por
-- defecto. `purgar_historial` (de 001) y `purgar_auditoria` (de 003) son
-- `security definer`, así que corren con los permisos del dueño y se saltan
-- row level security por diseño — que es lo que necesitan para poder borrar
-- filas de todo el mundo.
--
-- Juntando las dos cosas: PostgREST las expone en /rest/v1/rpc/, y la clave
-- `anon` viaja en el bundle del frontend, o sea que es pública. Cualquiera con
-- esa clave podía llamar a
--
--     POST /rest/v1/rpc/purgar_historial  {"dias": 0}
--
-- y borrar las conversaciones de todos los usuarios. Con purgar_auditoria,
-- ademas, borrar el rastro de haberlo hecho.
--
-- Verificado contra el proyecto real antes de escribir esto: las dos
-- respondían 200 a una llamada con la clave anon.
--
-- LA CORRECCIÓN. Quitarles el EXECUTE a todo el mundo. Son funciones de
-- mantenimiento: las invoca pg_cron —que corre como superusuario— o una
-- persona desde el editor SQL. Ninguna petición HTTP tiene por qué alcanzarlas.

revoke execute on function public.purgar_historial(int)
  from public, anon, authenticated;

revoke execute on function public.purgar_auditoria(int)
  from public, anon, authenticated;

-- Y que no vuelva a pasar con la siguiente función que alguien añada: a partir
-- de ahora, toda función nueva creada en public por este rol nace sin EXECUTE
-- para los roles del API.
alter default privileges in schema public
  revoke execute on functions from public, anon, authenticated;

-- `buscar_fragmentos` se queda como está, y es correcto: es `security invoker`
-- —corre con los permisos de quien llama, así que las políticas se aplican— y
-- el frontend la necesita. La diferencia entre las dos clases de función es
-- justo esta, y por eso conviene mirarla cada vez que se escribe una.

-- Trazabilidad de las respuestas y registro de auditoría.
--
-- Se ejecuta después de 002_documentos.sql, en el editor SQL de Supabase.
--
-- Esto es lo que faltaba para poder decir que el sistema sigue ISO/IEC 42001
-- en lo esencial. El razonamiento está en docs/GOBERNANZA.md. En resumen:
--
--   * una respuesta guardada tiene que decir QUÉ la produjo, o no se puede
--     reproducir ni auditar. El modelo cambia solo cuando se agota una cuota,
--     y el prompt se edita;
--   * tiene que existir un registro de quién consultó qué, y ese registro no
--     puede poder borrarlo quien lo generó.

-- ----------------------------------------------- versión del prompt en cada mensaje
-- `modelo` ya existía y nadie lo rellenaba. Ahora la API lo devuelve, junto
-- con la versión del prompt, y el frontend guarda las dos.
alter table public.mensajes
  add column if not exists prompt_version text;

comment on column public.mensajes.prompt_version is
  'Etiqueta + hash de rag.answer._SISTEMA que produjo la respuesta. '
  'Sin esto, una respuesta guardada no se puede reproducir.';

comment on column public.mensajes.modelo is
  'Modelo que respondió de verdad, no el configurado: la cadena de respaldo '
  'degrada sola cuando se agota una cuota.';

-- --------------------------------------------------------- eventos_auditoria
-- Quién usó el sistema, cuándo y con qué. Sin el texto de la consulta.
--
-- La consulta NO se guarda aquí a propósito. Lleva datos del caso —nombres,
-- DNI, montos— y la anonimización es de superficie: reconoce patrones, no
-- nombres. El historial de chat ya guarda el texto para quien lo escribió y
-- bajo su propia política; un registro de auditoría que además lo duplique
-- multiplica la exposición sin añadir nada que un auditor necesite.
--
-- Lo que sí queda: quién, cuándo, qué modelo, qué versión del prompt, y qué
-- normas se citaron. Con eso se responde "¿de dónde salió esta respuesta?" y
-- "¿quién estuvo consultando la Ley 30424 en marzo?".
create table if not exists public.eventos_auditoria (
  id              uuid primary key default gen_random_uuid(),
  usuario_id      uuid not null references public.perfiles(id) on delete cascade,
  ocurrido_en     timestamptz not null default now(),
  accion          text not null
                  check (accion in ('consulta', 'documento_subido',
                                    'documento_borrado')),
  modelo          text,
  prompt_version  text,
  -- Cuántas unidades tenía el índice. Identifica el corpus sin depender de que
  -- alguien acuerde de escribir una versión.
  corpus_unidades int,
  -- Identificadores de norma, no el texto citado. Basta para reconstruir de
  -- qué se habló y no arrastra el contenido.
  normas_citadas  text[] not null default '{}',
  documentos_citados int not null default 0,
  ok              boolean not null default true
);

create index if not exists auditoria_por_usuario
  on public.eventos_auditoria (usuario_id, ocurrido_en desc);

create index if not exists auditoria_por_fecha
  on public.eventos_auditoria (ocurrido_en desc);

-- --------------------------------------------------------------------- RLS
alter table public.eventos_auditoria enable row level security;

-- Deliberadamente NO hay `for all`. Cada quien puede escribir sus eventos y
-- leer los suyos, y nadie puede modificarlos ni borrarlos: sin política de
-- update ni de delete, PostgREST los rechaza. Un registro de auditoría que su
-- autor puede borrar no es un registro de auditoría.
--
-- Para leerlo entero —revisión, informe— se entra por el panel de Supabase,
-- que es donde vive la única credencial capaz de saltarse esto.
drop policy if exists "escribo mis eventos" on public.eventos_auditoria;
create policy "escribo mis eventos" on public.eventos_auditoria
  for insert with check (usuario_id = auth.uid());

drop policy if exists "leo mis eventos" on public.eventos_auditoria;
create policy "leo mis eventos" on public.eventos_auditoria
  for select using (usuario_id = auth.uid());

-- ----------------------------------------------------------------- retención
-- El mismo criterio que el historial: el plazo sale de la política de
-- retención de la organización, no de aquí. Se programa con pg_cron.
--
-- Va aparte de purgar_historial porque los dos plazos no tienen por qué ser el
-- mismo: la conversación es del usuario y el registro es de la organización.
create or replace function public.purgar_auditoria(dias int default 730)
returns int language plpgsql security definer set search_path = '' as $$
declare borradas int;
begin
  delete from public.eventos_auditoria
   where ocurrido_en < now() - (dias || ' days')::interval;
  get diagnostics borradas = row_count;
  return borradas;
end $$;

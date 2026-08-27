-- Documentos del usuario — subida, troceado e indexado vectorial.
--
-- Se ejecuta después de 001_historial.sql, en el editor SQL de Supabase.
--
-- La decisión de fondo está en docs/DOCUMENTOS.md. En resumen: los fragmentos
-- del usuario viven en Postgres y no en el índice numpy del corpus, porque
-- tienen dueño y el corpus no. Mezclarlos en el mismo fichero obligaría a
-- filtrar por usuario en cada búsqueda, y un filtro que se olvida una vez
-- filtra los documentos de un cliente a otro.

create extension if not exists vector;

-- ------------------------------------------------------------- documentos
create table if not exists public.documentos (
  id          uuid primary key default gen_random_uuid(),
  usuario_id  uuid not null references public.perfiles(id) on delete cascade,
  nombre      text not null,
  tipo        text not null check (tipo in ('pdf', 'docx')),
  bytes       int  not null,
  -- Evita reindexar el mismo archivo dos veces y detecta subidas duplicadas
  -- con nombre distinto.
  sha256      text not null,
  paginas     int,
  fragmentos  int  not null default 0,
  estado      text not null default 'procesando'
              check (estado in ('procesando', 'listo', 'error')),
  error       text,
  creado_en   timestamptz not null default now(),
  unique (usuario_id, sha256)
);

create index if not exists documentos_por_usuario
  on public.documentos (usuario_id, creado_en desc);

-- --------------------------------------------------- documento_fragmentos
-- 3072 dimensiones, las de gemini-embedding-2, para que el vector de la
-- consulta sirva igual contra el corpus y contra estos fragmentos.
--
-- NO lleva índice ANN a propósito: ivfflat y hnsw admiten hasta 2000
-- dimensiones, y reducir la dimensión aquí haría incomparables los scores con
-- los del corpus. A la escala de esto —decenas de documentos por usuario— el
-- barrido exacto tarda milisegundos. Si un usuario llegara a cientos de miles
-- de fragmentos habría que reducir dimensión en ambos lados a la vez.
create table if not exists public.documento_fragmentos (
  id            uuid primary key default gen_random_uuid(),
  documento_id  uuid not null
                references public.documentos(id) on delete cascade,
  orden         int  not null,
  pagina        int,
  texto         text not null,
  embedding     vector(3072) not null,
  unique (documento_id, orden)
);

create index if not exists fragmentos_por_documento
  on public.documento_fragmentos (documento_id, orden);

-- ---------------------------------------------------------------- busqueda
-- security invoker: la función corre con los permisos de quien llama, así que
-- las políticas de abajo se aplican y nadie puede leer fragmentos ajenos
-- aunque invoque la RPC directamente.
--
-- La consulta entra como texto y se castea dentro: PostgREST serializa los
-- argumentos como JSON y no sabe construir un vector de 3072 posiciones.
create or replace function public.buscar_fragmentos(
  consulta text,
  k int default 4,
  score_minimo real default 0.0
)
returns table (
  fragmento_id     uuid,
  documento_id     uuid,
  documento_nombre text,
  pagina           int,
  texto            text,
  score            real
)
language sql stable security invoker set search_path = public as $$
  select f.id, d.id, d.nombre, f.pagina, f.texto,
         -- pgvector devuelve distancia coseno en [0,2]; el resto del sistema
         -- razona en similitud, así que se invierte aquí y no en el cliente.
         (1 - (f.embedding <=> consulta::vector(3072)))::real as score
    from public.documento_fragmentos f
    join public.documentos d on d.id = f.documento_id
   where d.estado = 'listo'
     and (1 - (f.embedding <=> consulta::vector(3072))) >= score_minimo
   order by f.embedding <=> consulta::vector(3072)
   limit k;
$$;

-- --------------------------------------------------------------------- RLS
alter table public.documentos           enable row level security;
alter table public.documento_fragmentos enable row level security;

drop policy if exists "mis documentos" on public.documentos;
create policy "mis documentos" on public.documentos
  for all using (usuario_id = auth.uid())
          with check (usuario_id = auth.uid());

-- Los fragmentos heredan el dueño por la clave foránea, igual que los
-- mensajes heredan el suyo de la conversación.
drop policy if exists "fragmentos de mis documentos" on public.documento_fragmentos;
create policy "fragmentos de mis documentos" on public.documento_fragmentos
  for all using (exists (
    select 1 from public.documentos d
    where d.id = documento_fragmentos.documento_id and d.usuario_id = auth.uid()
  ));

-- --------------------------------------------- citas de documento en el historial
-- 001_historial.sql se escribió cuando la única fuente posible era un artículo
-- de una norma. Ahora una respuesta puede citar también un fragmento de un
-- documento del usuario, y el historial tiene que poder guardarlo.
--
-- `clase` va con default 'norma' para que las filas ya escritas sigan siendo
-- válidas, y `norma_id` pasa a admitir nulo porque un documento no pertenece a
-- ninguna norma.
alter table public.mensaje_fuentes
  add column if not exists clase text not null default 'norma';

do $$ begin
  alter table public.mensaje_fuentes
    add constraint mensaje_fuentes_clase_valida
    check (clase in ('norma', 'documento'));
exception when duplicate_object then null; end $$;

alter table public.mensaje_fuentes alter column norma_id drop not null;

-- Página del documento, cuando la fuente es un PDF. Nula para normas y DOCX.
alter table public.mensaje_fuentes
  add column if not exists pagina int;

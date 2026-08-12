-- Historial de chats — esquema inicial.
--
-- Se ejecuta en el editor SQL de Supabase, o con la CLI:
--     supabase db push
--
-- El razonamiento detrás de cada decisión está en docs/DATOS.md. En resumen:
--   * las citas se copian en vez de referenciarse, porque el corpus vive fuera
--     de Postgres y cambia;
--   * el aislamiento entre usuarios va en row-level security, no en el código.

-- ---------------------------------------------------------------- perfiles
-- Extiende auth.users, que gestiona Supabase, con lo que es nuestro.
create table if not exists public.perfiles (
  id         uuid primary key references auth.users(id) on delete cascade,
  nombre     text,
  rol        text not null default 'analista'
             check (rol in ('analista', 'admin')),
  creado_en  timestamptz not null default now()
);

-- Un perfil por cada alta, sin tener que acordarse desde la aplicación.
create or replace function public.crear_perfil()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.perfiles (id, nombre)
  values (new.id, coalesce(new.raw_user_meta_data->>'nombre', new.email));
  return new;
end $$;

drop trigger if exists al_crear_usuario on auth.users;
create trigger al_crear_usuario
  after insert on auth.users
  for each row execute function public.crear_perfil();

-- -------------------------------------------------------- corpus_versiones
-- Qué corpus respondió. El índice vive fuera de Postgres, así que se
-- identifica por el hash del fichero de vectores.
create table if not exists public.corpus_versiones (
  id           uuid primary key default gen_random_uuid(),
  hash_indice  text not null unique,
  unidades     int  not null,
  normas       jsonb not null default '[]',
  creado_en    timestamptz not null default now()
);

-- ----------------------------------------------------------- conversaciones
create table if not exists public.conversaciones (
  id              uuid primary key default gen_random_uuid(),
  usuario_id      uuid not null references public.perfiles(id) on delete cascade,
  titulo          text not null default 'Nueva consulta',
  creada_en       timestamptz not null default now(),
  actualizada_en  timestamptz not null default now(),
  archivada_en    timestamptz
);

create index if not exists conversaciones_por_usuario
  on public.conversaciones (usuario_id, actualizada_en desc);

-- ------------------------------------------------------------------ mensajes
create table if not exists public.mensajes (
  id                 uuid primary key default gen_random_uuid(),
  conversacion_id    uuid not null
                     references public.conversaciones(id) on delete cascade,
  -- Ordena la conversación. No usar creado_en: dos mensajes pueden caer en el
  -- mismo milisegundo y el orden dejaría de ser determinista.
  orden              int  not null,
  rol                text not null check (rol in ('usuario', 'asistente')),
  -- Texto tal como lo escribió el usuario. Ver docs/DATOS.md, decisión 2:
  -- puede contener datos personales, y la anonimización no cubre nombres.
  contenido          text not null,
  advertencias       text[] not null default '{}',
  diagrama           text,
  modelo             text,
  corpus_version_id  uuid references public.corpus_versiones(id),
  creado_en          timestamptz not null default now(),
  unique (conversacion_id, orden)
);

create index if not exists mensajes_por_conversacion
  on public.mensajes (conversacion_id, orden);

-- ----------------------------------------------------------- mensaje_fuentes
create table if not exists public.mensaje_fuentes (
  id         uuid primary key default gen_random_uuid(),
  mensaje_id uuid not null references public.mensajes(id) on delete cascade,
  etiqueta   text not null,
  -- Sin clave foránea a propósito: el corpus no está en Postgres.
  unidad_id  text not null,
  norma_id   text not null,
  -- Copias, no referencias: cuando el corpus se actualice, esta conversación
  -- debe seguir diciendo lo que dijo.
  cita       text not null,
  texto      text not null,
  score      real not null,
  unique (mensaje_id, etiqueta)
);

create index if not exists fuentes_por_mensaje
  on public.mensaje_fuentes (mensaje_id);

-- Sube actualizada_en al escribir en la conversación, para que la lista del
-- lateral se ordene por actividad real y no por fecha de creación.
create or replace function public.tocar_conversacion()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  update public.conversaciones
     set actualizada_en = now()
   where id = new.conversacion_id;
  return new;
end $$;

drop trigger if exists al_insertar_mensaje on public.mensajes;
create trigger al_insertar_mensaje
  after insert on public.mensajes
  for each row execute function public.tocar_conversacion();

-- ---------------------------------------------------------------------- RLS
alter table public.perfiles         enable row level security;
alter table public.conversaciones   enable row level security;
alter table public.mensajes         enable row level security;
alter table public.mensaje_fuentes  enable row level security;
alter table public.corpus_versiones enable row level security;

drop policy if exists "mi perfil" on public.perfiles;
create policy "mi perfil" on public.perfiles
  for all using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists "mis conversaciones" on public.conversaciones;
create policy "mis conversaciones" on public.conversaciones
  for all using (usuario_id = auth.uid())
          with check (usuario_id = auth.uid());

-- Mensajes y fuentes heredan el dueño por la cadena de claves foráneas, así
-- que no necesitan su propia columna usuario_id que mantener sincronizada.
drop policy if exists "mensajes de mis conversaciones" on public.mensajes;
create policy "mensajes de mis conversaciones" on public.mensajes
  for all using (exists (
    select 1 from public.conversaciones c
    where c.id = mensajes.conversacion_id and c.usuario_id = auth.uid()
  ));

drop policy if exists "fuentes de mis mensajes" on public.mensaje_fuentes;
create policy "fuentes de mis mensajes" on public.mensaje_fuentes
  for all using (exists (
    select 1 from public.mensajes m
    join public.conversaciones c on c.id = m.conversacion_id
    where m.id = mensaje_fuentes.mensaje_id and c.usuario_id = auth.uid()
  ));

-- El corpus es común: se lee, no se escribe desde el cliente.
drop policy if exists "corpus legible" on public.corpus_versiones;
create policy "corpus legible" on public.corpus_versiones
  for select using (auth.role() = 'authenticated');

-- --------------------------------------------------------------- retención
-- El plazo por defecto es un marcador, no una recomendación: debería salir de
-- la política de retención de la organización. Se programa con pg_cron.
create or replace function public.purgar_historial(dias int default 365)
returns int language plpgsql security definer set search_path = '' as $$
declare borradas int;
begin
  -- Basta con la conversación: mensajes y fuentes caen en cascada.
  delete from public.conversaciones
   where actualizada_en < now() - (dias || ' days')::interval;
  get diagnostics borradas = row_count;
  return borradas;
end $$;

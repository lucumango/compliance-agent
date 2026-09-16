-- Registrar los cotejos contra listas de sanciones y el padrón de SUNAT.
--
-- Se ejecuta después de 004_permisos_purga.sql.
--
-- 003 limitó `accion` a tres valores. DIEGO añade un cuarto: comprobar a un
-- tercero contra registros públicos. Es justo el tipo de uso que una revisión
-- quiere poder reconstruir —quién cotejó, cuándo, y si salió algo—, y sin esta
-- migración el evento se rechaza en silencio: auditoria.py atrapa el error para
-- no tumbar la respuesta, así que el cotejo funciona y no queda constancia.
--
-- El nombre o el RUC cotejado NO se guarda, por el mismo motivo por el que no
-- se guarda el texto de una consulta.

alter table public.eventos_auditoria
  drop constraint if exists eventos_auditoria_accion_check;

alter table public.eventos_auditoria
  add constraint eventos_auditoria_accion_check
  check (accion in ('consulta', 'documento_subido', 'documento_borrado', 'cotejo'));

"""Registro de auditoría: quién usó el sistema, cuándo y con qué.

Lo que responde: "¿de dónde salió esta respuesta?" y "¿quién estuvo
consultando esta norma?". Es lo primero que pide una revisión, y hasta ahora
no había forma de contestarlo.

Tres decisiones:

**El texto de la consulta no se guarda.** Lleva datos del caso y la
anonimización es de superficie. El historial de chat ya lo guarda para quien lo
escribió; duplicarlo aquí multiplica la exposición sin añadir nada auditable.

**Se escribe con el token del usuario, como todo lo demás.** La política de
`eventos_auditoria` permite insertar y leer lo propio, y no permite modificar
ni borrar: quien genera el evento no puede deshacerlo.

**Un fallo aquí nunca tumba la respuesta.** Se registra en consola y se sigue.
Perder un evento de auditoría es malo; perder la respuesta que el usuario está
esperando por no haber podido anotarla es peor, y además convierte una caída de
Supabase en una caída del asistente.

Sin sesión no hay evento: no hay a quién atribuirlo. Las consultas anónimas
quedan fuera del registro, que es una razón más para cerrar el alta abierta.
"""

from __future__ import annotations

import nube


def registrar(
    token: str | None,
    usuario_id: str | None,
    accion: str,
    *,
    modelo: str | None = None,
    prompt_version: str | None = None,
    corpus_unidades: int | None = None,
    normas_citadas: list[str] | None = None,
    documentos_citados: int = 0,
    ok: bool = True,
) -> None:
    if not token or not usuario_id or not nube.configurado():
        return
    try:
        nube.insertar(
            "eventos_auditoria",
            token,
            [
                {
                    "usuario_id": usuario_id,
                    "accion": accion,
                    "modelo": modelo,
                    "prompt_version": prompt_version,
                    "corpus_unidades": corpus_unidades,
                    # Sin duplicados y en orden estable, para que dos consultas
                    # iguales produzcan la misma fila y se puedan agrupar.
                    "normas_citadas": sorted(set(normas_citadas or [])),
                    "documentos_citados": documentos_citados,
                    "ok": ok,
                }
            ],
            devolver=False,
        )
    except nube.ErrorNube as e:
        print(f"AVISO: no se registró el evento de auditoría: {e}", flush=True)

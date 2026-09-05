"""Evaluación de los agentes: su corpus, sus citas y su frontera.

    python -m agentes.evaluar              # recuperación y citas: gratis
    python -m agentes.evaluar --alcance    # añade la frontera: llama al modelo

Tres controles, y el tercero es el que distingue un agente de una etiqueta:

**Recuperación.** Que cada consulta de su materia recupere el artículo que la
responde, con SU filtro puesto. Un agente que no encuentra lo suyo no tiene
corpus, tiene acceso a uno.

**Citas.** Que cada artículo que el cuestionario de DIEGO menciona exista en el
índice. Es determinista y vale para siempre: el día que el parser cambie un
identificador, esto se pone rojo antes de que un entregable cite un artículo
que no está.

**Alcance.** Que responda lo suyo y RECHACE lo ajeno. El caso que importa es el
segundo: una consulta de seguridad y salud en el trabajo que el corpus común sí
cubre y DIEGO no debe contestar. Sin este control, "alcance declarado" es una
frase en un documento.
"""

from __future__ import annotations

import os
import re
import sys

from rag.answer import responder
from rag.retrieval import Buscador

from .catalogo import AGENTES
from .cuestionario import unidades_citadas

_NEGATIVAS = (
    "no contiene",
    "no está en el corpus",
    "no dispongo",
    "fuera de mi alcance",
    "no forma parte",
    "no tengo acceso",
    "no puedo",
)


def _hay_clave() -> bool:
    """Vectorizar una consulta cuesta una llamada, y la llamada cuesta clave.

    En el CI no hay ninguna a menos que alguien la ponga como secreto, así que
    la parte de recuperación se salta y la de citas —que es determinista y no
    llama a nadie— corre igual. Un control que solo puede correr en el portátil
    de quien lo escribió no es un control.
    """
    from rag.config import _load_dotenv

    _load_dotenv()
    return bool(os.getenv("GOOGLE_API_KEY", "").strip())


def _recuperacion(buscador: Buscador) -> int:
    fallos = 0
    for agente in AGENTES.values():
        if not agente.casos_recuperacion:
            continue
        print(f"\n{agente.nombre} · recuperación")
        for caso in agente.casos_recuperacion:
            materias = list(agente.materias) if agente.materias else None
            res = buscador.buscar(caso.consulta, k=caso.k, materias=materias)
            ids = [r.unidad.id for r in res]
            if caso.unidad in ids:
                pos = ids.index(caso.unidad) + 1
                print(f"  ok    {caso.consulta[:58]:58} {pos}/{caso.k}")
            else:
                fallos += 1
                print(f"  FALLA {caso.consulta[:58]:58} —")
                print(f"        esperaba {caso.unidad}")
                print(f"        recuperó {ids[:4]}")
    return fallos


def _citas(buscador: Buscador) -> int:
    existentes = {u.id for u in buscador.unidades}
    faltan = sorted(unidades_citadas() - existentes)
    print("\nDIEGO · citas del cuestionario")
    if faltan:
        print(f"  FALLA {len(faltan)} unidad(es) citadas que no están en el índice:")
        for u in faltan:
            print(f"        {u}")
        return 1
    print(f"  ok    las {len(unidades_citadas())} unidades citadas existen")
    return 0


def _alcance(buscador: Buscador) -> int:
    fallos = 0
    for agente in AGENTES.values():
        if not agente.casos_alcance:
            continue
        print(f"\n{agente.nombre} · alcance")
        for caso in agente.casos_alcance:
            r = responder(caso.consulta, buscador, con_diagrama=False, agente=agente)
            cita = bool(re.search(r"\[[FD]\d+(?:\s*,\s*[FD]\d+)*\]", r.texto))
            niega = any(n in r.texto.lower() for n in _NEGATIVAS)
            # Responder = citar y no abrir negando. Rechazar = decirlo, con o
            # sin citas: negarse citando lo que sí tiene es correcto.
            respondio = cita and not any(n in r.texto[:200].lower() for n in _NEGATIVAS)

            if respondio == caso.responde:
                verbo = "responde" if caso.responde else "rechaza"
                print(f"  ok    {verbo}: {caso.consulta[:52]}")
            else:
                fallos += 1
                esperado = "responder" if caso.responde else "rechazar"
                print(f"  FALLA debía {esperado}: {caso.consulta[:52]}")
                print(f"        porque: {caso.porque}")
                print(f"        cita={cita} niega={niega}")
                print(f"        dijo: {r.texto[:200]!r}")
    return fallos


def main() -> int:
    con_alcance = "--alcance" in sys.argv
    buscador = Buscador()

    agentes = ", ".join(a.nombre for a in AGENTES.values())
    print(f"{len(AGENTES)} agentes: {agentes}")

    con_clave = _hay_clave()
    if con_clave:
        fallos = _recuperacion(buscador)
    else:
        fallos = 0
        print("\n(recuperación omitida: no hay GOOGLE_API_KEY)")

    fallos += _citas(buscador)

    if con_alcance and not con_clave:
        print("(alcance omitido: no hay GOOGLE_API_KEY)")
    elif con_alcance:
        fallos += _alcance(buscador)
    else:
        print("\n(alcance omitido: llama al modelo. Añade --alcance)")

    print(f"\n{'FALLA' if fallos else 'ok'} — {fallos} problema(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())

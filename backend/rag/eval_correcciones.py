"""Las observaciones de los revisores, re-ejecutadas.

    python -m rag.eval_correcciones

`docs/CORRECCIONES.md` recoge ocho observaciones de un revisor de seguridad y
otro de compliance, con la respuesta de antes y la de después. Este banco
comprueba que las de «después» siguen siendo las de ahora.

Por qué existe aparte de `rag.eval_prompt`: aquél verifica las reglas del
prompt en abstracto; este verifica **casos concretos que alguien reportó**. Son
la memoria del proyecto sobre sus propios fallos, y sin ejecutarlos nadie sabe
si una corrección sigue en pie tres semanas después.

**Qué comprueba y qué no.** La sustancia, no el formato. La observación era
«enlistar los sujetos obligados», no «usar viñetas»: que el modelo los nombre
en prosa o en lista es variación a temperatura 0.2 y no una regresión. Una
comprobación que mide el formato se pone roja sola y acaba ignorándose.

Llama al modelo una vez por caso, así que gasta cuota y no corre en el CI.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from agentes import obtener

from .answer import responder
from .retrieval import Buscador

_NEGATIVA = ("no contiene", "no está en el corpus", "no dispongo", "no forma parte")
_FALTA = ("no está en el corpus", "no aparece", "no figura", "no se encuentra",
          "no forma parte", "no consta")


@dataclass
class Caso:
    numero: int
    observacion: str
    consulta: str
    agente: str | None = None
    # Todas estas cadenas tienen que aparecer en la respuesta.
    contiene: tuple[str, ...] = ()
    # Al menos una de estas.
    alguna: tuple[str, ...] = ()
    # Fuentes de más de una norma: la observación era «solo habla de soborno».
    varias_normas: bool = False
    # Avisa de que el artículo citado en la consulta no existe (regla 5).
    avisa_falta: bool = False
    # Abre admitiendo que no lo cubre.
    abstiene: bool = False
    # El aviso determinista de materia que falta nombra esta norma.
    aviso_materia: str = ""
    notas: str = ""


CASOS: tuple[Caso, ...] = (
    Caso(1, "Enlistar los sujetos obligados",
         "un casino es un sujeto obligado de plaft?",
         contiene=("casino",),
         alguna=("tragamoneda", "lotería", "loteria", "bingo", "juego"),
         notas="Antes remitía a la norma sin decir si el casino estaba dentro."),
    Caso(2, "Alcance vigente de la Ley 30424",
         "¿Qué delitos generan responsabilidad administrativa de la persona "
         "jurídica según la Ley 30424?",
         contiene=("226", "228", "397"),
         notas="Antes decía solo cohecho activo transnacional, el alcance de 2016."),
    Caso(3, "Ejemplos concretos en vez de abstracciones",
         "cuándo aplica la debida diligencia reforzada", agente="diego",
         alguna=("PEP", "fideicomiso", "no residente", "no domiciliada"),
         notas="Antes: «debe hacerse una evaluación de riesgo». Sin los supuestos."),
    Caso(4, "Sesgo hacia soborno",
         "cuándo aplica la debida diligencia reforzada", agente="diego",
         varias_normas=True,
         notas="Era falta de corpus, no del recuperador: la ISO 37001 eran 204 "
               "de las unidades cargadas y hablaba de soborno."),
    Caso(5, "Artículo inexistente citado en la consulta",
         "Según el artículo 512 de la Ley 29733, ¿qué obligaciones tengo con "
         "los datos sensibles?",
         avisa_falta=True,
         notas="Antes daba por bueno el artículo inventado y seguía."),
    Caso(6, "Libre competencia — PENDIENTE, falta el DL 1034",
         "puedo asistir a un almuerzo con un competidor?",
         aviso_materia="DL 1034",
         notas="No se exige que se abstenga: la ISO 37001 usa literalmente la "
               "palabra «competidor» en su ejemplo de conflicto de intereses y "
               "el recuperador la saca con 0.63. Lo exigible es que se diga que "
               "la materia no está cargada."),
    Caso(8, "Hallazgo de bienes culturales — PENDIENTE, falta la Ley 28296",
         "qué pasa si un trabajador encuentra un huaco",
         abstiene=True, aviso_materia="Ley 28296",
         notas="La palabra «trabajador» arrastra la consulta a seguridad y "
               "salud en el trabajo, que puntúa 0.63 frente al 0.55 de una "
               "consulta bien formulada sobre patrimonio."),
)

# La 7 —«buscar en documentos internos»— no está: exige una sesión y un
# documento subido, o sea infraestructura que este banco no monta. Se prueba a
# mano contra el despliegue.


def _revisar(caso: Caso, buscador: Buscador) -> list[str]:
    agente = obtener(caso.agente)
    r = responder(caso.consulta, buscador, con_diagrama=False, agente=agente)
    txt = r.texto
    bajo = txt.lower()
    fallos: list[str] = []

    faltan = [c for c in caso.contiene if c.lower() not in bajo]
    if faltan:
        fallos.append(f"no menciona {faltan}")
    if caso.alguna and not any(a.lower() in bajo for a in caso.alguna):
        fallos.append(f"no menciona ninguno de {list(caso.alguna)}")
    if caso.varias_normas and len({f.unidad.norma_id for f in r.fuentes}) <= 1:
        fallos.append("todas las fuentes son de la misma norma")
    if caso.avisa_falta and not any(s in bajo for s in _FALTA):
        fallos.append("no avisa de que el artículo citado no existe")
    if caso.abstiene and not any(s in bajo[:250] for s in _NEGATIVA):
        fallos.append("no admite de entrada que no lo cubre")
    if caso.aviso_materia and not any(caso.aviso_materia in a for a in r.advertencias):
        fallos.append(f"falta el aviso de que no está cargado el {caso.aviso_materia}")

    if fallos:
        citas = ", ".join(f.unidad.cita for f in r.fuentes[:5]) or "ninguna"
        fallos.append(f"fuentes: {citas}")
        fallos.append(f"dijo: {txt[:220]!r}")
    return fallos


def main() -> int:
    buscador = Buscador()
    print(f"{len(CASOS)} observaciones de docs/CORRECCIONES.md\n")

    malas = 0
    for caso in CASOS:
        fallos = _revisar(caso, buscador)
        marca = "ok   " if not fallos else "FALLA"
        print(f"{marca} {caso.numero}. {caso.observacion}")
        if fallos:
            malas += 1
            for f in fallos:
                print(f"      - {f}")
            print(f"      contexto: {caso.notas}")
        print()

    print(f"{len(CASOS) - malas}/{len(CASOS)} observaciones siguen bien")
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main())

"""Qué es un agente, como dato.

Hasta ahora la única diferencia entre materias era una casilla de filtro sobre
un índice común, y eso no es un agente: es una consulta con menos corpus. Un
agente necesita cuatro cosas, y las cuatro viven aquí:

  * **su corpus** — qué materias del índice puede ver;
  * **su alcance declarado** — qué responde y qué no, en palabras que entran
    al prompt, no en un README;
  * **sus reglas propias** — lo que su oficio exige y el prompt común no dice;
  * **sus casos de evaluación** — qué debe acertar, y qué debe rechazar.

Lo cuarto es lo que impide que un agente sea una etiqueta. Un agente sin casos
que comprueben su alcance no tiene alcance: tiene una intención.

Va antes que el orquestador a propósito. Enrutar entre cosas que no están
definidas es enrutar al azar.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CasoRecuperacion:
    """La consulta debe recuperar esta unidad dentro de las k primeras."""

    consulta: str
    unidad: str
    k: int = 5


@dataclass(frozen=True)
class CasoAlcance:
    """Qué debe hacer el agente con una consulta que roza su frontera.

    `responde=False` es el caso importante: una consulta que cae fuera de su
    materia y que tiene que rechazar aunque el corpus común sí la cubra. Sin
    estos casos, «alcance declarado» es una frase en un documento.
    """

    consulta: str
    responde: bool
    porque: str


@dataclass(frozen=True)
class Agente:
    id: str
    nombre: str
    acronimo: str
    area: str
    # None = todo el corpus. Una tupla = solo esas materias del índice.
    materias: tuple[str, ...] | None
    # Entra literal al prompt. Escrito en segunda persona, como el resto de
    # las reglas, porque el modelo lo lee como instrucción y no como ficha.
    alcance: str
    fuera_de_alcance: str
    reglas: tuple[str, ...] = ()
    casos_recuperacion: tuple[CasoRecuperacion, ...] = field(default_factory=tuple)
    casos_alcance: tuple[CasoAlcance, ...] = field(default_factory=tuple)

    def bloque_prompt(self) -> str:
        """El trozo del prompt que distingue a este agente de los demás."""
        lineas = [
            f"ERES {self.nombre}, el agente de {self.area.lower()}.",
            f"ALCANCE: {self.alcance}",
            f"FUERA DE TU ALCANCE: {self.fuera_de_alcance}",
        ]
        if self.reglas:
            lineas.append("Reglas propias de tu materia:")
            # Empiezan en 10 para no chocar con las nueve del prompt común: si
            # el modelo ve dos reglas 3, una de las dos deja de existir.
            lineas += [f"{i}. {r}" for i, r in enumerate(self.reglas, 10)]
        return "\n".join(lineas)

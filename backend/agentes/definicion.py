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
    # Las normas sin las que este agente no existe. Un agente está ACTIVO si y
    # solo si todas están en el índice, y eso se calcula, no se declara: cuando
    # alguien carga el PDF que falta, el agente se enciende solo, y si alguien
    # retira una norma, se apaga en vez de seguir respondiendo de memoria.
    #
    # Vacío = no depende de ninguna en concreto (CARLOS, que usa el índice
    # entero).
    normas_requeridas: tuple[str, ...] = ()
    # Si las conversaciones con este agente se guardan en el historial.
    #
    # ELENA es la razón de que exista. Su materia es el canal de denuncias, y
    # la tentación obvia de quien lo use es pegar una denuncia real para
    # preguntar qué hacer con ella. ELENA no procesa denuncias —su regla lo
    # dice—, pero una regla del prompt no impide que el texto ya pegado acabe
    # en la tabla `mensajes`. No guardarlo sí lo impide. Es la "retención
    # acotada" de manual-casos, aplicada en el único sitio donde es verificable.
    guarda_historial: bool = True

    def faltantes(self, indexadas: set[str]) -> list[str]:
        """Normas requeridas que no están en el índice."""
        return [n for n in self.normas_requeridas if n not in indexadas]

    def activo(self, indexadas: set[str]) -> bool:
        return not self.faltantes(indexadas)

    def bloque_prompt(self) -> str:
        """El trozo del prompt que distingue a este agente de los demás."""
        lineas = [
            f"ERES {self.nombre}, el agente de {self.area.lower()}.",
            f"ALCANCE: {self.alcance}",
            f"FUERA DE TU ALCANCE: {self.fuera_de_alcance}",
        ]
        reglas = list(self.reglas)
        if self.materias is not None:
            # Va automática para todo agente con corpus acotado, y no escrita a
            # mano en cada uno, porque el fallo es estructural y no de materia.
            #
            # Con el filtro puesto, el recuperador SIEMPRE devuelve algo: sus
            # ocho mejores dentro de su corpus, aunque la consulta sea de otra
            # cosa. Preguntado por auditorías de seguridad y salud en el
            # trabajo, DIEGO sacaba el artículo 34 de la Resolución SBS —que
            # habla de auditorías, pero del SPLAFT— y abría contestando con él.
            # Quien lo lea deprisa cree que le respondieron lo que preguntó.
            reglas.append(
                "Si la consulta es de una materia fuera de tu alcance, DILO EN "
                "LA PRIMERA FRASE, aunque en tus fuentes haya algo que se le "
                "parezca. Tu corpus está filtrado: el recuperador siempre te "
                "devuelve tus mejores ocho artículos, incluso cuando ninguno "
                "viene a cuento. Que un artículo comparta palabras con la "
                "consulta no significa que la cubra. Después de decirlo, puedes "
                "añadir qué sí regula lo que encontraste, dejando claro que es "
                "otra cosa."
            )
        if reglas:
            lineas.append("Reglas propias de tu materia:")
            # Empiezan en 10 para no chocar con las nueve del prompt común: si
            # el modelo ve dos reglas 3, una de las dos deja de existir.
            lineas += [f"{i}. {r}" for i, r in enumerate(reglas, 10)]
        return "\n".join(lineas)

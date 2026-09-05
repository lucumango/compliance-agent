"""Lo que se sabe que NO está en el corpus.

Por qué existe. Cuando el corpus no cubre una consulta, la respuesta correcta
es decirlo — y hasta ahora eso era una sola frase: «El corpus cargado no
contiene una respuesta a esto.» Cierto, y completamente inútil: el usuario no
sabe si preguntó mal, si la materia no está cargada, o si no hay norma.

Lo que este módulo NO hace es dejar que el modelo rellene el hueco. Decirle
«y si no sabes, di qué norma lo regula» es pedirle exactamente lo que el
sistema entero existe para no hacer: afirmar derecho de memoria. Así que la
lista está escrita a mano, revisada, y viaja como aviso del sistema —no como
parte de la respuesta del modelo—.

Se mantiene junto a la sección «Cobertura que falta» de docs/FUENTES.md. Si
una de estas normas se carga, hay que quitarla de aquí: una lista de huecos
que menciona algo que ya está cargado es peor que no tenerla.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Hueco:
    norma: str
    materia: str


# Ordenados por lo que más veces se ha echado en falta. Los dos primeros
# vienen de observaciones reales de los revisores; ver docs/CORRECCIONES.md.
HUECOS: tuple[Hueco, ...] = (
    Hueco("Ley 28296", "patrimonio cultural: hallazgos arqueológicos y bienes culturales"),
    Hueco("DL 1034", "libre competencia y conductas anticompetitivas"),
    Hueco("Reglamento de la Ley 30424 (DS 002-2019-JUS, DS 002-2025-JUS)",
          "el modelo de prevención"),
    Hueco("ISO 37002 y el régimen laboral de hostilidad y represalia",
          "canal de denuncias y línea ética"),
    Hueco("TUO de la Ley 27444", "potestad sancionadora y graduación de multas"),
    Hueco("Código Penal", "tipificación de delitos — fuera de alcance a propósito"),
)


def aviso() -> str:
    """Una línea con los huecos declarados, para acompañar una negativa."""
    partes = [f"{h.norma} ({h.materia})" for h in HUECOS]
    return (
        "Materias que se sabe que NO están cargadas, por si tu consulta cae en "
        "alguna: " + "; ".join(partes) + ". Esta lista se mantiene a mano en "
        "docs/FUENTES.md; que algo no aparezca aquí no garantiza que sí esté."
    )


def como_lista() -> list[dict]:
    return [{"norma": h.norma, "materia": h.materia} for h in HUECOS]

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
    # Palabras que delatan que la consulta va de esto. Se eligen por lo
    # DISCRIMINANTES que son, no por lo frecuentes: "competencia" sola aparece
    # en "competencia de la autoridad" y no serviría; "competidor" y "colusión"
    # solo salen cuando se habla de libre competencia.
    terminos: tuple[str, ...] = ()


# Ordenados por lo que más veces se ha echado en falta. Los dos primeros
# vienen de observaciones reales de los revisores; ver docs/CORRECCIONES.md.
HUECOS: tuple[Hueco, ...] = (
    Hueco("Ley 28296", "patrimonio cultural: hallazgos arqueológicos y bienes culturales",
          ("huaca", "huaco", "arqueológ", "arqueolog", "patrimonio cultural",
           "restos históricos", "bien cultural", "bienes culturales", "yacimiento")),
    Hueco("DL 1034", "libre competencia y conductas anticompetitivas",
          ("competidor", "competidores", "libre competencia", "colusión",
           "colusion", "cártel", "cartel de precios", "reparto de mercado",
           "fijación de precios", "anticompetitiv", "abuso de posición")),
    Hueco("Reglamento de la Ley 30424 (DS 002-2019-JUS, DS 002-2025-JUS)",
          "el modelo de prevención",
          ("modelo de prevención", "modelo de prevencion")),
    Hueco("DL 1327, DS 010-2017-JUS e ISO 37002",
          "canal de denuncias y protección al denunciante — lo que necesita ELENA",
          ("línea ética", "linea etica", "canal de denuncias", "represalia",
           "denunciante", "whistleblow", "protección al denunciante")),
    Hueco("Ley 27942 y DS 014-2019-MIMP",
          "hostigamiento sexual — lo que necesitan ELENA e IVÁN",
          ("hostigamiento sexual", "acoso sexual", "hostigamiento")),
    Hueco("TUO del DL 728 (DS 003-97-TR)",
          "falta grave, despido y actos de hostilidad — lo que necesita IVÁN",
          ("despido", "despedir", "falta grave", "carta de preaviso",
           "actos de hostilidad", "hostilidad laboral")),
    Hueco("Ley 27269", "firmas y documentos electrónicos como evidencia",
          ("firma digital", "firma electrónica", "firma electronica",
           "certificado digital")),
    Hueco("TUO de la Ley 27444", "potestad sancionadora y graduación de multas",
          ("graduación de la multa", "graduar la sanción", "27444",
           "procedimiento administrativo sancionador")),
    Hueco("Código Penal", "tipificación de delitos — fuera de alcance a propósito",
          ("código penal", "codigo penal", "tipifica", "pena privativa",
           "años de cárcel", "anos de carcel")),
)


def huecos_para(consulta: str) -> list[Hueco]:
    """Los huecos declarados que la consulta parece tocar.

    Determinista y por palabras, no por el modelo. Existe porque el prompt no
    basta: ante «¿puedo asistir a un almuerzo con un competidor?» el
    recuperador saca las cláusulas de conflicto de intereses de la ISO 37001
    —que hablan literalmente de «competidor»— con 0.63, y el modelo las da por
    respuesta. Son otra materia. Sin la libre competencia cargada, lo único
    honesto es decir en voz alta que falta.

    Falsos positivos los habrá; el coste de uno es una línea de aviso de más.
    El coste de un falso negativo es que alguien se lleve una respuesta sobre
    conflicto de intereses creyendo que le contestaron sobre libre competencia.
    """
    texto = consulta.lower()
    return [h for h in HUECOS if any(t in texto for t in h.terminos)]


def aviso_dirigido(consulta: str) -> str | None:
    """Aviso para una consulta que toca una materia que se sabe que falta."""
    tocados = huecos_para(consulta)
    if not tocados:
        return None
    partes = [f"{h.norma} — {h.materia}" for h in tocados]
    return (
        "Tu consulta toca una materia que NO está en el corpus: "
        + "; ".join(partes)
        + ". Lo que responda arriba sale de otras normas y puede parecer una "
        "respuesta sin serlo. Contrasta con la fuente oficial."
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

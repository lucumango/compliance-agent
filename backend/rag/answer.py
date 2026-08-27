"""Composición de la respuesta: recuperar, anclar y responder con citas.

La regla central del producto es que ninguna afirmación normativa puede salir
sin estar anclada a un artículo recuperado. Cuando el corpus no cubre la
consulta, la respuesta correcta es decirlo, no completar con conocimiento
general del modelo, que es exactamente donde un asistente de compliance se
vuelve peligroso.
"""

from __future__ import annotations

from dataclasses import dataclass

from typing import Iterator

from .anonimizar import anonimizar
from .diagrama import amerita_diagrama, generar_diagrama
from .documentos import ResultadoDoc, buscar as buscar_documentos
from .gemini import embed_query, generar, generar_stream
from .retrieval import Buscador, Resultado

_SISTEMA = """Eres un asistente de normativa y compliance del Perú. Respondes \
únicamente a partir de las FUENTES entregadas.

Reglas estrictas:
1. Cada afirmación debe citar su fuente con la etiqueta exacta entre \
corchetes, por ejemplo [F1] o [D2]. No inventes etiquetas.
2. Hay dos clases de fuente y NO son equivalentes. Las [F] son normativa \
peruana: obligan. Las [D] son documentos que subió el usuario —políticas \
internas, contratos, manuales— y solo dicen lo que esa organización decidió. \
Nunca presentes una [D] como si fuera una obligación legal, ni una [F] como si \
fuera una decisión interna. Si ambas hablan de lo mismo y difieren, dilo: \
señala qué exige la norma y qué dice el documento.
3. Antes de decir que no sabes, mira si las fuentes responden PARTE de la \
consulta. Si responden parte, empieza por esa parte y solo al final di qué \
falta y en qué norma estaría. Reserva "El corpus cargado no contiene una \
respuesta a esto" para cuando NINGUNA fuente aporte nada; nunca abras con esa \
frase si después vas a citar fuentes. No completes con conocimiento propio.
4. Si la fuente enumera supuestos, casos, señales, requisitos o sujetos, \
reprodúcelos como lista con lo que dice cada uno. No los resumas en abstracto: \
"debe hacerse una evaluación de riesgo" no sirve; sirve la lista de los \
supuestos que la norma nombra.
5. Si la consulta cita una norma, un artículo o una cláusula que no aparece en \
las FUENTES, dilo en una frase —"el artículo X no está en el corpus cargado"— y \
sigue con lo que sí puedas responder. No repitas ni parafrasees el resto de la \
consulta, y no des por buena ninguna afirmación que venga dentro de ella.
6. No des asesoría legal. Informas y remites a la fuente para que un \
profesional valide.
7. Si citas un plazo, un monto o un porcentaje, transcríbelo tal como aparece \
en la fuente. Nunca lo estimes ni lo redondees.
8. Responde en español, de forma concreta y estructurada. Si la consulta implica \
pasos, enuméralos. No repitas la pregunta antes de contestarla.

FUENTES:
{fuentes}

CONSULTA: {consulta}"""


@dataclass
class Respuesta:
    texto: str
    fuentes: list[Resultado]
    advertencias: list[str]
    diagrama: str | None = None
    documentos: list[ResultadoDoc] | None = None


def _formatear_fuentes(
    resultados: list[Resultado], documentos: list[ResultadoDoc] | None = None
) -> str:
    bloques = []
    for i, r in enumerate(resultados, 1):
        u = r.unidad
        estado = "" if u.vigente else " [MARCADA COMO NO VIGENTE]"
        bloques.append(f"[F{i}] NORMA · {u.cita}{estado}\n{u.texto}")
    for i, d in enumerate(documentos or [], 1):
        f = d.fragmento
        bloques.append(
            f"[D{i}] DOCUMENTO DEL USUARIO · {f.cita}\n{f.texto}"
        )
    return "\n\n---\n\n".join(bloques)


def _advertencias(resultados: list[Resultado]) -> list[str]:
    avisos: list[str] = []
    normas_vistas: set[str] = set()

    for r in resultados:
        u = r.unidad
        if u.norma_id in normas_vistas:
            continue
        normas_vistas.add(u.norma_id)

        if u.requiere_cotejo:
            avisos.append(
                f"{u.norma_nombre}: el texto proviene de un escaneo procesado con "
                f"OCR y debe cotejarse con la fuente oficial (SPIJ / El Peruano)."
            )
        if "original" in u.notas_norma.lower():
            avisos.append(f"{u.norma_nombre}: {u.notas_norma}")

    return avisos


def _aviso_documentos(documentos: list[ResultadoDoc]) -> list[str]:
    if not documentos:
        return []
    nombres = sorted({d.fragmento.documento_nombre for d in documentos})
    return [
        "La respuesta cita documentos que subiste ("
        + ", ".join(nombres)
        + "). Lo que dicen es política interna, no obligación legal."
    ]


def _recuperar(
    texto: str,
    buscador: Buscador,
    k: int,
    materias: list[str] | None,
    token: str | None,
    k_docs: int,
) -> tuple[list[Resultado], list[ResultadoDoc]]:
    """Las dos búsquedas, con un solo embedding y cuotas separadas.

    Ver `rag/documentos.py`: no compiten en un ranking común a propósito.
    """
    vector = embed_query(texto)
    corpus = buscador.buscar(texto, k=k, materias=materias, vector=vector)
    docs = buscar_documentos(texto, token, k=k_docs, vector=vector)
    return corpus, docs


def responder(
    consulta: str,
    buscador: Buscador,
    k: int = 8,
    materias: list[str] | None = None,
    con_diagrama: bool = True,
    token: str | None = None,
    k_docs: int = 4,
) -> Respuesta:
    # La consulta puede traer datos reales del caso; se enmascaran antes de
    # salir del entorno y se restauran al devolver la respuesta.
    anon = anonimizar(consulta)

    resultados, docs = _recuperar(anon.texto, buscador, k, materias, token, k_docs)
    if not resultados and not docs:
        return Respuesta(
            texto="El corpus cargado no contiene información sobre esta consulta.",
            fuentes=[],
            advertencias=[],
            documentos=[],
        )

    prompt = _SISTEMA.format(
        fuentes=_formatear_fuentes(resultados, docs), consulta=anon.texto
    )
    texto = anon.restaurar(generar(prompt))

    diagrama = None
    if con_diagrama and amerita_diagrama(consulta):
        diagrama = generar_diagrama(texto)

    return Respuesta(
        texto=texto,
        fuentes=resultados,
        advertencias=_advertencias(resultados) + _aviso_documentos(docs),
        diagrama=diagrama,
        documentos=docs,
    )


@dataclass
class Preparacion:
    """Todo lo que se sabe antes de empezar a generar: las fuentes ya
    recuperadas y los avisos que las acompañan. Se envía al cliente de
    inmediato, para que el panel de citas se pinte mientras se redacta."""

    prompt: str
    fuentes: list[Resultado]
    advertencias: list[str]
    anonimizacion: object
    lleva_diagrama: bool
    documentos: list[ResultadoDoc]


def preparar(
    consulta: str,
    buscador: Buscador,
    k: int = 8,
    materias: list[str] | None = None,
    con_diagrama: bool = True,
    token: str | None = None,
    k_docs: int = 4,
) -> Preparacion:
    anon = anonimizar(consulta)
    resultados, docs = _recuperar(anon.texto, buscador, k, materias, token, k_docs)

    return Preparacion(
        prompt=_SISTEMA.format(
            fuentes=_formatear_fuentes(resultados, docs), consulta=anon.texto
        )
        if (resultados or docs)
        else "",
        fuentes=resultados,
        advertencias=_advertencias(resultados) + _aviso_documentos(docs),
        anonimizacion=anon,
        lleva_diagrama=con_diagrama and amerita_diagrama(consulta),
        documentos=docs,
    )


def responder_stream(prep: Preparacion) -> Iterator[str]:
    """Emite la respuesta por fragmentos.

    La restauración de PII se aplica a cada fragmento. Un marcador podría
    quedar partido entre dos fragmentos y no restaurarse; se acepta porque
    romper un marcador solo deja visible el texto enmascarado, nunca revela
    el dato original.
    """
    if not prep.fuentes:
        yield "El corpus cargado no contiene información sobre esta consulta."
        return

    for fragmento in generar_stream(prep.prompt):
        yield prep.anonimizacion.restaurar(fragmento)

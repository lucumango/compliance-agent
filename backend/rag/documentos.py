"""Recuperación sobre los documentos del usuario.

Vive aparte de `retrieval.py` porque las dos búsquedas no compiten: se corren
las dos y cada una trae su cuota. Un ranking único ordenaría corpus y
documentos por el mismo score, y como los fragmentos del usuario son más
largos y más parecidos al lenguaje de la pregunta, empujarían fuera al artículo
de la ley justo en las consultas donde la ley es lo que hace falta.

La cuota fija cuesta algo de precisión en las consultas que solo tocan un lado,
y compra que la respuesta nunca se quede sin la norma.
"""

from __future__ import annotations

from dataclasses import dataclass

import nube

from .gemini import embed_query


@dataclass
class FragmentoDoc:
    id: str
    documento_id: str
    documento_nombre: str
    pagina: int | None
    texto: str

    @property
    def cita(self) -> str:
        if self.pagina:
            return f"{self.documento_nombre}, p. {self.pagina}"
        return self.documento_nombre


@dataclass
class ResultadoDoc:
    fragmento: FragmentoDoc
    score: float


def buscar(
    consulta: str,
    token: str | None,
    k: int = 4,
    score_minimo: float = 0.55,
    vector: list[float] | None = None,
) -> list[ResultadoDoc]:
    """Fragmentos del usuario más cercanos a la consulta.

    `vector` permite reutilizar el embedding que ya calculó la búsqueda del
    corpus, para no pagar dos veces la misma llamada.

    El umbral no es cosmético: sin él, un usuario con un solo documento recibe
    siempre sus cuatro fragmentos menos malos aunque la consulta no tenga nada
    que ver, y el modelo los cita porque están ahí.
    """
    if not token or not nube.configurado() or k <= 0:
        return []

    v = vector if vector is not None else embed_query(consulta)

    try:
        filas = nube.rpc(
            "buscar_fragmentos",
            token,
            consulta="[" + ",".join(f"{x:.7g}" for x in v) + "]",
            k=k,
            score_minimo=score_minimo,
        )
    except nube.ErrorNube:
        # Los documentos del usuario son un extra: si Supabase no responde, la
        # consulta debe seguir contestándose con el corpus normativo.
        return []

    return [
        ResultadoDoc(
            fragmento=FragmentoDoc(
                id=f["fragmento_id"],
                documento_id=f["documento_id"],
                documento_nombre=f["documento_nombre"],
                pagina=f.get("pagina"),
                texto=f["texto"],
            ),
            score=float(f["score"]),
        )
        for f in (filas or [])
    ]

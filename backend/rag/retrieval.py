"""Recuperación sobre el índice vectorial."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .gemini import embed_query
from .index import Unidad, cargar


@dataclass
class Resultado:
    unidad: Unidad
    score: float


class Buscador:
    def __init__(self) -> None:
        self.matriz, self.unidades = cargar()

    def buscar(
        self,
        consulta: str,
        k: int = 8,
        materias: list[str] | None = None,
        score_minimo: float = 0.0,
        vector: list[float] | None = None,
        max_por_norma: int | None = None,
    ) -> list[Resultado]:
        # El vector se acepta ya calculado porque la búsqueda sobre los
        # documentos del usuario necesita el mismo, y vectorizar la consulta
        # dos veces es una llamada de red de más por cada mensaje.
        crudo = vector if vector is not None else embed_query(consulta)
        vector = np.array(crudo, dtype=np.float32)
        vector /= np.linalg.norm(vector)

        # La matriz ya está normalizada al indexar, así que el producto punto
        # es directamente la similitud coseno.
        scores = self.matriz @ vector

        if materias:
            permitidas = set(materias)
            mascara = np.array(
                [u.materia in permitidas for u in self.unidades], dtype=bool
            )
            scores = np.where(mascara, scores, -np.inf)

        disponibles = int(np.isfinite(scores).sum())
        if disponibles == 0:
            return []

        # El tope muerde solo cuando una norma se llevaria la MAYORIA de las
        # plazas. Mas estrecho hace dano: se midio con "cuando aplica la debida
        # diligencia reforzada", donde un tope de 3 sobre k=6 expulsaba el
        # articulo 16 de la Resolucion SBS —el que enumera los regimenes, que
        # es la respuesta— para meter en su lugar un articulo peor de otra
        # norma. Reservar plazas cuesta precision; solo compensa contra el
        # acaparamiento.
        if max_por_norma is None:
            max_por_norma = max(3, k // 2)

        # Se piden mas candidatos que plazas porque despues se filtra por norma
        # y hay que tener con que rellenar.
        n = min(max(k * 4, k), disponibles)
        candidatos = np.argpartition(-scores, n - 1)[:n]
        candidatos = [i for i in candidatos[np.argsort(-scores[candidatos])]
                      if scores[i] >= score_minimo]

        # Tope por norma. Sin el, una norma larga y de lenguaje generico copa el
        # resultado: la ISO 37001 son 204 de las 824 unidades y esta escrita en
        # terminos de "riesgo", "debida diligencia" y "controles", que es
        # justo el vocabulario de casi cualquier consulta de cumplimiento. El
        # sintoma es que a una pregunta sobre lavado de activos se responde
        # hablando de soborno, con la norma peruana especifica desplazada del
        # top-k por clausulas que dicen algo parecido de forma mas general.
        #
        # El tope no descarta: reserva. Si no hay suficientes unidades de otras
        # normas, la segunda pasada devuelve las que sobraban.
        elegidos: list[int] = []
        sobrantes: list[int] = []
        por_norma: dict[str, int] = {}
        for i in candidatos:
            norma = self.unidades[i].norma_id
            if por_norma.get(norma, 0) < max_por_norma:
                por_norma[norma] = por_norma.get(norma, 0) + 1
                elegidos.append(i)
            else:
                sobrantes.append(i)
            if len(elegidos) == k:
                break

        if len(elegidos) < k:
            elegidos.extend(sobrantes[: k - len(elegidos)])
            elegidos.sort(key=lambda i: -scores[i])

        return [
            Resultado(unidad=self.unidades[i], score=float(scores[i]))
            for i in elegidos
        ]

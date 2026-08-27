"""Bloques a fragmentos indexables.

El corpus normativo no necesita esto: una ley ya viene troceada por su propio
autor en artículos, y el artículo es la unidad que se cita. Un documento del
usuario no trae esa estructura, así que hay que fabricarla.

El criterio es el párrafo. Se acumulan párrafos hasta llegar al tamaño
objetivo y se corta ahí, nunca a mitad de párrafo salvo que un solo párrafo ya
lo supere. Cortar por número de caracteres a secas parte tablas y listas
numeradas justo donde está el dato que se buscaba.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .extraer import Bloque

# Un fragmento debe caber holgado en el contexto junto a otros cinco del
# corpus, y ser lo bastante largo para que el embedding tenga de qué agarrarse.
OBJETIVO = 1200
MAXIMO = 1800
# El solape evita que una definición que cae en el límite entre dos fragmentos
# quede partida en dos mitades, ninguna de las cuales recupera bien.
SOLAPE = 150
# Por debajo de esto no hay señal: un encabezado suelto, un número de página.
MINIMO = 80

# Techo por documento. A 3072 dimensiones cada fragmento son 12 KB de vector;
# mil fragmentos son 12 MB en una tabla sin índice ANN, que sigue barriéndose
# en milisegundos. Más que eso pide otra arquitectura, no otro parámetro.
MAX_FRAGMENTOS = 1000


@dataclass
class Fragmento:
    orden: int
    pagina: int | None
    texto: str


def _parrafos(texto: str) -> list[str]:
    partes = re.split(r"\n\s*\n", texto)
    return [p.strip() for p in partes if p.strip()]


def _partir_largo(parrafo: str) -> list[str]:
    """Parte un párrafo que por sí solo excede el máximo.

    Se intenta por frase; si tampoco cabe —una tabla sin puntos, un bloque de
    texto corrido mal extraído— se corta por longitud, que es feo pero
    preferible a mandar 20.000 caracteres al modelo de embeddings.
    """
    frases = re.split(r"(?<=[.;:])\s+", parrafo)
    piezas: list[str] = []
    actual = ""
    for frase in frases:
        if len(frase) > MAXIMO:
            if actual:
                piezas.append(actual)
                actual = ""
            piezas.extend(
                frase[i : i + OBJETIVO] for i in range(0, len(frase), OBJETIVO)
            )
            continue
        if actual and len(actual) + len(frase) + 1 > OBJETIVO:
            piezas.append(actual)
            actual = frase
        else:
            actual = f"{actual} {frase}".strip()
    if actual:
        piezas.append(actual)
    return piezas


def trocear(bloques: list[Bloque]) -> list[Fragmento]:
    fragmentos: list[Fragmento] = []
    # Acumulador abierto: (texto, página donde empezó).
    actual = ""
    pagina_actual: int | None = None

    def cerrar() -> None:
        nonlocal actual, pagina_actual
        if len(actual.strip()) >= MINIMO:
            fragmentos.append(
                Fragmento(
                    orden=len(fragmentos), pagina=pagina_actual, texto=actual.strip()
                )
            )
        actual = ""

    for bloque in bloques:
        for parrafo in _parrafos(bloque.texto):
            piezas = _partir_largo(parrafo) if len(parrafo) > MAXIMO else [parrafo]
            for pieza in piezas:
                if not actual:
                    pagina_actual = bloque.pagina
                    actual = pieza
                    continue
                if len(actual) + len(pieza) + 2 <= OBJETIVO:
                    actual = f"{actual}\n\n{pieza}"
                    continue
                cola = actual[-SOLAPE:]
                cerrar()
                if len(fragmentos) >= MAX_FRAGMENTOS:
                    return fragmentos
                # El solape arranca el siguiente fragmento con el final del
                # anterior, no con la pieza a secas.
                pagina_actual = bloque.pagina
                actual = f"{cola}\n\n{pieza}"

    cerrar()
    return fragmentos[:MAX_FRAGMENTOS]

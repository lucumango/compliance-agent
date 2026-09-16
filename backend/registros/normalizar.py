"""Normalización de nombres para comparar.

Tan simple como se pueda defender. Quita tildes, pasa a mayúsculas, deja letras
y dígitos, y quita las formas societarias: "Constructora Andina S.A.C." y
"CONSTRUCTORA ANDINA SAC" tienen que dar lo mismo, y "SAC" no aporta nada a la
identidad de nadie.
"""

from __future__ import annotations

import re
import unicodedata

# Formas societarias peruanas y las que más salen en las listas extranjeras.
# Van como palabras sueltas: se quitan después de normalizar la puntuación, así
# que "S.A.C." ya ha pasado a "S A C" y se recompone abajo.
_FORMAS = {
    "SAC", "SA", "SAA", "SRL", "EIRL", "SCRL", "SCR", "SPA", "SL", "SAS",
    "LTD", "LTDA", "LLC", "LLP", "LP", "INC", "CORP", "CO", "PLC", "GMBH",
    "AG", "BV", "NV", "OOO", "ZAO", "OAO", "PAO", "JSC", "PJSC", "FZE", "FZCO",
    "LIMITED", "COMPANY", "CORPORATION", "INCORPORATED", "SOCIEDAD", "ANONIMA",
    "CERRADA", "EMPRESA", "INDIVIDUAL", "RESPONSABILIDAD", "LIMITADA",
}

_SIGLAS_PARTIDAS = re.compile(r"\b(?:[A-Z]\s){1,4}[A-Z]\b")


def normalizar(texto: str) -> str:
    if not texto:
        return ""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    limpio = re.sub(r"[^A-Z0-9]+", " ", sin_tildes.upper()).strip()
    # "S A C" -> "SAC", para que la forma societaria se reconozca como una.
    limpio = _SIGLAS_PARTIDAS.sub(lambda m: m.group(0).replace(" ", ""), limpio)
    palabras = [p for p in limpio.split() if p not in _FORMAS and p not in {"DE", "Y", "E"}]
    return " ".join(palabras)

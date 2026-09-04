"""Anonimización de PII antes de enviar texto al LLM.

El usuario típico redacta consultas con datos reales ("el trabajador Juan Pérez,
DNI 45678912, denunció..."). Esos datos no necesitan salir del entorno para que
el modelo responda una pregunta normativa, así que se enmascaran antes de la
llamada y se restauran en la respuesta.

Cubre dos cosas, y con la MISMA tabla de marcadores:

  * la consulta;
  * los fragmentos de los documentos que subió el usuario, que también son
    suyos y también viajan en el prompt.

Compartir la tabla es lo que permite que un mismo DNI que aparece en la
consulta y en el contrato subido reciba el mismo marcador, y que el modelo
pueda razonar sobre que se trata de la misma persona.

Lo que NO se enmascara son las normas del corpus: son texto legal público, no
contienen datos de nadie, y aplicarles los patrones numéricos destrozaría
plazos y montos.

Es una defensa de superficie, no una garantía: reconoce patrones estructurados
(DNI, RUC, correos, teléfonos, montos, tarjetas), no nombres arbitrarios. Y no
alcanza al indexado: el texto del documento viaja íntegro a Google cuando se
vectoriza al subirlo. Está dicho en la interfaz y en docs/DOCUMENTOS.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# El orden importa: RUC (11 dígitos) debe intentarse antes que DNI (8), y el
# correo antes que cualquier patrón numérico que pudiera partirlo.
_PATRONES: list[tuple[str, re.Pattern]] = [
    ("CORREO", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("RUC", re.compile(r"\b(?:10|15|16|17|20)\d{9}\b")),
    ("TARJETA", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
    ("DNI", re.compile(r"\b\d{8}\b")),
    ("TELEFONO", re.compile(r"\b(?:\+51[ -]?)?9\d{8}\b")),
    ("CUENTA", re.compile(r"\b\d{13,20}\b")),
    ("MONTO", re.compile(r"(?:S/\.?|USD|\$)\s?\d[\d,.]*")),
]


@dataclass
class Anonimizacion:
    texto: str
    reemplazos: dict[str, str] = field(default_factory=dict)
    # Cuántos marcadores se pusieron por etiqueta. Vive aquí y no en una
    # variable local para que `tambien()` siga numerando donde se quedó.
    _contadores: dict[str, int] = field(default_factory=dict, repr=False)

    def tambien(self, texto: str) -> str:
        """Enmascara otro texto con la misma tabla de marcadores.

        Se usa para los fragmentos de los documentos del usuario. Un valor que
        ya apareció en la consulta reutiliza su marcador en vez de recibir uno
        nuevo, que es lo que permite al modelo ver que son el mismo dato.
        """
        return _enmascarar(texto, self.reemplazos, self._contadores)

    def restaurar(self, texto: str) -> str:
        """Devuelve los valores originales a la respuesta del modelo."""
        for marcador, original in self.reemplazos.items():
            texto = texto.replace(marcador, original)
        return texto


def _enmascarar(
    texto: str, reemplazos: dict[str, str], contadores: dict[str, int]
) -> str:
    # Invertida para no recorrer la tabla entera por cada coincidencia: con un
    # documento largo eso era cuadrático.
    ya_vistos = {v: k for k, v in reemplazos.items()}

    def sustituir(match: re.Match, etiqueta: str) -> str:
        original = match.group(0)
        # El mismo valor repetido recibe el mismo marcador, para que el modelo
        # pueda razonar sobre que se trata de la misma persona o entidad.
        if original in ya_vistos:
            return ya_vistos[original]
        contadores[etiqueta] = contadores.get(etiqueta, 0) + 1
        marcador = f"[{etiqueta}_{contadores[etiqueta]}]"
        reemplazos[marcador] = original
        ya_vistos[original] = marcador
        return marcador

    resultado = texto
    for etiqueta, patron in _PATRONES:
        resultado = patron.sub(lambda m, e=etiqueta: sustituir(m, e), resultado)
    return resultado


def anonimizar(texto: str) -> Anonimizacion:
    reemplazos: dict[str, str] = {}
    contadores: dict[str, int] = {}
    enmascarado = _enmascarar(texto, reemplazos, contadores)
    return Anonimizacion(
        texto=enmascarado, reemplazos=reemplazos, _contadores=contadores
    )

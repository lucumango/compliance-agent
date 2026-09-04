"""Los agentes del motor: su alcance, su corpus y sus casos."""

from .catalogo import AGENTES, CARLOS, DIEGO, POR_DEFECTO, obtener
from .definicion import Agente, CasoAlcance, CasoRecuperacion

__all__ = [
    "AGENTES",
    "CARLOS",
    "DIEGO",
    "POR_DEFECTO",
    "Agente",
    "CasoAlcance",
    "CasoRecuperacion",
    "obtener",
]

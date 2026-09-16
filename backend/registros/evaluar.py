"""Evaluación del cotejo contra registros públicos.

    python -m registros.evaluar

Sin modelo y sin cuota: todo es determinista. Necesita los registros
descargados (`python -m registros.actualizar`).

Lo que más importa aquí es el FALSO NEGATIVO. Un falso positivo le cuesta a
alguien diez minutos de descartar un homónimo; un falso negativo deja pasar a
un designado porque su nombre venía con una tilde, un "S.A.C." o en otro orden.
Los casos están escritos para romper exactamente eso.

Los designados de prueba son públicos y notorios —el Banco Nacional de Cuba
lleva en la lista OFAC desde los sesenta—, elegidos para que no desaparezcan de
la lista de un mes a otro y el banco no se ponga rojo por una baja legítima.
"""

from __future__ import annotations

import sys

from .listas import Cotejo
from .osce import Inhabilitados
from .sunat import Padron

# (consulta, lista esperada o None si NO debe salir nada, qué rompe)
LISTAS = (
    ("BANCO NACIONAL DE CUBA", "OFAC", "el nombre tal cual"),
    ("Banco Nacional de Cuba S.A.", "OFAC", "minúsculas y forma societaria"),
    ("MADURO MOROS, Nicolás", "OFAC", "tilde y orden apellido-nombre"),
    ("Nicolas Madruo Moros", "OFAC", "errata"),
    ("Rosneft Oil Company PJSC", "UK", "forma societaria rusa"),
    ("Constructora Andina del Peru SAC", None, "empresa peruana inventada: no debe salir"),
    ("Juan Carlos Perez Garcia", None, "nombre común: no debe salir un homónimo con 85"),
)


def main() -> int:
    fallos = 0

    print("Listas de sanciones")
    try:
        cotejo = Cotejo()
    except FileNotFoundError as e:
        print(f"  omitido: {e}")
        cotejo = None
    if cotejo:
        for aviso in cotejo.vigencia():
            print(f"  aviso: {aviso}")
        for consulta, esperada, que in LISTAS:
            listas = {c.lista for c in cotejo.buscar(consulta)}
            ok = (not listas) if esperada is None else (esperada in listas)
            fallos += not ok
            print(f"  {'ok   ' if ok else 'FALLA'} {que:44} -> {sorted(listas) or 'nada'}")

    print("\nPadrón de SUNAT")
    try:
        padron = Padron()
    except FileNotFoundError as e:
        print(f"  omitido: {e}")
        padron = None
    if padron:
        bcp = padron.por_ruc("20100047218")
        ok = bool(bcp) and bcp.estado == "ACTIVO"
        fallos += not ok
        print(f"  {'ok   ' if ok else 'FALLA'} un RUC conocido se encuentra y está activo")
        mal = padron.por_ruc("123") is None
        fallos += not mal
        print(f"  {'ok   ' if mal else 'FALLA'} un RUC mal formado no devuelve nada")

    print("\nProveedores sancionados (OSCE)")
    try:
        osce = Inhabilitados()
    except FileNotFoundError as e:
        print(f"  omitido: {e}")
        osce = None
    if osce:
        ok = len(osce.sanciones) > 1000
        fallos += not ok
        print(f"  {'ok   ' if ok else 'FALLA'} el dataset tiene sanciones ({len(osce.sanciones)})")
        primera = osce.sanciones[0]
        ok = bool(osce.por_ruc(primera.ruc))
        fallos += not ok
        print(f"  {'ok   ' if ok else 'FALLA'} una sanción se encuentra por su RUC")
        dias = osce.antiguedad_dias()
        print(f"  aviso: dataset del {osce.fecha}, hace {dias} días")

    print(f"\n{'FALLA' if fallos else 'ok'} — {fallos} problema(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())

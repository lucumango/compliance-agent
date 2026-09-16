"""Descarga y reconstruye los registros públicos.

    python -m registros.actualizar            # listas de sanciones + OSCE
    python -m registros.actualizar --sunat    # además el padrón de SUNAT (392 MB)

Cada fuente va por separado y el fallo de una no tumba las demás: que la ONU no
responda no es motivo para quedarse también sin OFAC. Sale con error si falla
alguna, para que quien lo lance se entere; el Dockerfile lo tolera y la API
publica lo que haya en /api/diego/registros.
"""

from __future__ import annotations

import sys
import traceback

from . import listas, osce, sunat


def main() -> int:
    tareas = [
        ("Listas de sanciones", lambda: (listas.descargar(), listas.construir())),
        ("Proveedores sancionados (OSCE)", lambda: osce.construir(osce.descargar())),
    ]
    if "--sunat" in sys.argv:
        tareas.append(("Padrón de SUNAT", lambda: (sunat.descargar(), sunat.construir())))

    fallos = []
    for nombre, tarea in tareas:
        print(f"\n{nombre}")
        try:
            tarea()
        except Exception:
            fallos.append(nombre)
            traceback.print_exc(limit=2)
    if fallos:
        print(f"\nFALLARON: {', '.join(fallos)}")
        return 1
    print("\nTodo actualizado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

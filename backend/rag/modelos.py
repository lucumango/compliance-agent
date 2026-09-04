"""Comprueba que los modelos configurados siguen existiendo.

    python -m rag.modelos

Por qué hace falta. La cadena de respaldo existe para sobrevivir a que se agote
la cuota del modelo principal, así que el ÚLTIMO de la lista casi nunca se usa
—y es justo el que se pudre sin que nadie lo note—. `gemini-2.0-flash` estuvo
en la cadena hasta que Google lo retiró, y el fallo salió a la cara del usuario
como un 404 crudo el primer día que los dos primeros agotaron cuota.

No llama a ningún modelo: solo pide el catálogo. Es gratis y tarda un segundo,
así que cabe en la revisión mensual de docs/MANTENIMIENTO.md.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from .config import (
    API_BASE,
    EMBEDDING_DIM,
    MODEL_EMBEDDING,
    MODELOS_GENERACION,
    get_api_key,
)


def _catalogo() -> dict[str, list[str]]:
    req = urllib.request.Request(
        f"{API_BASE}/models?pageSize=200",
        headers={"x-goog-api-key": get_api_key()},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        datos = json.load(resp)
    return {
        m["name"].removeprefix("models/"): m.get("supportedGenerationMethods", [])
        for m in datos.get("models", [])
    }


def main() -> int:
    try:
        catalogo = _catalogo()
    except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
        print(f"No se pudo leer el catálogo de modelos: {e}")
        return 2

    problemas = 0
    print("Generación, en orden de preferencia:")
    for i, modelo in enumerate(MODELOS_GENERACION, 1):
        metodos = catalogo.get(modelo)
        if metodos is None:
            print(f"  {i}. {modelo}  ← NO EXISTE")
            problemas += 1
        elif "generateContent" not in metodos:
            print(f"  {i}. {modelo}  ← existe pero no genera texto")
            problemas += 1
        else:
            print(f"  {i}. {modelo}  ok")

    print(f"\nEmbeddings ({EMBEDDING_DIM} dimensiones):")
    metodos = catalogo.get(MODEL_EMBEDDING)
    if metodos is None:
        print(f"  {MODEL_EMBEDDING}  ← NO EXISTE")
        problemas += 1
    else:
        print(f"  {MODEL_EMBEDDING}  ok")

    if problemas:
        print(
            f"\n{problemas} problema(s). Actualiza rag/config.py.\n"
            "Cambiar el ÚLTIMO de la cadena no exige repetir rag.eval_prompt; "
            "cambiar el PRIMERO sí, porque es el que responde de verdad."
        )
        return 1

    print("\nTodo en orden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

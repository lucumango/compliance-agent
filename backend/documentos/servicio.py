"""Del archivo subido a fragmentos consultables.

Cuatro pasos: extraer, trocear, vectorizar y guardar. Los tres primeros son
locales; el cuarto escribe en Supabase con el token del usuario, así que row
level security decide qué puede tocar y el servidor no necesita saberlo.

El estado del documento se guarda antes de empezar y se cierra al terminar. Si
la vectorización falla a mitad, la fila queda en 'error' con el motivo en vez
de desaparecer: un documento que se sube y no aparece por ningún lado es peor
que uno que aparece marcado como fallido.
"""

from __future__ import annotations

import hashlib

import nube
from rag.gemini import BATCH_MAX, embed_batch

from .extraer import ErrorExtraccion, extraer, tipo_de
from .trocear import MAX_FRAGMENTOS, trocear


def _a_literal(vector: list[float]) -> str:
    """pgvector acepta el literal '[1,2,3]'; PostgREST manda JSON, y una lista
    de Python se serializaría como array de Postgres, que no es lo mismo."""
    return "[" + ",".join(f"{v:.7g}" for v in vector) + "]"


def procesar(
    *,
    token: str,
    usuario_id: str,
    nombre: str,
    datos: bytes,
    content_type: str | None,
) -> dict:
    tipo = tipo_de(nombre, content_type)
    bloques = extraer(datos, tipo)
    fragmentos = trocear(bloques)
    if not fragmentos:
        raise ErrorExtraccion("El documento no tiene texto suficiente para indexar.")

    paginas = max((b.pagina or 0) for b in bloques) or None
    sha = hashlib.sha256(datos).hexdigest()

    filas = nube.insertar(
        "documentos",
        token,
        [
            {
                "usuario_id": usuario_id,
                "nombre": nombre,
                "tipo": tipo,
                "bytes": len(datos),
                "sha256": sha,
                "paginas": paginas,
                "estado": "procesando",
            }
        ],
    )
    documento = filas[0]
    doc_id = documento["id"]

    try:
        pendientes = []
        for i in range(0, len(fragmentos), BATCH_MAX):
            lote = fragmentos[i : i + BATCH_MAX]
            vectores = embed_batch([f.texto for f in lote])
            pendientes.extend(
                {
                    "documento_id": doc_id,
                    "orden": f.orden,
                    "pagina": f.pagina,
                    "texto": f.texto,
                    "embedding": _a_literal(v),
                }
                for f, v in zip(lote, vectores, strict=True)
            )
            # Se escribe lote a lote y no todo al final: un documento largo
            # produce megabytes de vectores, y un solo POST con todo agota la
            # memoria del proceso y el tiempo de espera del proxy.
            nube.insertar("documento_fragmentos", token, pendientes, devolver=False)
            pendientes = []

        actualizados = nube.actualizar(
            "documentos",
            token,
            {"estado": "listo", "fragmentos": len(fragmentos)},
            id=f"eq.{doc_id}",
        )
        return actualizados[0] if actualizados else documento

    except Exception as e:
        nube.actualizar(
            "documentos",
            token,
            {"estado": "error", "error": str(e)[:500]},
            id=f"eq.{doc_id}",
        )
        raise


def listar(token: str) -> list[dict]:
    return nube.seleccionar(
        "documentos",
        token,
        select="id,nombre,tipo,bytes,paginas,fragmentos,estado,error,creado_en",
        order="creado_en.desc",
    )


def eliminar(token: str, documento_id: str) -> None:
    # Los fragmentos caen en cascada por la clave foránea.
    nube.borrar("documentos", token, id=f"eq.{documento_id}")


__all__ = ["MAX_FRAGMENTOS", "eliminar", "listar", "procesar"]

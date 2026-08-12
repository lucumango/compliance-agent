"""Construcción y carga del índice vectorial del corpus.

Un índice denso en numpy es suficiente a esta escala (cientos de unidades):
una búsqueda exhaustiva sobre 701 x 3072 tarda menos de un milisegundo. Migrar
a pgvector/Qdrant tiene sentido cuando el corpus crezca o haya multi-tenancy,
no antes.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .config import INDEX_DIR, PARSED_DIR
from .gemini import BATCH_MAX, embed_batch

VECTORS_PATH = INDEX_DIR / "vectors.npy"
META_PATH = INDEX_DIR / "unidades.json"


@dataclass
class Unidad:
    id: str
    norma_id: str
    norma_nombre: str
    materia: str
    cita: str
    tipo_unidad: str
    documento: str
    numero: str
    titulo: str
    texto: str
    vigente: bool
    requiere_cotejo: bool
    notas_norma: str
    # Metadatos de la norma que la API sirve sin tener que leer data/parsed/,
    # que no viaja al contenedor de producción. Con valores por defecto para
    # que un unidades.json antiguo siga cargando.
    por_que_relevante: str = ""
    estado_texto: str = "consolidado"
    relaciones: list[dict] = field(default_factory=list)


def cargar_unidades() -> tuple[list[Unidad], list[str]]:
    """Devuelve las unidades del corpus y el texto que debe vectorizarse."""
    unidades: list[Unidad] = []
    textos: list[str] = []

    for path in sorted(PARSED_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        requiere_cotejo = data["extraccion"]["requiere_cotejo"]
        for u in data["unidades"]:
            unidades.append(
                Unidad(
                    id=u["id"],
                    norma_id=data["norma_id"],
                    norma_nombre=data["nombre"],
                    materia=data["materia"],
                    cita=u["cita"],
                    tipo_unidad=u["tipo_unidad"],
                    documento=u["documento"],
                    numero=str(u["numero"]),
                    titulo=u["titulo"],
                    texto=u["texto"],
                    vigente=u["vigente"],
                    requiere_cotejo=requiere_cotejo,
                    notas_norma=data["notas"],
                    por_que_relevante=data.get("por_que_relevante", ""),
                    estado_texto=data.get("estado_texto", "consolidado"),
                    relaciones=data.get("relaciones", []),
                )
            )
            textos.append(u["texto_para_embedding"])

    return unidades, textos


def construir(verbose: bool = True) -> None:
    unidades, textos = cargar_unidades()
    if verbose:
        print(f"Vectorizando {len(textos)} unidades con lotes de {BATCH_MAX}...")

    vectores: list[list[float]] = []
    inicio = time.time()
    for i in range(0, len(textos), BATCH_MAX):
        lote = textos[i : i + BATCH_MAX]
        vectores.extend(embed_batch(lote, task_type="RETRIEVAL_DOCUMENT"))
        if verbose:
            print(f"  {len(vectores)}/{len(textos)}", flush=True)

    matriz = np.array(vectores, dtype=np.float32)
    # Normalizar una vez al indexar convierte la similitud coseno en un simple
    # producto punto en cada consulta.
    matriz /= np.linalg.norm(matriz, axis=1, keepdims=True)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(VECTORS_PATH, matriz)
    META_PATH.write_text(
        json.dumps([u.__dict__ for u in unidades], ensure_ascii=False, indent=1)
    )

    if verbose:
        print(
            f"Índice guardado: {matriz.shape[0]} vectores x {matriz.shape[1]} dims "
            f"en {time.time() - inicio:.1f}s"
        )


def actualizar_metadatos(verbose: bool = True) -> None:
    """Reescribe unidades.json desde data/parsed/ sin tocar los vectores.

    Cambiar `por_que_relevante`, `notas` o las relaciones de una norma no
    altera el `texto_para_embedding` de ninguna unidad, así que revectorizar
    sería tirar seis minutos y cuota de embeddings para nada.

    Solo es válido si el corpus tiene exactamente las mismas unidades en el
    mismo orden. Si has añadido o quitado alguna, hace falta `construir()`.
    """
    unidades, _ = cargar_unidades()

    if not VECTORS_PATH.exists():
        raise FileNotFoundError(
            "No existe el índice. Constrúyelo con: python -m rag.index"
        )

    filas = np.load(VECTORS_PATH, mmap_mode="r").shape[0]
    if filas != len(unidades):
        raise ValueError(
            f"El corpus tiene {len(unidades)} unidades y el índice {filas} "
            "vectores. Han cambiado las unidades, no solo sus metadatos: "
            "reconstruye el índice con `python -m rag.index`."
        )

    META_PATH.write_text(
        json.dumps([u.__dict__ for u in unidades], ensure_ascii=False, indent=1)
    )
    if verbose:
        print(f"Metadatos actualizados: {len(unidades)} unidades, vectores intactos.")


def cargar() -> tuple[np.ndarray, list[Unidad]]:
    if not VECTORS_PATH.exists():
        raise FileNotFoundError(
            "No existe el índice. Constrúyelo con: python -m rag.index"
        )
    matriz = np.load(VECTORS_PATH)
    metadatos = json.loads(META_PATH.read_text())
    return matriz, [Unidad(**m) for m in metadatos]


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Construye el índice vectorial.")
    ap.add_argument(
        "--solo-metadatos",
        action="store_true",
        help=(
            "Reescribe unidades.json desde data/parsed/ sin revectorizar. "
            "Úsalo cuando solo cambien metadatos de la norma (notas, "
            "relaciones, por_que_relevante) y no el texto de las unidades."
        ),
    )
    args = ap.parse_args()

    if args.solo_metadatos:
        actualizar_metadatos()
    else:
        construir()

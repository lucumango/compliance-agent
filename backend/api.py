"""API HTTP del asistente.

    uvicorn api:app --reload --port 8000

El índice se carga una sola vez al arrancar: son 9 MB de vectores y releerlos
por petición añadiría cientos de milisegundos a cada consulta.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
# Pydantic evalúa las anotaciones en runtime, y el Python 3.9 del sistema no
# entiende `list[str] | None`. Los modelos usan typing explícito por eso.
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from auth import aviso_de_arranque, limitar_uso, verificar_clave
from rag.answer import preparar, responder, responder_stream
from rag.diagrama import generar_diagrama
from rag.gemini import GeminiError
from rag.multas import REGIMENES, estimar, uit_vigente
from rag.retrieval import Buscador

DESCARGO = (
    "Este asistente informa sobre normativa; no constituye asesoría legal. "
    "Verifica siempre contra la fuente oficial."
)

_estado: dict[str, Buscador] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _estado["buscador"] = Buscador()
    if (aviso := aviso_de_arranque()) is not None:
        print(aviso, flush=True)
    yield
    _estado.clear()


# Todo lo que consume cuota del modelo, o expone el corpus, va detrás de la
# clave y del límite por IP. /api/salud queda fuera a propósito: las
# plataformas de despliegue lo sondean sin cabeceras.
PROTEGIDO = [Depends(verificar_clave), Depends(limitar_uso)]


app = FastAPI(
    title="Asistente de Normativa y Compliance (Perú)",
    version="0.1.0",
    lifespan=lifespan,
)

# En desarrollo el frontend corre en otro puerto (Vite: 5173). En producción
# vive en otro dominio, así que los orígenes permitidos se configuran por
# entorno: ALLOWED_ORIGINS="https://mi-app.vercel.app,https://otra.com".
_ORIGENES_DEV = ["http://localhost:5173", "http://127.0.0.1:5173"]
_origenes_env = os.getenv("ALLOWED_ORIGINS", "").strip()
ORIGENES = (
    [o.strip() for o in _origenes_env.split(",") if o.strip()]
    if _origenes_env
    else _ORIGENES_DEV
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConsultaIn(BaseModel):
    consulta: str = Field(min_length=3, max_length=2000)
    k: int = Field(default=6, ge=1, le=15)
    materias: Optional[List[str]] = None
    con_diagrama: bool = True


class FuenteOut(BaseModel):
    etiqueta: str
    cita: str
    norma: str
    materia: str
    titulo: str
    texto: str
    score: float
    vigente: bool


class ConsultaOut(BaseModel):
    respuesta: str
    fuentes: List[FuenteOut]
    advertencias: List[str]
    diagrama: Optional[str]
    descargo: str


@app.get("/api/salud")
def salud() -> dict:
    buscador = _estado.get("buscador")
    anio, valor, fuente = uit_vigente()
    return {
        "ok": buscador is not None,
        "unidades_indexadas": len(buscador.unidades) if buscador else 0,
        "uit": {"anio": anio, "valor": valor, "fuente": fuente},
    }


@app.get("/api/normas", dependencies=PROTEGIDO)
def normas() -> list[dict]:
    """Corpus disponible, para que el frontend ofrezca filtros por materia."""
    buscador = _estado["buscador"]
    vistas: dict[str, dict] = {}
    for u in buscador.unidades:
        entrada = vistas.setdefault(
            u.norma_id,
            {
                "norma_id": u.norma_id,
                "nombre": u.norma_nombre,
                "materia": u.materia,
                "unidades": 0,
                "requiere_cotejo": u.requiere_cotejo,
                "por_que_relevante": u.por_que_relevante,
                "estado_texto": u.estado_texto,
            },
        )
        entrada["unidades"] += 1
    return sorted(vistas.values(), key=lambda n: n["nombre"])


@app.get("/api/grafo", dependencies=PROTEGIDO)
def grafo() -> dict:
    """Grafo de trazabilidad entre normas.

    Los nodos con `en_corpus: false` son normas que sabemos que existen y que
    afectan a las cargadas, pero cuyo texto no tenemos. Son la parte útil: el
    grafo sirve de mapa de cobertura además de trazar las relaciones.
    """
    buscador = _estado["buscador"]

    nodos: dict[str, dict] = {}
    aristas: list[dict] = []

    for u in buscador.unidades:
        if u.norma_id in nodos:
            continue
        nodos[u.norma_id] = {
            "id": u.norma_id,
            "nombre": u.norma_nombre,
            "materia": u.materia,
            "estado_texto": u.estado_texto,
            "requiere_cotejo": u.requiere_cotejo,
            "en_corpus": True,
        }
        for r in u.relaciones:
            destino = r["destino"]
            # Una norma referida que no está cargada entra igual como nodo,
            # marcada, para que el hueco se vea en vez de desaparecer.
            if destino not in nodos:
                nodos[destino] = {
                    "id": destino,
                    "nombre": destino,
                    "materia": None,
                    "estado_texto": None,
                    "requiere_cotejo": False,
                    "en_corpus": bool(r.get("en_corpus")),
                }
            aristas.append(
                {
                    "origen": u.norma_id,
                    "destino": destino,
                    "tipo": r["tipo"],
                    "nota": r.get("nota", ""),
                }
            )

    return {"nodos": list(nodos.values()), "aristas": aristas}


@app.post("/api/consultar", response_model=ConsultaOut, dependencies=PROTEGIDO)
def consultar(payload: ConsultaIn) -> ConsultaOut:
    try:
        resp = responder(
            payload.consulta,
            _estado["buscador"],
            k=payload.k,
            materias=payload.materias,
            con_diagrama=payload.con_diagrama,
        )
    except GeminiError as e:
        # 502: el fallo es del proveedor del modelo, no de la petición.
        raise HTTPException(status_code=502, detail=f"Error del modelo: {e}") from e

    return ConsultaOut(
        respuesta=resp.texto,
        fuentes=[
            FuenteOut(
                etiqueta=f"F{i}",
                cita=r.unidad.cita,
                norma=r.unidad.norma_nombre,
                materia=r.unidad.materia,
                titulo=r.unidad.titulo,
                texto=r.unidad.texto,
                score=round(r.score, 4),
                vigente=r.unidad.vigente,
            )
            for i, r in enumerate(resp.fuentes, 1)
        ],
        advertencias=resp.advertencias,
        diagrama=resp.diagrama,
        descargo=DESCARGO,
    )


def _sse(evento: str, dato: dict) -> str:
    """Un mensaje SSE: nombre de evento y una línea `data:` con el JSON.
    El doble salto de línea es lo que marca el fin del mensaje."""
    return f"event: {evento}\ndata: {json.dumps(dato, ensure_ascii=False)}\n\n"


@app.post("/api/consultar/stream", dependencies=PROTEGIDO)
def consultar_stream(payload: ConsultaIn) -> StreamingResponse:
    """Igual que /api/consultar pero emitiendo la respuesta por fragmentos.

    Orden de los eventos:
      fuentes  — en cuanto termina la recuperación (~1 s), para que el panel
                 de citas se pinte mientras el modelo redacta
      delta    — cada fragmento de texto
      fin      — señala el cierre e indica si procede pedir el diagrama

    El diagrama NO se genera aquí: duplicaría el tiempo (12 s -> 30 s) y el
    cliente ya puede pedirlo aparte a /api/diagrama cuando termine de leer.
    """
    # La recuperación ocurre ANTES de abrir el stream, y también llama al
    # modelo (para vectorizar la consulta). Sin este try, agotar la cuota de
    # embeddings salía como un 500 con traza en vez del 502 que devuelve
    # /api/consultar, y el frontend solo podía enseñar "Error 500".
    try:
        prep = preparar(
            payload.consulta,
            _estado["buscador"],
            k=payload.k,
            materias=payload.materias,
            con_diagrama=payload.con_diagrama,
        )
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=f"Error del modelo: {e}") from e

    def eventos():
        yield _sse(
            "fuentes",
            {
                "fuentes": [
                    {
                        "etiqueta": f"F{i}",
                        "cita": r.unidad.cita,
                        "norma": r.unidad.norma_nombre,
                        "materia": r.unidad.materia,
                        "titulo": r.unidad.titulo,
                        "texto": r.unidad.texto,
                        "score": round(r.score, 4),
                        "vigente": r.unidad.vigente,
                    }
                    for i, r in enumerate(prep.fuentes, 1)
                ],
                "advertencias": prep.advertencias,
            },
        )
        try:
            for fragmento in responder_stream(prep):
                yield _sse("delta", {"texto": fragmento})
        except GeminiError as e:
            # El stream ya está abierto, así que el error no puede devolverse
            # como código HTTP: viaja como un evento más.
            yield _sse("error", {"mensaje": str(e)})
            return

        yield _sse("fin", {"lleva_diagrama": prep.lleva_diagrama, "descargo": DESCARGO})

    return StreamingResponse(
        eventos(),
        media_type="text/event-stream",
        # Sin esto, un proxy intermedio puede acumular la respuesta y anular
        # la ventaja del streaming.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class DiagramaIn(BaseModel):
    respuesta: str = Field(min_length=20, max_length=20000)


@app.post("/api/diagrama", dependencies=PROTEGIDO)
def diagrama(payload: DiagramaIn) -> dict:
    """Genera el diagrama a partir de una respuesta ya redactada.

    Va aparte del stream para sacarlo del camino crítico: el usuario lee la
    respuesta mientras el diagrama se dibuja detrás.
    """
    return {"diagrama": generar_diagrama(payload.respuesta)}


class MultaIn(BaseModel):
    regimen: str
    gravedad: str
    anio: Optional[int] = None


@app.get("/api/regimenes", dependencies=PROTEGIDO)
def regimenes() -> list[dict]:
    return [
        {
            "id": r.id,
            "nombre": r.nombre,
            "fuente": r.articulo_cita,
            "gravedades": list(r.rangos),
        }
        for r in REGIMENES.values()
    ]


@app.post("/api/multa", dependencies=PROTEGIDO)
def multa(payload: MultaIn) -> dict:
    try:
        e = estimar(payload.regimen, payload.gravedad, payload.anio)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return e.__dict__ | {"descargo": DESCARGO}

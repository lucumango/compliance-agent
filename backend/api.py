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

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import agentes
import auditoria
import documentos as docs
import nube
from agentes import cuestionario
from auth import (
    Usuario,
    aviso_de_arranque,
    limitar_uso,
    usuario_opcional,
    usuario_requerido,
    verificar_clave,
)
from rag.answer import (
    PROMPT_VERSION,
    preparar,
    responder,
    responder_stream,
    version_prompt,
)
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
    # 8 y no 6: con 11 normas cargadas, seis plazas se llenan antes de llegar
    # al articulo que enumera lo que se pregunta. Ver docs/CORRECCIONES.md.
    k: int = Field(default=8, ge=1, le=15)
    materias: Optional[List[str]] = None
    con_diagrama: bool = True
    # Cuota separada, no parte de k: los documentos del usuario no compiten con
    # el corpus por las mismas plazas. Ver rag/documentos.py.
    k_documentos: int = Field(default=4, ge=0, le=8)
    # Qué agente responde. Un id desconocido cae en CARLOS en vez de dar 400:
    # una interfaz vieja tras un despliegue no debe dejar de funcionar.
    agente: Optional[str] = None


class FuenteOut(BaseModel):
    etiqueta: str
    cita: str
    norma: str
    materia: str
    titulo: str
    texto: str
    score: float
    vigente: bool


class DocumentoFuenteOut(BaseModel):
    """Un fragmento de un documento del usuario, citado en la respuesta.

    Se serializa aparte de FuenteOut y no como un caso suyo: la interfaz tiene
    que poder pintarlos distinto sin adivinar, porque confundir una política
    interna con una norma es el fallo que más caro sale aquí.
    """

    etiqueta: str
    cita: str
    documento: str
    documento_id: str
    pagina: Optional[int]
    texto: str
    score: float


class ConsultaOut(BaseModel):
    respuesta: str
    fuentes: List[FuenteOut]
    documentos: List[DocumentoFuenteOut]
    advertencias: List[str]
    diagrama: Optional[str]
    descargo: str
    # Qué produjo la respuesta. El frontend los guarda con el mensaje: sin
    # ellos, una respuesta del historial no se puede reproducir ni explicar.
    # `modelo` es el que respondió de verdad, no el configurado.
    modelo: Optional[str] = None
    prompt_version: str = PROMPT_VERSION
    # Qué agente respondió de verdad. Si se pidió uno que no existe, aquí se
    # ve cuál contestó en su lugar.
    agente: str = agentes.POR_DEFECTO.id


@app.get("/api/salud")
def salud() -> dict:
    buscador = _estado.get("buscador")
    anio, valor, fuente = uit_vigente()
    return {
        "ok": buscador is not None,
        "unidades_indexadas": len(buscador.unidades) if buscador else 0,
        "uit": {"anio": anio, "valor": valor, "fuente": fuente},
        # El frontend usa esto para decidir si enseña login e historial o
        # arranca en modo suelto, en vez de llevarlo en su propia variable de
        # entorno y arriesgarse a que discrepen.
        "cuentas": nube.configurado(),
        # Inventario de versiones: qué prompt está sirviendo este despliegue.
        # Sin esto no hay forma de saber, desde fuera, si lo desplegado es lo
        # que se evaluó. Ver docs/GOBERNANZA.md.
        "prompt_version": PROMPT_VERSION,
    }


@app.get("/api/agentes", dependencies=PROTEGIDO)
def catalogo_agentes() -> list[dict]:
    """Los agentes disponibles, con su alcance declarado.

    La interfaz lo usa para pintar el selector; el alcance viaja con él para
    que el usuario lea lo mismo que lee el modelo, y no una versión de
    marketing escrita aparte que acabe diciendo otra cosa.
    """
    return [
        {
            "id": a.id,
            "nombre": a.nombre,
            "acronimo": a.acronimo,
            "area": a.area,
            "alcance": a.alcance,
            "fuera_de_alcance": a.fuera_de_alcance,
            "materias": list(a.materias) if a.materias else None,
            "prompt_version": version_prompt(a),
        }
        for a in agentes.AGENTES.values()
    ]


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


def _documentos_out(resultados) -> list[dict]:
    return [
        {
            "etiqueta": f"D{i}",
            "cita": d.fragmento.cita,
            "documento": d.fragmento.documento_nombre,
            "documento_id": d.fragmento.documento_id,
            "pagina": d.fragmento.pagina,
            "texto": d.fragmento.texto,
            "score": round(d.score, 4),
        }
        for i, d in enumerate(resultados or [], 1)
    ]


@app.post("/api/consultar", response_model=ConsultaOut, dependencies=PROTEGIDO)
def consultar(
    payload: ConsultaIn, usuario: Optional[Usuario] = Depends(usuario_opcional)
) -> ConsultaOut:
    agente = agentes.obtener(payload.agente)
    try:
        resp = responder(
            payload.consulta,
            _estado["buscador"],
            k=payload.k,
            materias=payload.materias,
            con_diagrama=payload.con_diagrama,
            token=usuario.token if usuario else None,
            k_docs=payload.k_documentos,
            agente=agente,
        )
    except GeminiError as e:
        # 502: el fallo es del proveedor del modelo, no de la petición.
        raise HTTPException(status_code=502, detail=f"Error del modelo: {e}") from e

    auditoria.registrar(
        usuario.token if usuario else None,
        usuario.id if usuario else None,
        "consulta",
        modelo=resp.modelo,
        prompt_version=resp.prompt_version,
        corpus_unidades=len(_estado["buscador"].unidades),
        normas_citadas=[r.unidad.norma_id for r in resp.fuentes],
        documentos_citados=len(resp.documentos or []),
    )

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
        documentos=[DocumentoFuenteOut(**d) for d in _documentos_out(resp.documentos)],
        advertencias=resp.advertencias,
        diagrama=resp.diagrama,
        descargo=DESCARGO,
        modelo=resp.modelo,
        prompt_version=resp.prompt_version,
        agente=agente.id,
    )


def _sse(evento: str, dato: dict) -> str:
    """Un mensaje SSE: nombre de evento y una línea `data:` con el JSON.
    El doble salto de línea es lo que marca el fin del mensaje."""
    return f"event: {evento}\ndata: {json.dumps(dato, ensure_ascii=False)}\n\n"


@app.post("/api/consultar/stream", dependencies=PROTEGIDO)
def consultar_stream(
    payload: ConsultaIn, usuario: Optional[Usuario] = Depends(usuario_opcional)
) -> StreamingResponse:
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
    agente = agentes.obtener(payload.agente)
    try:
        prep = preparar(
            payload.consulta,
            _estado["buscador"],
            k=payload.k,
            materias=payload.materias,
            con_diagrama=payload.con_diagrama,
            token=usuario.token if usuario else None,
            k_docs=payload.k_documentos,
            agente=agente,
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
                "documentos": _documentos_out(prep.documentos),
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

        modelo = prep.modelo[0] if prep.modelo else None
        yield _sse(
            "fin",
            {
                "lleva_diagrama": prep.lleva_diagrama,
                "descargo": DESCARGO,
                "modelo": modelo,
                "prompt_version": prep.prompt_version,
                "agente": agente.id,
            },
        )
        # Al final y no al principio: hasta aquí no se sabe qué modelo de la
        # cadena respondió, y un evento sin esa columna no sirve para auditar.
        auditoria.registrar(
            usuario.token if usuario else None,
            usuario.id if usuario else None,
            "consulta",
            modelo=modelo,
            prompt_version=prep.prompt_version,
            corpus_unidades=len(_estado["buscador"].unidades),
            normas_citadas=[r.unidad.norma_id for r in prep.fuentes],
            documentos_citados=len(prep.documentos or []),
        )

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


# ---------------------------------------------------------- debida diligencia
# El cuestionario NO pasa por el modelo. Es una tabla de decisión sobre el
# artículo 16 de la Resolución SBS 789-2018, igual que el estimador de multas
# lo es sobre los rangos de sanción: la respuesta es la misma cada vez y cada
# requisito trae el inciso del que sale. Preguntárselo a un modelo sería
# introducir variación en algo que la norma ya dejó cerrado.


class CuestionarioIn(BaseModel):
    tipo: str
    detonadores: Optional[List[str]] = None


@app.get("/api/diego/detonadores", dependencies=PROTEGIDO)
def detonadores() -> dict:
    """Los hechos que escalan el régimen, separados por origen.

    Los de la norma llevan su inciso; los de la firma no llevan cita, porque no
    la tienen. La interfaz los pinta en dos grupos por la misma razón por la
    que las fuentes [F] y [D] se pintan distinto.
    """
    return {
        "tipos": list(cuestionario.TIPOS),
        "detonadores": [
            {
                "id": d.id,
                "etiqueta": d.etiqueta,
                "origen": d.origen,
                "cita": d.cita,
                "nota": d.nota,
            }
            for d in cuestionario.DETONADORES.values()
        ],
    }


@app.post("/api/diego/cuestionario", dependencies=PROTEGIDO)
def generar_cuestionario(payload: CuestionarioIn) -> dict:
    try:
        ev = cuestionario.evaluar(payload.tipo, payload.detonadores)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ev.como_dict() | {"descargo": DESCARGO}


# ------------------------------------------------------------- documentos
# El historial no pasa por aquí: el frontend habla con Supabase directamente y
# row level security lo aisla. Los documentos sí, porque vectorizarlos exige la
# clave de Gemini, que es del servidor y no puede bajar al navegador.


class DocumentoOut(BaseModel):
    id: str
    nombre: str
    tipo: str
    bytes: int
    paginas: Optional[int]
    fragmentos: int
    estado: str
    error: Optional[str]
    creado_en: str


@app.get("/api/documentos", response_model=List[DocumentoOut], dependencies=PROTEGIDO)
def listar_documentos(usuario: Usuario = Depends(usuario_requerido)):
    try:
        return docs.listar(usuario.token)
    except nube.ErrorNube as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@app.post("/api/documentos", response_model=DocumentoOut, dependencies=PROTEGIDO)
def subir_documento(
    archivo: UploadFile = File(...),
    usuario: Usuario = Depends(usuario_requerido),
):
    """Sube, extrae, trocea, vectoriza e indexa un PDF o DOCX.

    Es síncrono a propósito. Un trabajo en segundo plano necesitaría una cola y
    un sitio donde dejar el archivo mientras espera; para documentos de hasta
    20 MB la extracción y el indexado caben en la petición, y el usuario ve el
    resultado en vez de un "procesando" que no sabe cuándo termina.
    """
    datos = archivo.file.read()
    try:
        fila = docs.procesar(
            token=usuario.token,
            usuario_id=usuario.id,
            nombre=archivo.filename or "documento",
            datos=datos,
            content_type=archivo.content_type,
        )
    except docs.ErrorExtraccion as e:
        # 422: el archivo llegó bien, lo que no vale es su contenido.
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GeminiError as e:
        raise HTTPException(status_code=502, detail=f"Error del modelo: {e}") from e
    except nube.ErrorNube as e:
        mensaje = str(e)
        if "duplicate key" in mensaje or "23505" in mensaje:
            raise HTTPException(
                status_code=409, detail="Ese archivo ya está subido."
            ) from e
        raise HTTPException(status_code=502, detail=mensaje) from e
    auditoria.registrar(usuario.token, usuario.id, "documento_subido")
    return fila


@app.delete("/api/documentos/{documento_id}", status_code=204, dependencies=PROTEGIDO)
def borrar_documento(
    documento_id: str, usuario: Usuario = Depends(usuario_requerido)
) -> None:
    try:
        docs.eliminar(usuario.token, documento_id)
    except nube.ErrorNube as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    auditoria.registrar(usuario.token, usuario.id, "documento_borrado")

"""Autenticación por clave compartida y límite de uso por IP.

Lo que esto resuelve: hasta ahora cualquiera con la URL podía lanzar consultas
contra la cuota de Gemini del proyecto. `/api/diagrama` era el peor caso —
acepta 20.000 caracteres arbitrarios y los manda al modelo sin anclarlos a
ninguna fuente—, es decir, un proxy de LLM abierto.

Lo que NO resuelve, y conviene tener claro antes de desplegar:

  * Una clave compartida que viaja en el bundle del frontend es visible para
    cualquiera que abra las herramientas de desarrollo. Sirve contra el abuso
    de paso —bots, alguien que encuentra la URL— no contra alguien decidido.
  * No hay usuarios ni permisos. Todo el que tiene la clave puede todo.

El siguiente paso, cuando haga falta, son cuentas de verdad con el token
emitido por el servidor; el punto de enganche es `verificar_clave`.

Se activa solo si `API_KEY` está definida. Sin ella el servidor arranca abierto
—que es lo que quieres en local— y avisa por consola.
"""

from __future__ import annotations

import hmac
import os
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request

API_KEY = os.getenv("API_KEY", "").strip()

# Ventana deslizante por IP. Los valores por defecto son holgados para una
# herramienta interna: el objetivo es frenar un bucle descontrolado, no
# racionar el uso legítimo.
LIMITE_PETICIONES = int(os.getenv("RATE_LIMIT_PETICIONES", "30"))
LIMITE_VENTANA_SEG = int(os.getenv("RATE_LIMIT_VENTANA", "60"))

_historial: dict[str, deque[float]] = defaultdict(deque)


def _ip_cliente(request: Request) -> str:
    # Detrás de Render/Railway/Fly el socket es el del proxy, así que la IP
    # real llega en X-Forwarded-For. Se toma el primer salto, que es el
    # cliente; el resto de la cadena la añaden los proxies intermedios.
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


def verificar_clave(x_api_key: str = Header(default="")) -> None:
    """Dependencia de FastAPI: exige la clave si el servidor la tiene puesta."""
    if not API_KEY:
        return
    # compare_digest evita filtrar por tiempo cuánto prefijo de la clave se
    # acertó. Con una clave compartida el riesgo es remoto, pero comparar bien
    # no cuesta nada.
    if not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Falta la cabecera X-API-Key o no es válida.",
        )


def limitar_uso(request: Request) -> None:
    """Dependencia de FastAPI: ventana deslizante por IP.

    En memoria y por proceso: con varias réplicas cada una lleva su cuenta, así
    que el límite efectivo se multiplica por el número de instancias. Para un
    despliegue de una sola instancia —que es el caso— basta. Si algún día hay
    varias, esto se muda a Redis.
    """
    ahora = time.time()
    ip = _ip_cliente(request)
    marcas = _historial[ip]

    while marcas and ahora - marcas[0] > LIMITE_VENTANA_SEG:
        marcas.popleft()

    if len(marcas) >= LIMITE_PETICIONES:
        espera = int(LIMITE_VENTANA_SEG - (ahora - marcas[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas peticiones. Inténtalo en {espera} s.",
            headers={"Retry-After": str(espera)},
        )

    marcas.append(ahora)

    # Sin esto, un servidor de larga vida acumula una entrada por cada IP que
    # lo haya tocado alguna vez.
    if len(_historial) > 10_000:
        for clave in [k for k, v in _historial.items() if not v]:
            del _historial[clave]


def aviso_de_arranque() -> str | None:
    if API_KEY:
        return None
    return (
        "AVISO: API_KEY no está definida; la API acepta peticiones de "
        "cualquiera. Correcto en local, NO para un despliegue accesible."
    )

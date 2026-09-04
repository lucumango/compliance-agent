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

Desde que existe Supabase hay además cuentas de verdad. Las dos cosas conviven
a propósito:

  * la clave compartida sigue protegiendo el chat, para que un despliegue ya
    montado no deje de funcionar el día que se activan las cuentas;
  * el historial y los documentos exigen sesión, porque son datos con dueño y
    sin dueño no hay a quién atribuirlos ni de quién aislarlos.

`usuario_opcional` resuelve la sesión si viene, y `usuario_requerido` la exige.

Se activa solo si `API_KEY` está definida. Sin ella el servidor arranca abierto
—que es lo que quieres en local— y avisa por consola.
"""

from __future__ import annotations

import hmac
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

import nube

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


# ----------------------------------------------------------------- sesiones


@dataclass(frozen=True)
class Usuario:
    id: str
    email: str | None
    # Se guarda para reenviarlo a Supabase: cada escritura viaja con el token
    # de quien la pide, y así row level security decide en vez del servidor.
    token: str


def _token_de(cabecera: str) -> str:
    partes = cabecera.split(None, 1)
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1].strip()
    return ""


def usuario_opcional(authorization: str = Header(default="")) -> Usuario | None:
    """La sesión si el cliente la manda y es válida; None si no."""
    token = _token_de(authorization)
    if not token or not nube.configurado():
        return None
    try:
        datos = nube.usuario_de_token(token)
    except nube.ErrorNube:
        # Supabase inalcanzable no es lo mismo que credencial inválida. En el
        # camino opcional se degrada a sesión anónima: el chat sigue.
        return None
    if not datos:
        return None
    return Usuario(id=datos["id"], email=datos.get("email"), token=token)


def usuario_requerido(authorization: str = Header(default="")) -> Usuario:
    """Igual, pero falla si no hay sesión. Para lo que tiene dueño."""
    if not nube.configurado():
        raise HTTPException(
            status_code=503,
            detail=(
                "Este servidor no tiene cuentas configuradas. Falta "
                "SUPABASE_URL y SUPABASE_ANON_KEY."
            ),
        )
    token = _token_de(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Falta la sesión.")
    try:
        datos = nube.usuario_de_token(token)
    except nube.ErrorNube as e:
        raise HTTPException(
            status_code=503, detail="No se pudo verificar la sesión con Supabase."
        ) from e
    if not datos:
        raise HTTPException(status_code=401, detail="La sesión no es válida o expiró.")
    return Usuario(id=datos["id"], email=datos.get("email"), token=token)

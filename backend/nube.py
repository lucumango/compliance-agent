"""Cliente de Supabase sobre su API REST.

Dos decisiones que conviene no deshacer:

**Todo viaja con el token del usuario, nunca con `service_role`.** La clave de
servicio salta row-level security por diseño: un fallo con ella no filtra una
fila, filtra la tabla. Como cada petición ya trae el JWT de quien la hace, se
reenvía tal cual y Postgres aplica las políticas. El servidor no necesita
—y no tiene— credenciales capaces de leer datos ajenos.

**El token se valida contra Supabase, no localmente.** Verificarlo aquí
obligaría a conocer el algoritmo de firma del proyecto, que cambia entre
secreto compartido y claves asimétricas según cuándo se creó. Una llamada a
`/auth/v1/user` funciona en ambos casos; el resultado se cachea unos segundos
para no pagar el viaje en cada mensaje de un stream.

Si `SUPABASE_URL` no está definida, `configurado()` devuelve False y el resto
del sistema sigue funcionando sin cuentas, sin historial y sin documentos, que
es como corre hoy en local.
"""

from __future__ import annotations

import hashlib
import os
import time
from typing import Any

import httpx

from rag.config import _load_dotenv

_load_dotenv()

URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()

# Un usuario no cambia de identidad a media conversación, y un stream hace
# varias llamadas seguidas con el mismo token. Sesenta segundos ahorran ese
# viaje sin que una revocación tarde en notarse más de un minuto.
_CACHE_TTL_SEG = 60
_cache_usuarios: dict[str, tuple[float, dict]] = {}

TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def configurado() -> bool:
    return bool(URL and ANON_KEY)


class ErrorNube(RuntimeError):
    """Fallo al hablar con Supabase, con el detalle que devolvió."""


def _cabeceras(token: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    cabeceras = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if extra:
        cabeceras.update(extra)
    return cabeceras


def _revisar(resp: httpx.Response) -> Any:
    if resp.status_code >= 400:
        detalle = resp.text
        try:
            cuerpo = resp.json()
            detalle = cuerpo.get("message") or cuerpo.get("msg") or detalle
        except Exception:
            pass
        raise ErrorNube(f"Supabase {resp.status_code}: {detalle}")
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


# ------------------------------------------------------------------ usuarios


def usuario_de_token(token: str) -> dict | None:
    """Devuelve el usuario dueño del token, o None si no vale."""
    if not configurado() or not token:
        return None

    # La clave del caché es un hash: el token entero es una credencial y no
    # tiene por qué quedarse legible en memoria más de lo necesario.
    clave = hashlib.sha256(token.encode()).hexdigest()
    guardado = _cache_usuarios.get(clave)
    ahora = time.monotonic()
    if guardado and ahora - guardado[0] < _CACHE_TTL_SEG:
        return guardado[1]

    try:
        with httpx.Client(timeout=TIMEOUT) as cliente:
            resp = cliente.get(f"{URL}/auth/v1/user", headers=_cabeceras(token))
    except httpx.HTTPError as e:
        # Supabase caído no debe convertirse en "credencial inválida": quien
        # llama distingue el None de una excepción para responder 401 o 503.
        raise ErrorNube("No se pudo contactar con Supabase") from e

    if resp.status_code in (401, 403):
        return None
    usuario = _revisar(resp)
    if not isinstance(usuario, dict) or not usuario.get("id"):
        return None

    _cache_usuarios[clave] = (ahora, usuario)
    return usuario


# --------------------------------------------------------------- REST básico


def seleccionar(tabla: str, token: str, **params: str) -> list[dict]:
    with httpx.Client(timeout=TIMEOUT) as cliente:
        resp = cliente.get(
            f"{URL}/rest/v1/{tabla}", headers=_cabeceras(token), params=params
        )
    return _revisar(resp) or []


def insertar(tabla: str, token: str, filas: list[dict], devolver: bool = True) -> list[dict]:
    extra = {"Prefer": "return=representation" if devolver else "return=minimal"}
    with httpx.Client(timeout=TIMEOUT) as cliente:
        resp = cliente.post(
            f"{URL}/rest/v1/{tabla}", headers=_cabeceras(token, extra), json=filas
        )
    return _revisar(resp) or []


def actualizar(tabla: str, token: str, cambios: dict, **params: str) -> list[dict]:
    extra = {"Prefer": "return=representation"}
    with httpx.Client(timeout=TIMEOUT) as cliente:
        resp = cliente.patch(
            f"{URL}/rest/v1/{tabla}",
            headers=_cabeceras(token, extra),
            params=params,
            json=cambios,
        )
    return _revisar(resp) or []


def borrar(tabla: str, token: str, **params: str) -> None:
    with httpx.Client(timeout=TIMEOUT) as cliente:
        resp = cliente.delete(
            f"{URL}/rest/v1/{tabla}", headers=_cabeceras(token), params=params
        )
    _revisar(resp)


def rpc(nombre: str, token: str, **argumentos: Any) -> Any:
    with httpx.Client(timeout=TIMEOUT) as cliente:
        resp = cliente.post(
            f"{URL}/rest/v1/rpc/{nombre}",
            headers=_cabeceras(token),
            json=argumentos,
        )
    return _revisar(resp)

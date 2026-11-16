"""Rate limiting de los endpoints que se pueden atacar con credenciales.

Dos límites independientes por endpoint:

- **por IP**: frena a quien prueba muchas cuentas desde la misma conexión;
- **por cuenta**: frena a quien prueba muchas contraseñas contra la misma
  cuenta desde IPs distintas.

Los dos se cuentan por separado, así que ni un atacante que rota cuentas ni
uno que rota IPs se escapan del límite.

El límite por cuenta necesita saber a qué cuenta se está atacando, y esa
información solo existe en el cuerpo de la petición. ``AccountCaptureMiddleware``
lo extrae ahí y lo deja en el estado compartido del *scope* (``request.state``),
que es donde el limitador lo lee.
"""

import json
import os
from urllib.parse import parse_qs

from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Rutas cuyo cuerpo identifica la cuenta atacada.
ACCOUNT_PATHS = frozenset(
    {
        "/api/v1/auth/login",
        "/api/v1/auth/forgot-password",
    }
)

# Clave dentro de ``scope["state"]`` donde queda la cuenta detectada.
ACCOUNT_STATE_KEY = "rate_limit_account"

# Valor por defecto de los límites. Se pueden ajustar por entorno sin tocar
# el código, y las pruebas los bajan o suben según lo que necesitan.
DEFAULT_LOGIN_LIMIT_PER_MINUTE = 5
DEFAULT_FORGOT_PASSWORD_LIMIT_PER_MINUTE = 5
# El refresco tiene un límite más alto: una sesión legítima renueva el token
# cada hora, y varias pestañas pueden pedirlo a la vez.
DEFAULT_REFRESH_LIMIT_PER_MINUTE = 30

LOGIN_LIMIT_PER_MINUTE = int(
    os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", str(DEFAULT_LOGIN_LIMIT_PER_MINUTE))
)
FORGOT_PASSWORD_LIMIT_PER_MINUTE = int(
    os.getenv(
        "RATE_LIMIT_FORGOT_PASSWORD_PER_MINUTE",
        str(DEFAULT_FORGOT_PASSWORD_LIMIT_PER_MINUTE),
    )
)
REFRESH_LIMIT_PER_MINUTE = int(
    os.getenv("RATE_LIMIT_REFRESH_PER_MINUTE", str(DEFAULT_REFRESH_LIMIT_PER_MINUTE))
)

# Tope del cuerpo que se lee para detectar la cuenta. Es un login o un
# forgot-password: unos bytes. Si alguien manda algo enorme, se deja de leer
# y la cuenta queda como "desconocida" (el límite por IP sigue aplicando).
MAX_ACCOUNT_BODY_BYTES = 8 * 1024


def _limit_provider(per_minute: int):
    """Devuelve el proveedor del límite, que slowapi evalúa en cada petición.

    Se lee el valor en cada comprobación (y no al importar el módulo) para que
    las pruebas puedan ajustarlo sin recargar la aplicación.
    """

    def provider(key: str) -> str:
        return f"{per_minute}/minute"

    return provider


limiter = Limiter(key_func=get_remote_address, default_limits=[], headers_enabled=True)


def ip_key(request: Request) -> str:
    """Clave del límite por IP."""
    return get_remote_address(request)


def account_key(request: Request) -> str:
    """Clave del límite por cuenta.

    Si la cuenta no se pudo detectar (cuerpo inesperado, petición de otro
    cliente, ...) se usa una clave fija: de todos modos el límite por IP sigue
    aplicando, y agrupar lo desconocido bajo una sola clave evita que el
    límite por cuenta sea el que se puede esquivar con cuentas inventadas.
    """
    scope_state = request.scope.get("state") or {}
    account = scope_state.get(ACCOUNT_STATE_KEY)
    if not account:
        return "unknown-account"
    return str(account)


def refresh_account_key(request: Request) -> str:
    """Clave del límite por cuenta en el refresco de token.

    Aquí la cuenta no viene en el cuerpo sino en el token de refresco que
    viaja en la cabecera ``Authorization``. Se leen sus claims **sin
    verificar** (la firma la comprueba el endpoint): para contar hace falta
    una clave, no una autorización.
    """
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return "unknown-account"
    try:
        payload = jwt.get_unverified_claims(header[len("bearer ") :].strip())
    except Exception:
        return "unknown-account"
    subject = payload.get("sub")
    if not subject:
        return "unknown-account"
    return f"refresh:{subject}"


def _header(scope: Scope, name: str) -> str:
    wanted = name.lower().encode()
    for key, value in scope.get("headers") or []:
        if key.lower() == wanted:
            return value.decode("latin-1")
    return ""


def _normalize_account(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    account = raw.strip().lower()
    if not account:
        return ""
    # Una clave de límite no necesita ser el correo entero: acota el tamaño
    # de lo que se guarda como clave.
    return account[:128]


def extract_account(scope: Scope, body: bytes) -> str:
    """Saca la cuenta (usuario o correo) del cuerpo de la petición."""
    content_type = _header(scope, "content-type").lower()

    if "application/json" in content_type:
        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return ""
        if not isinstance(payload, dict):
            return ""
        return _normalize_account(payload.get("email") or payload.get("username"))

    if "application/x-www-form-urlencoded" in content_type:
        try:
            parsed = parse_qs(body.decode("utf-8", "replace"))
        except Exception:
            return ""
        values = parsed.get("username") or parsed.get("email") or []
        if not values:
            return ""
        return _normalize_account(values[0])

    return ""


async def _read_body(receive: Receive) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            break
        chunk = message.get("body", b"")
        chunks.append(chunk)
        total += len(chunk)
        if not message.get("more_body", False):
            break
        if total > MAX_ACCOUNT_BODY_BYTES:
            break
    return b"".join(chunks)


def _replay(body: bytes) -> Receive:
    """Devuelve un ``receive`` que entrega el cuerpo una sola vez.

    El cuerpo se leyó antes de que llegara al endpoint, así que hay que
    reenviarlo: sin esto, el login no recibiría su formulario.
    """
    delivered = False

    async def receive() -> Message:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive


class AccountCaptureMiddleware:
    """Deja la cuenta atacada disponible para el limitador.

    Lee el cuerpo de las rutas de autenticación, guarda la cuenta en
    ``scope["state"]`` (que el endpoint y el limitador comparten) y reenvía el
    cuerpo intacto para que la validación normal del formulario siga viendo
    exactamente lo mismo.
    """

    def __init__(self, app: ASGIApp, paths: frozenset[str] | None = None):
        self.app = app
        self.paths = ACCOUNT_PATHS if paths is None else paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in self.paths:
            await self.app(scope, receive, send)
            return

        body = await _read_body(receive)
        account = extract_account(scope, body)
        scope.setdefault("state", {})[ACCOUNT_STATE_KEY] = account

        await self.app(scope, _replay(body), send)

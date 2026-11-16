"""Endurecimiento de los tokens: tipo, revocación, un solo uso y límites.

Lo que un token robado o reutilizado no debe poder hacer:

- servir después de que cambien las credenciales de la cuenta (contraseña,
  rol o baja): el token lleva la versión de la cuenta y deja de coincidir;
- abrir sesión cuando es un token de reset, ni resetear la contraseña cuando
  es un token de acceso: cada tipo solo vale para lo suyo;
- canjearse dos veces: un token de reset es de un solo uso;
- abrir la puerta a fuerza bruta: el login y el forgot-password están
  limitados por IP y por cuenta.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from jose import jwt
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.core.cors import build_allowed_origins
from app.core.rate_limit import account_key, extract_account
from app.core.security import Security
from app.main import app
from app.models.models import User, UserRole
from app.services.auth_service import (
    ALGORITHM,
    SECRET_KEY,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_PASSWORD_RESET,
    TOKEN_TYPE_REFRESH,
    create_password_reset_token,
)
from tests.conftest import TestingSessionLocal

LOCALHOST_ORIGIN = "http://localhost:3000"
FOREIGN_ORIGIN = "http://attacker.example.com"


def _create_user(username: str, role: UserRole = UserRole.OPERATOR) -> int:
    """Crea un usuario desechable y devuelve su id."""
    db = TestingSessionLocal()
    user = User(
        first_name="Hardening",
        last_name="Test",
        username=username,
        email=f"{username}@test.com",
        hashed_password=Security.get_password_hash("testpass123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()
    return user_id


def _user_version(username: str) -> int:
    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == username).first()
    version = user.token_version or 0
    db.close()
    return version


async def _login(client: AsyncClient, username: str, password: str = "testpass123"):
    response = await client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Los claims del token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_access_token_carries_the_user_id_and_its_type(
    client: AsyncClient, test_users, test_locations
):
    """``sub`` es el id del usuario (no el username) y ``typ`` dice qué es."""
    token = await _login(client, "admin")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["typ"] == TOKEN_TYPE_ACCESS
    assert payload["sub"].isdigit()
    assert payload["ver"] == _user_version("admin")


@pytest.mark.asyncio
async def test_login_with_email_still_works(
    client: AsyncClient, test_users, test_locations
):
    """El login acepta correo o username, y el token resuelve igual."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "testpass123"},
    )
    assert response.status_code == 200, response.text

    token = response.json()["access_token"]
    me = await client.get("/api/v1/user/me", headers=_bearer(token))
    assert me.status_code == 200
    assert me.json()["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_access_token_expires_in_about_60_minutes(
    client: AsyncClient, test_users, test_locations
):
    """El token de acceso dura una hora, no las nueve de antes."""
    token = await _login(client, "admin")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    delta = datetime.fromtimestamp(payload["exp"], tz=UTC) - datetime.now(UTC)
    assert timedelta(minutes=55) < delta <= timedelta(minutes=60)


@pytest.mark.asyncio
async def test_a_token_without_type_is_rejected(
    client: AsyncClient, test_users, test_locations
):
    """Un token sin ``typ`` no abre sesión.

    Es lo que pasa con los tokens emitidos antes de este cambio: no se puede
    saber si eran de acceso o de reset, así que no se aceptan.
    """
    payload = {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=10)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    response = await client.get("/api/v1/user/me", headers=_bearer(token))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 2. Revocación: un token viejo deja de servir
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_old_token_is_rejected_after_a_password_change(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Cambiar la contraseña cierra las sesiones que estaban abiertas."""
    _create_user("hp-password")
    token = await _login(client, "hp-password")
    headers = _bearer(token)

    assert (await client.get("/api/v1/user/me", headers=headers)).status_code == 200

    change = await client.put(
        "/api/v1/user/me/password",
        json={"current_password": "testpass123", "new_password": "nueva-clave-123"},
        headers=headers,
    )
    assert change.status_code == 204, change.text

    after = await client.get("/api/v1/user/me", headers=headers)
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_old_token_is_rejected_after_a_role_change(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Cambiar el rol cierra las sesiones abiertas con el rol anterior.

    Si no, un token de operador seguiría valiendo como token de manager
    hasta que se venciera.
    """
    user_id = _create_user("hp-role")
    token = await _login(client, "hp-role")
    headers = _bearer(token)

    assert (await client.get("/api/v1/user/me", headers=headers)).status_code == 200

    change = await client.put(
        f"/api/v1/user/{user_id}",
        json={"role": "manager"},
        headers=auth_headers,
    )
    assert change.status_code == 200, change.text

    after = await client.get("/api/v1/user/me", headers=headers)
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_old_token_is_rejected_after_deactivation(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Dar de baja una cuenta cierra sus sesiones abiertas."""
    user_id = _create_user("hp-deactivated")
    token = await _login(client, "hp-deactivated")
    headers = _bearer(token)

    assert (await client.get("/api/v1/user/me", headers=headers)).status_code == 200

    change = await client.put(
        f"/api/v1/user/{user_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert change.status_code == 200, change.text

    after = await client.get("/api/v1/user/me", headers=headers)
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_a_token_with_a_stale_version_is_rejected(
    client: AsyncClient, test_users, test_locations
):
    """La versión del token tiene que coincidir con la de la cuenta."""
    token = await _login(client, "admin")

    db = TestingSessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    admin.token_version = (admin.token_version or 0) + 1
    db.commit()
    db.close()

    response = await client.get("/api/v1/user/me", headers=_bearer(token))
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 3. Cada tipo de token solo sirve para lo suyo
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_token_used_as_access_token_returns_401(
    client: AsyncClient, test_users, test_locations
):
    """Un token de reset no abre sesión: responde 401."""
    reset_token = create_password_reset_token("admin@test.com", 0)

    response = await client.get("/api/v1/user/me", headers=_bearer(reset_token))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_access_token_used_as_reset_token_is_rejected(
    client: AsyncClient, test_users, test_locations
):
    """Un token de acceso no resetea contraseñas: responde 400."""
    token = await _login(client, "admin")

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "clave-nueva-123"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 4. El token de reset es de un solo uso
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_token_cannot_be_used_twice(
    client: AsyncClient, test_users, test_locations
):
    """Canjear el token de reset lo deja sin uso.

    El token queda atado a la versión de la cuenta: canjearlo cambia la
    contraseña y sube la versión, así que el mismo token ya no encuentra la
    versión que espera.
    """
    _create_user("hp-reset")

    with patch(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        new=AsyncMock(return_value=None),
    ) as send:
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "hp-reset@test.com"}
        )
    assert response.status_code == 200
    reset_token = send.call_args.kwargs["reset_token"]

    first = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "clave-nueva-123"},
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "otra-clave-123"},
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_reset_token_is_revoked_by_a_password_change(
    client: AsyncClient, test_users, test_locations
):
    """Un token de reset emitido antes de un cambio de credenciales no sirve."""
    _create_user("hp-reset-old")

    with patch(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        new=AsyncMock(return_value=None),
    ) as send:
        await client.post(
            "/api/v1/auth/forgot-password", json={"email": "hp-reset-old@test.com"}
        )
    reset_token = send.call_args.kwargs["reset_token"]

    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "hp-reset-old").first()
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    db.close()

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "clave-nueva-123"},
    )
    assert response.status_code == 400


def test_reset_token_expires_in_15_minutes():
    """El token de reset conserva su caducidad de 15 minutos."""
    token = create_password_reset_token("admin@test.com", 0)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert payload["typ"] == TOKEN_TYPE_PASSWORD_RESET
    delta = datetime.fromtimestamp(payload["exp"], tz=UTC) - datetime.now(UTC)
    assert timedelta(minutes=14) < delta <= timedelta(minutes=15)


# ---------------------------------------------------------------------------
# 5. Rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_rate_limit_answers_429(
    client: AsyncClient, test_users, test_locations
):
    """Pasado el límite, el login responde 429."""
    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "contrasena-incorrecta"},
        )
        assert response.status_code == 401, response.text

    blocked = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "contrasena-incorrecta"},
    )
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_forgot_password_rate_limit_answers_429(
    client: AsyncClient, test_users, test_locations
):
    """Pasado el límite, el forgot-password responde 429."""
    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/forgot-password", json={"email": "nadie-aqui@test.com"}
        )
        assert response.status_code == 200, response.text

    blocked = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nadie-aqui@test.com"}
    )
    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_the_account_limit_counts_across_different_ips(
    client: AsyncClient, test_users, test_locations
):
    """El límite por cuenta cuenta aunque cada intento venga de otra IP.

    Cada intento sale de una IP distinta, así que el límite por IP no llega a
    completarse: el 429 solo puede venir del límite por cuenta.
    """
    for attempt in range(5):
        async with AsyncClient(
            transport=ASGITransport(app=app, client=(f"10.0.0.{attempt}", 1234)),
            base_url="http://test",
        ) as other:
            response = await other.post(
                "/api/v1/auth/login",
                data={"username": "admin", "password": "contrasena-incorrecta"},
            )
            assert response.status_code == 401, response.text

    async with AsyncClient(
        transport=ASGITransport(app=app, client=("10.0.0.99", 1234)),
        base_url="http://test",
    ) as other:
        blocked = await other.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "contrasena-incorrecta"},
        )

    assert blocked.status_code == 429


def test_the_account_is_read_from_the_request_body():
    """La cuenta se extrae del formulario (login) y del JSON (forgot-password)."""
    form_scope = {
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
    }
    assert extract_account(form_scope, b"username=Admin%40Test.com&password=x") == (
        "admin@test.com"
    )

    json_scope = {"headers": [(b"content-type", b"application/json")]}
    assert (
        extract_account(json_scope, b'{"email": "Admin@Test.com"}') == "admin@test.com"
    )

    # Sin content-type reconocible no se inventa una cuenta.
    assert extract_account({}, b"username=admin") == ""


def test_the_account_key_falls_back_when_nothing_was_captured():
    """Si no se pudo leer la cuenta, la clave es una sola y known."""
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [],
            "query_string": b"",
            "state": {},
        }
    )
    assert account_key(request) == "unknown-account"

    request.scope["state"]["rate_limit_account"] = "admin@test.com"
    assert account_key(request) == "admin@test.com"


# ---------------------------------------------------------------------------
# 5b. El refresco de token: la sesión sobrevive a la caducidad del acceso
# ---------------------------------------------------------------------------


async def _login_full(client: AsyncClient, username: str) -> dict:
    response = await client.post(
        "/api/v1/auth/login", data={"username": username, "password": "testpass123"}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_the_login_response_carries_a_refresh_token(
    client: AsyncClient, test_users, test_locations
):
    """El login entrega un token de refresco y la vida del token de acceso."""
    payload = await _login_full(client, "admin")

    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 60 * 60
    assert payload["refresh_token"]

    claims = jwt.decode(payload["refresh_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims["typ"] == TOKEN_TYPE_REFRESH
    assert claims["sub"].isdigit()


@pytest.mark.asyncio
async def test_the_refresh_endpoint_issues_a_new_access_token(
    client: AsyncClient, test_users, test_locations
):
    """Un token de refresco válido da un token de acceso nuevo."""
    payload = await _login_full(client, "admin")

    response = await client.post(
        "/api/v1/auth/refresh",
        headers=_bearer(payload["refresh_token"]),
    )
    assert response.status_code == 200, response.text

    data = response.json()
    # El token puede salir idéntico al anterior si se firma dentro del mismo
    # segundo (los claims son los mismos): lo que importa es que sea válido.
    claims = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert claims["typ"] == TOKEN_TYPE_ACCESS
    assert claims["sub"].isdigit()

    # El token nuevo sirve para llamar a la API.
    me = await client.get("/api/v1/user/me", headers=_bearer(data["access_token"]))
    assert me.status_code == 200


@pytest.mark.asyncio
async def test_an_access_token_cannot_be_used_to_refresh(
    client: AsyncClient, test_users, test_locations
):
    """Un token de acceso no sirve para refrescar: solo el de refresco."""
    payload = await _login_full(client, "admin")

    response = await client.post(
        "/api/v1/auth/refresh", headers=_bearer(payload["access_token"])
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_a_reset_token_cannot_be_used_to_refresh(
    client: AsyncClient, test_users, test_locations
):
    """Un token de reset tampoco sirve para refrescar."""
    reset_token = create_password_reset_token("admin@test.com", 0)

    response = await client.post("/api/v1/auth/refresh", headers=_bearer(reset_token))
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_the_refresh_endpoint_needs_a_token(
    client: AsyncClient, test_users, test_locations
):
    """Sin token de refresco, el endpoint responde 401."""
    response = await client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_a_refresh_token_is_revoked_after_a_password_change(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Cambiar la contraseña cierra también la sesión que se iba a refrescar."""
    _create_user("hp-refresh")
    payload = await _login_full(client, "hp-refresh")

    change = await client.put(
        "/api/v1/user/me/password",
        json={"current_password": "testpass123", "new_password": "nueva-clave-123"},
        headers=_bearer(payload["access_token"]),
    )
    assert change.status_code == 204, change.text

    response = await client.post(
        "/api/v1/auth/refresh", headers=_bearer(payload["refresh_token"])
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_a_refresh_token_stops_working_after_deactivation(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """Dar de baja la cuenta también cierra el refresco."""
    user_id = _create_user("hp-refresh-off")
    payload = await _login_full(client, "hp-refresh-off")

    change = await client.put(
        f"/api/v1/user/{user_id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert change.status_code == 200, change.text

    response = await client.post(
        "/api/v1/auth/refresh", headers=_bearer(payload["refresh_token"])
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_the_refresh_endpoint_is_rate_limited(
    client: AsyncClient, test_users, test_locations
):
    """El refresco también tiene límite: no es una puerta libre a tokens."""
    payload = await _login_full(client, "admin")

    for _ in range(30):
        response = await client.post(
            "/api/v1/auth/refresh", headers=_bearer(payload["refresh_token"])
        )
        assert response.status_code == 200, response.text

    blocked = await client.post(
        "/api/v1/auth/refresh", headers=_bearer(payload["refresh_token"])
    )
    assert blocked.status_code == 429


# ---------------------------------------------------------------------------
# 6. CORS: localhost solo en desarrollo
# ---------------------------------------------------------------------------


def test_localhost_origins_are_only_added_in_development():
    """En producción la lista no incluye ningún origen de localhost."""
    production = build_allowed_origins(
        env="production", frontend_url="https://thunderroll.vercel.app"
    )
    assert LOCALHOST_ORIGIN not in production
    assert "http://frontend:3000" not in production
    assert "https://thunderroll.vercel.app" in production

    development = build_allowed_origins(
        env="development", frontend_url="https://thunderroll.vercel.app"
    )
    assert LOCALHOST_ORIGIN in development
    assert "http://frontend:3000" in development


@pytest.mark.asyncio
async def test_cors_does_not_allow_localhost_outside_development():
    """Una app montada como producción no responde a localhost.

    La comprobación va contra el middleware real de CORS: si el origen no
    está en la lista, el navegador no puede leer la respuesta.
    """
    production_app = FastAPI()
    production_app.add_middleware(
        CORSMiddleware,
        allow_origins=build_allowed_origins(
            env="production", frontend_url="https://thunderroll.vercel.app"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @production_app.get("/ping")
    async def ping():
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=production_app), base_url="http://test"
    ) as ac:
        localhost_response = await ac.get("/ping", headers={"Origin": LOCALHOST_ORIGIN})
        allowed_response = await ac.get(
            "/ping", headers={"Origin": "https://thunderroll.vercel.app"}
        )

    assert "access-control-allow-origin" not in localhost_response.headers
    assert (
        allowed_response.headers.get("access-control-allow-origin")
        == "https://thunderroll.vercel.app"
    )


@pytest.mark.asyncio
async def test_cors_allows_localhost_in_development(
    client: AsyncClient, test_users, test_locations
):
    """En desarrollo el frontend de localhost sí puede hablar con la API."""
    response = await client.get(
        "/api/v1/units/",
        headers={"Origin": LOCALHOST_ORIGIN},
    )
    assert response.headers.get("access-control-allow-origin") == LOCALHOST_ORIGIN

    foreign = await client.get(
        "/api/v1/units/",
        headers={"Origin": FOREIGN_ORIGIN},
    )
    assert "access-control-allow-origin" not in foreign.headers

"""La IP que usa el rate limit cuando la petición viene detrás de un proxy.

El problema que se arregla: detrás de un proxy, `request.client.host` es la
dirección del proxy, no la del cliente. Con esa clave, los 5 logins por
minuto se comparten entre todos los usuarios.

Y el riesgo que se evita: `X-Forwarded-For` lo puede escribir el cliente, así
que no se puede usar tal cual (ni el valor de la izquierda, ni con
`--forwarded-allow-ips=*`, que hace que uvicorn tome justo el valor que
escribe el cliente).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.client_ip import get_client_ip, is_trusted_proxy
from app.main import app

# Direcciones de prueba.
CLIENT_A = "198.51.100.10"  # cliente público (no es un proxy de confianza)
CLIENT_B = "198.51.100.11"  # otro cliente público
PROXY = "10.0.0.7"  # proxy en la red privada (como el de Render)
LOOPBACK = "127.0.0.1"


def make_request(
    peer: str | None = CLIENT_A,
    forwarded_for: str | None = None,
    headers: dict[str, str] | None = None,
) -> Request:
    """Una petición ASGI con la dirección de conexión que se le pida."""
    raw_headers = [(b"host", b"test")]
    if forwarded_for is not None:
        raw_headers.append((b"x-forwarded-for", forwarded_for.encode()))
    for name, value in (headers or {}).items():
        raw_headers.append((name.encode().lower(), value.encode()))

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": raw_headers,
        "query_string": b"",
        "client": (peer, 1234) if peer else None,
        "state": {},
    }
    return Request(scope)


# ---------------------------------------------------------------------------
# La resolución de la IP
# ---------------------------------------------------------------------------


def test_without_the_header_it_uses_the_connection_address():
    """Sin header, la clave es la dirección de la conexión."""
    request = make_request(peer=CLIENT_A)
    assert get_client_ip(request) == CLIENT_A


def test_a_trusted_proxy_wins_over_the_connection_address():
    """Desde un proxy de confianza, se usa la IP que él puso en el header."""
    request = make_request(peer=PROXY, forwarded_for="203.0.113.9")
    assert get_client_ip(request) == "203.0.113.9"


def test_the_client_cannot_pick_its_own_bucket():
    """Un X-Forwarded-For falsificado no decide la clave.

    El cliente solo puede *anteponer* valores: lo que añade el proxy siempre
    queda a la derecha, y esa es la que se usa.
    """
    request = make_request(peer=PROXY, forwarded_for="1.2.3.4, 203.0.113.9")
    assert get_client_ip(request) == "203.0.113.9"


def test_a_spoofed_header_from_an_untrusted_peer_is_ignored():
    """Si la conexión no viene de un proxy de confianza, el header no se lee.

    Es el caso de quien alcanza la API directamente: puede escribir el header
    que quiera, y no sirve de nada.
    """
    request = make_request(peer=CLIENT_A, forwarded_for="1.2.3.4")
    assert get_client_ip(request) == CLIENT_A


def test_an_entry_that_is_not_an_ip_falls_back_to_the_connection():
    """Un valor que no es una IP no puede ser la clave."""
    request = make_request(peer=PROXY, forwarded_for="no-es-una-ip")
    assert get_client_ip(request) == PROXY


def test_an_empty_header_falls_back_to_the_connection():
    request = make_request(peer=PROXY, forwarded_for="   ")
    assert get_client_ip(request) == PROXY


def test_without_a_connection_address_it_falls_back_to_unknown():
    request = make_request(peer=None)
    assert get_client_ip(request) == "unknown"


def test_the_hops_setting_skips_entries_from_the_right(monkeypatch):
    """Con dos proxies delante, la IP del cliente está una posición más a la izquierda."""
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    request = make_request(peer=PROXY, forwarded_for="203.0.113.9, 10.0.0.3")
    assert get_client_ip(request) == "203.0.113.9"


def test_the_trusted_proxies_are_configurable(monkeypatch):
    """La lista de proxies de confianza se puede cambiar por entorno."""
    assert is_trusted_proxy(PROXY) is True
    assert is_trusted_proxy(CLIENT_A) is False

    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "198.51.100.0/24")
    assert is_trusted_proxy(CLIENT_A) is True
    assert is_trusted_proxy(PROXY) is False

    monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "*")
    assert is_trusted_proxy(CLIENT_A) is True
    assert is_trusted_proxy("cualquiera") is True


def test_the_loopback_is_trusted_by_default():
    """En local, el proxy y la app están en la misma máquina."""
    assert is_trusted_proxy(LOOPBACK) is True


# ---------------------------------------------------------------------------
# El efecto sobre el rate limit
# ---------------------------------------------------------------------------


async def _login(client: AsyncClient, username: str, headers: dict | None = None):
    return await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": "contrasena-incorrecta"},
        headers=headers or {},
    )


@pytest.mark.asyncio
async def test_two_clients_with_different_ips_have_separate_buckets(
    client: AsyncClient, test_users, test_locations
):
    """Cada IP tiene su propio presupuesto de intentos.

    Con la clave equivocada (la del proxy) los dos compartirían cubeta y el
    segundo recibiría un 429 sin haber intentado nada.

    Cada uno usa una cuenta distinta a propósito: el límite por cuenta es
    otro cubeta, y lo que se quiere medir aquí es el de IP.
    """
    async with (
        AsyncClient(
            transport=ASGITransport(app=app, client=(CLIENT_A, 1234)),
            base_url="http://test",
        ) as first,
        AsyncClient(
            transport=ASGITransport(app=app, client=(CLIENT_B, 1234)),
            base_url="http://test",
        ) as second,
    ):
        for _ in range(5):
            response = await _login(first, "admin")
            assert response.status_code == 401, response.text

        # El primer cliente ya agotó el presupuesto de su IP...
        blocked = await _login(first, "admin")
        assert blocked.status_code == 429

        # ...pero el segundo va con otra IP y con otra cuenta: ni se entera.
        response = await _login(second, "inventario")
        assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_a_spoofed_forwarded_for_does_not_bypass_the_limit(
    client: AsyncClient, test_users, test_locations
):
    """Un X-Forwarded-For falsificado no sirve para saltarse el límite.

    La conexión viene de un peer que no es un proxy de confianza, así que el
    header se ignora y la clave sigue siendo la IP real del cliente: cambiarlo
    en cada intento no abre cubetas nuevas.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(CLIENT_A, 1234)),
        base_url="http://test",
    ) as spoofed:
        for attempt in range(5):
            response = await _login(
                spoofed, "admin", headers={"X-Forwarded-For": f"10.0.0.{attempt}"}
            )
            assert response.status_code == 401, response.text

        blocked = await _login(
            spoofed, "admin", headers={"X-Forwarded-For": "10.0.0.99"}
        )

    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_a_client_behind_a_proxy_cannot_choose_its_own_bucket(
    client: AsyncClient, test_users, test_locations
):
    """Detrás de un proxy, un X-Forwarded-For falsificado no abre cubeta nueva.

    El cliente solo puede anteponer valores: lo que agrega el proxy queda a
    la derecha, y esa es la que se usa como clave. Por eso los 5 intentos
    comparten cubeta aunque cada uno se haga pasar por una IP distinta.

    Cada intento usa además una cuenta distinta, para que lo único que pueda
    dispararlo sea la cubeta de IP.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(PROXY, 1234)), base_url="http://test"
    ) as first:
        for attempt in range(5):
            response = await _login(
                first,
                f"probe-{attempt}",
                headers={"X-Forwarded-For": f"203.0.113.{attempt}, 198.51.100.50"},
            )
            assert response.status_code == 401, response.text

        # El spoof no abre una cubeta nueva: la clave es la que puso el proxy.
        blocked = await _login(
            first,
            "probe-final",
            headers={"X-Forwarded-For": "203.0.113.99, 198.51.100.50"},
        )

    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_two_clients_behind_a_proxy_have_separate_buckets(
    client: AsyncClient, test_users, test_locations
):
    """Dos clientes reales detrás del mismo proxy sí van a cubetas distintas.

    Es el caso que se quería arreglar: sin resolver la IP, los dos usuarios
    comparten la cubeta del proxy. Aquí cada uno trae su propia IP en el
    header, y cada uno tiene su presupuesto.
    """
    async with (
        AsyncClient(
            transport=ASGITransport(app=app, client=(PROXY, 1234)),
            base_url="http://test",
        ) as first,
        AsyncClient(
            transport=ASGITransport(app=app, client=(PROXY, 1234)),
            base_url="http://test",
        ) as second,
    ):
        for _ in range(5):
            response = await _login(
                first, "admin", headers={"X-Forwarded-For": "198.51.100.60"}
            )
            assert response.status_code == 401, response.text

        blocked = await _login(
            first, "admin", headers={"X-Forwarded-For": "198.51.100.60"}
        )
        assert blocked.status_code == 429

        # El otro cliente viene de otra IP: su cubeta está intacta.
        response = await _login(
            second, "inventario", headers={"X-Forwarded-For": "198.51.100.61"}
        )
        assert response.status_code == 401, response.text

"""La IP que usa el rate limit cuando la petición viene detrás de un proxy.

El problema que se arregla: detrás de un proxy, `request.client.host` es la
dirección del proxy, no la del cliente. Con esa clave, los 5 logins por
minuto se comparten entre todos los usuarios.

Y el riesgo que se evita: `X-Forwarded-For` lo puede escribir el cliente, así
que no se puede usar tal cual. En Render queda demostrado: el header llega a
la app tal cual lo mandó el cliente, así que usarlo como clave dejaría el
límite esquivable cambiando la IP en cada petición. La cabecera fiable es
`CF-Connecting-IP`: la pone Cloudflare y rechaza (403, error 1000) las
peticiones que traen su propia copia.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.client_ip import get_client_ip
from app.main import app

# Direcciones de prueba.
CLIENT_A = "198.51.100.10"  # cliente que conectó (lo que pone Cloudflare)
CLIENT_B = "198.51.100.11"  # otro cliente que conectó
PROXY = "10.0.0.7"  # el proxy, en la red privada


def make_request(
    peer: str | None = CLIENT_A,
    headers: dict[str, str] | None = None,
) -> Request:
    """Una petición ASGI con la dirección de conexión que se le pida."""
    raw_headers = [(b"host", b"test")]
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


def test_without_any_header_it_uses_the_connection_address():
    """Sin la cabecera de Cloudflare, la clave es la dirección de la conexión."""
    request = make_request(peer=PROXY)
    assert get_client_ip(request) == PROXY


def test_the_cloudflare_header_wins_over_the_connection_address():
    """Con Cloudflare delante, se usa la IP que él puso."""
    request = make_request(peer=PROXY, headers={"CF-Connecting-IP": CLIENT_A})
    assert get_client_ip(request) == CLIENT_A


def test_the_forwarded_for_is_ignored():
    """`X-Forwarded-For` no se usa: Render lo pasa tal cual lo manda el cliente.

    Si se usara, un cliente podría escribir su IP ahí y repartirse el límite
    como quisiera (comprobado en producción).
    """
    request = make_request(
        peer=PROXY,
        headers={"X-Forwarded-For": "9.9.9.9", "CF-Connecting-IP": CLIENT_A},
    )
    assert get_client_ip(request) == CLIENT_A

    # Y sin Cloudflare tampoco: el header no pesa.
    request = make_request(peer=PROXY, headers={"X-Forwarded-For": "9.9.9.9"})
    assert get_client_ip(request) == PROXY


def test_a_cloudflare_header_that_is_not_an_ip_is_ignored():
    """Un valor que no es una IP no puede ser la clave."""
    request = make_request(peer=PROXY, headers={"CF-Connecting-IP": "no-es-una-ip"})
    assert get_client_ip(request) == PROXY


def test_without_a_connection_address_it_falls_back_to_unknown():
    request = make_request(peer=None)
    assert get_client_ip(request) == "unknown"


def test_the_cloudflare_header_is_stripped():
    """Los espacios alrededor de la IP no estorban."""
    request = make_request(peer=PROXY, headers={"CF-Connecting-IP": "  203.0.113.9  "})
    assert get_client_ip(request) == "203.0.113.9"


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
                first, "admin", headers={"CF-Connecting-IP": CLIENT_A}
            )
            assert response.status_code == 401, response.text

        # El primer cliente ya agotó el presupuesto de su IP...
        blocked = await _login(first, "admin", headers={"CF-Connecting-IP": CLIENT_A})
        assert blocked.status_code == 429

        # ...pero el segundo viene de otra IP: ni se entera.
        response = await _login(
            second, "inventario", headers={"CF-Connecting-IP": CLIENT_B}
        )
        assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_a_spoofed_forwarded_for_does_not_bypass_the_limit(
    client: AsyncClient, test_users, test_locations
):
    """Un X-Forwarded-For falsificado no sirve para saltarse el límite.

    El header se ignora, así que la clave sigue siendo la IP real del cliente
    y cambiarlo en cada intento no abre cubetas nuevas.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(PROXY, 1234)), base_url="http://test"
    ) as spoofed:
        for attempt in range(5):
            response = await _login(
                spoofed,
                f"spoof-{attempt}",
                headers={
                    "X-Forwarded-For": f"10.0.0.{attempt}",
                    "CF-Connecting-IP": CLIENT_A,
                },
            )
            assert response.status_code == 401, response.text

        blocked = await _login(
            spoofed,
            "spoof-final",
            headers={"X-Forwarded-For": "10.0.0.99", "CF-Connecting-IP": CLIENT_A},
        )

    assert blocked.status_code == 429


@pytest.mark.asyncio
async def test_without_the_cloudflare_header_it_uses_the_connection_address(
    client: AsyncClient, test_users, test_locations
):
    """Sin Cloudflare (local, otros despliegues) la clave es el peer.

    Y sin cabecera de Cloudflare tampoco hay forma de que el cliente elija su
    cubeta: la clave es la dirección de la conexión, que no controla.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(CLIENT_A, 1234)),
        base_url="http://test",
    ) as direct:
        for _ in range(5):
            response = await _login(direct, "admin")
            assert response.status_code == 401, response.text

        blocked = await _login(direct, "admin")

    assert blocked.status_code == 429

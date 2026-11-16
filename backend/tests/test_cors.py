"""CORS: what the browser is allowed to do with the API.

The frontend runs on a different origin than the API (Vercel vs Render), so
the browser applies CORS to every request the app makes. A misconfigured CORS
breaks the app in production while everything works in development, because
``http://localhost:3000`` is on the default allow list.

These tests go through the real ``CORSMiddleware`` of the app (the ASGI
client is not a browser, but the middleware does not care).
"""

import pytest
from httpx import AsyncClient

ALLOWED_ORIGIN = "http://localhost:3000"
FOREIGN_ORIGIN = "http://attacker.example.com"


@pytest.mark.asyncio
async def test_allowed_origin_is_answered(
    client: AsyncClient, auth_headers, test_users
):
    """The frontend's origin gets the green light."""
    response = await client.get(
        "/api/v1/units/",
        headers={**auth_headers, "Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


@pytest.mark.asyncio
async def test_unknown_origin_is_not_allowed(
    client: AsyncClient, auth_headers, test_users
):
    """A foreign origin gets no permission to read the response."""
    response = await client.get(
        "/api/v1/units/",
        headers={**auth_headers, "Origin": FOREIGN_ORIGIN},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_preflight_allows_the_authorization_header(
    client: AsyncClient, test_users
):
    """The browser asks before sending the Bearer token; it must be allowed.

    Every authenticated request carries ``Authorization``, so if the
    preflight did not allow it, the browser would block the call before it
    was ever sent.
    """
    response = await client.options(
        "/api/v1/user/me",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    allowed_headers = response.headers.get("access-control-allow-headers", "")
    assert "authorization" in allowed_headers.lower()


@pytest.mark.asyncio
async def test_preflight_of_a_foreign_origin_is_refused(
    client: AsyncClient, test_users
):
    """The preflight of an unknown origin does not authorize anything."""
    response = await client.options(
        "/api/v1/user/me",
        headers={
            "Origin": FOREIGN_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_total_count_header_is_exposed_to_the_browser(
    client: AsyncClient, auth_headers, test_users
):
    """``X-Total-Count`` must be readable by the browser.

    The units list reads that header for the pagination count. A browser
    only exposes the headers the server lists in
    ``Access-Control-Expose-Headers``: without it the count silently falls
    back to the length of the current page.
    """
    response = await client.get(
        "/api/v1/units/",
        headers={**auth_headers, "Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    exposed = response.headers.get("access-control-expose-headers", "")
    assert "X-Total-Count" in exposed

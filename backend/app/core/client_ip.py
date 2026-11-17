"""La IP del cliente cuando la petición viene detrás de un proxy.

Detrás de un proxy (Render en producción, el contenedor del frontend en local)
la dirección de la conexión **no** es la del cliente: es la del proxy. Si el
rate limit se keya por esa dirección, todos los usuarios comparten la misma
cubeta (5 logins por minuto entre todos).

De dónde sale la IP real:

``CF-Connecting-IP``
    La pone el edge de **Cloudflare** (en Render, el que está delante de la
    app) con la IP de quien conectó. Cloudflare además **rechaza** las
    peticiones que traen su propia copia de esa cabecera (403, *error code
    1000*), así que el valor no se puede falsificar: o es el de verdad, o la
    petición no llega.

``request.client.host``
    La dirección de la conexión. Es la del proxy si hay uno, pero es la
    única fiable cuando no hay Cloudflare delante (local, otros despliegues).

**``X-Forwarded-For`` no se usa, y es a propósito.** El header lo escribe el
cliente primero y cada proxy debería *añadir* la suya al final, así que la
entrada de la derecha sería la del proxy. Pero Render **no lo hace**: pasa el
header del cliente tal cual, sin anteponerle nada. Comprobado en producción:
con ``X-Forwarded-For`` falsificado, la clave del límite cambió con el valor
falsificado y el límite se podía saltar. Con ``CF-Connecting-IP`` no pasa:
Cloudflare sustituye el valor y rechaza las copias.
"""

import ipaddress

from starlette.requests import Request

# Cabeceras que Cloudflare pone con la IP real del cliente que conectó.
CLOUDFLARE_IP_HEADERS = ("cf-connecting-ip",)

UNKNOWN_IP = "unknown"


def _is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def get_client_ip(request: Request) -> str:
    """La IP que se usa para el rate limiting.

    La cabecera de Cloudflare si viene (no se puede falsificar); si no, la
    dirección de la conexión.
    """
    for header in CLOUDFLARE_IP_HEADERS:
        value = request.headers.get(header)
        if value:
            value = value.strip()
            if _is_valid_ip(value):
                return value

    return request.client.host if request.client else UNKNOWN_IP

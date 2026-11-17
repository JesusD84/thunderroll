"""La IP del cliente cuando la petición viene detrás de un proxy.

Detrás de un proxy (Render en producción, el contenedor del frontend en local)
la dirección de la conexión **no** es la del cliente: es la del proxy. Si el
rate limit se keya por esa dirección, todos los usuarios comparten la misma
cubeta (5 logins por minuto entre todos).

La IP del cliente viaja en ``X-Forwarded-For``. Ese header lo escribe el
cliente primero y **cada proxy añade la suya al final**, así que:

- las entradas de la **izquierda** las puede poner cualquiera, y por eso no se
  usan: un cliente podría escribir su propia IP ahí y quedarse con la cubeta
  que le conviene;
- la entrada de la **derecha** la puso el último proxy, y esa es la que se
  usa. El cliente no la controla: como solo puede *anteponer* valores, lo que
  añada el proxy siempre queda a la derecha.

Para no fiarnos de un header que puede venir de cualquiera, **solo se lee si
la conexión viene de un proxy de confianza** (``TRUSTED_PROXY_CIDRS``). Si la
petición llega de cualquier otro sitio, se usa la dirección de la conexión.

Configuración (variables de entorno):

``TRUSTED_PROXY_CIDRS``
    Direcciones o CIDR desde las que se acepta el header, separados por comas.
    Por defecto, las redes privadas y el loopback: de ahí es de donde se
    conectan los proxies propios (el balanceador de Render en producción, el
    contenedor del frontend en local). ``*`` acepta cualquier peer: solo es
    seguro si el proceso no es alcanzable directamente desde internet.

``TRUSTED_PROXY_HOPS``
    Cuántas entradas del extremo derecho se descartan antes de tomar la IP.
    ``0`` (por defecto) toma la de la derecha, que es la que agregó el proxy.
    Súbelo si hay más proxies entre el cliente y la app y su IP está más a la
    izquierda.
"""

import ipaddress
import os
from functools import lru_cache

from starlette.requests import Request

# Redes privadas + loopback. El balanceador de Render se conecta desde el
# espacio de direcciones privado (su guía lo dice: hay que limitar
# `--forwarded-allow-ips` a "las IPs privadas o los bloques CIDR de sus
# balanceadores").
DEFAULT_TRUSTED_PROXY_CIDRS = (
    "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
)

# Cuántas entradas del extremo derecho se descartan. 0 = se usa la de la
# derecha, que es la que agregó el proxy.
DEFAULT_TRUSTED_PROXY_HOPS = 0

UNKNOWN_IP = "unknown"


@lru_cache(maxsize=16)
def _parse_networks(value: str) -> tuple:
    """Convierte la lista de CIDR en redes. Lo que no parsea se ignora."""
    networks = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return tuple(networks)


def _trusted_proxy_cidrs() -> str:
    return os.getenv("TRUSTED_PROXY_CIDRS", DEFAULT_TRUSTED_PROXY_CIDRS).strip()


def _trusted_proxy_hops() -> int:
    try:
        return max(
            0, int(os.getenv("TRUSTED_PROXY_HOPS", str(DEFAULT_TRUSTED_PROXY_HOPS)))
        )
    except ValueError:
        return DEFAULT_TRUSTED_PROXY_HOPS


def is_trusted_proxy(peer: str | None) -> bool:
    """¿La conexión viene de un proxy al que se le cree el header?"""
    if not peer:
        return False
    cidrs = _trusted_proxy_cidrs()
    if cidrs == "*":
        return True
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(address in network for network in _parse_networks(cidrs))


def get_client_ip(request: Request) -> str:
    """La IP que se usa para el rate limiting.

    Sin ``X-Forwarded-For`` (o si el peer no es de confianza) es la dirección
    de la conexión. Con el header y un peer de confianza, es la entrada que
    agregó el proxy: la de la derecha, menos las que se descarten con
    ``TRUSTED_PROXY_HOPS``.
    """
    peer = request.client.host if request.client else UNKNOWN_IP

    header = request.headers.get("x-forwarded-for")
    if not header:
        return peer

    # El header solo vale si viene de nuestro propio proxy. Si lo aceptáramos
    # de cualquiera, un cliente podría escribir su IP ahí y repartirse el
    # límite como quisiera.
    if not is_trusted_proxy(peer):
        return peer

    entries = [item.strip() for item in header.split(",") if item.strip()]
    if not entries:
        return peer

    # Las entradas de la derecha son las que puso la infraestructura; las de
    # la izquierda las pudo escribir el cliente. Nos quedamos con la que
    # agregó nuestro último proxy.
    index = max(0, len(entries) - 1 - _trusted_proxy_hops())
    candidate = entries[index]

    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        # Un valor que no es una IP no sirve de clave: mejor la dirección de
        # la conexión, que siempre es real.
        return peer
    return candidate

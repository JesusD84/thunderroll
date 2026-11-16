"""Configuración del entorno, validada al importar el módulo.

Las variables obligatorias se validan cuando se importa este módulo, no cuando
se usan: es preferible que la aplicación NO arranque a que firme los JWT con
una clave conocida por todos o que apunte a una base de datos cuya credencial
esté escrita en el repositorio.

Ninguna de estas variables tiene un valor de respaldo. Un default fijo en el
código es un secreto público: el repositorio es público y cualquier valor
"por defecto" termina en las manos de quien lea el código.
"""

import os

from dotenv import load_dotenv

# El `.env` local vive en la raíz del repo (es el que lee docker-compose).
# Se carga aquí, una sola vez, para que todas las validaciones de este módulo
# vean exactamente las mismas variables.
load_dotenv()

# Longitud mínima de la clave de firma de los JWT. Una clave más corta es
# adivinable y una clave ausente haría que la app firmara tokens con un valor
# público.
MIN_SECRET_KEY_LENGTH = 32


class ConfigurationError(RuntimeError):
    """Variable de entorno obligatoria ausente o con un valor inválido."""


def require_secret_key() -> str:
    """Devuelve la clave de firma de los JWT o falla con un error claro.

    Se lee exclusivamente del entorno. Si la variable no está definida o es
    más corta que ``MIN_SECRET_KEY_LENGTH`` se lanza ``ConfigurationError``:
    la app no debe arrancar en ese estado, porque firmaría tokens con una
    clave que cualquiera puede conocer.
    """
    key = os.getenv("SECRET_KEY", "").strip()
    if not key:
        raise ConfigurationError(
            "SECRET_KEY no está definida. El backend no puede arrancar sin la "
            "clave de firma de los JWT. Genera una aleatoria de 32 caracteres o "
            "más con: openssl rand -hex 32"
        )
    if len(key) < MIN_SECRET_KEY_LENGTH:
        raise ConfigurationError(
            f"SECRET_KEY es demasiado corta: {len(key)} caracteres, se requieren "
            f"al menos {MIN_SECRET_KEY_LENGTH}. Genera una aleatoria de 32 "
            "caracteres o más con: openssl rand -hex 32"
        )
    return key


def require_database_url() -> str:
    """Devuelve la URL de la base de datos o falla con un error claro.

    No hay valor de respaldo: apuntar a una URL fija en el código significa
    publicar una credencial (y además rompería en cuanto cambien host, puerto
    o nombre de base).
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise ConfigurationError(
            "DATABASE_URL no está definida. El backend no puede arrancar sin la "
            "URL de la base de datos. Ejemplo: "
            "postgresql://usuario:password@localhost:5432/thunderoll"
        )
    return url

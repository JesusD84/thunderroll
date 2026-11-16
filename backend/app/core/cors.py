"""CORS: qué orígenes puede usar el navegador contra la API.

El frontend corre en un origen distinto al de la API (Vercel vs Render), así
que el navegador aplica CORS a cada llamada. La lista de orígenes permitidos
se arma aquí, en un solo lugar, para que quede claro qué se abre y por qué.

Los orígenes de ``localhost`` solo se admiten en desarrollo: en producción
permitirlos abriría la API a cualquier página que se sirva en el puerto 3000
de la máquina de quien la visite.
"""

import os

# Valores de ``ENV`` que cuentan como desarrollo.
DEVELOPMENT_ENV = "development"

# ``ENV`` es la variable que manda. ``ENVIRONMENT`` se acepta como alias
# porque es la que ya usaba el ``.env`` del proyecto.
ENV_VARS = ("ENV", "ENVIRONMENT")

# Orígenes locales: el frontend de Next.js en desarrollo y el servicio
# ``frontend`` de docker-compose.
LOCALHOST_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://frontend:3000",
)


def is_development(env: str | None = None) -> bool:
    """¿El entorno es de desarrollo?

    Sin argumentos lee ``ENV`` y, si no está, ``ENVIRONMENT``.
    """
    if env is not None:
        value = env
    else:
        value = ""
        for name in ENV_VARS:
            value = os.getenv(name, "")
            if value:
                break
    return (value or "").strip().lower() == DEVELOPMENT_ENV


def build_allowed_origins(
    env: str | None = None,
    frontend_url: str | None = None,
    extra_origins: str | None = None,
) -> list[str]:
    """Arma la lista de orígenes permitidos.

    - En desarrollo se suman los orígenes de ``localhost``.
    - ``FRONTEND_URL`` es el origen del frontend en producción.
    - ``ALLOWED_ORIGINS`` es una lista separada por comas para los orígenes
      de Vercel (producción y previews).
    """
    origins: list[str] = []

    if is_development(env):
        origins.extend(LOCALHOST_ORIGINS)

    if frontend_url is None:
        frontend_url = os.getenv("FRONTEND_URL", "")
    frontend_url = (frontend_url or "").strip()
    if frontend_url and frontend_url not in origins:
        origins.append(frontend_url)

    if extra_origins is None:
        extra_origins = os.getenv("ALLOWED_ORIGINS", "")
    for origin in (extra_origins or "").split(","):
        origin = origin.strip()
        if origin and origin not in origins:
            origins.append(origin)

    return origins

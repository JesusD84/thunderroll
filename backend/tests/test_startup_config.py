"""Tests de arranque: la app exige configuración válida y falla sin ella.

La validación vive en `app/core/config.py` y corre al importar la app, así que
estos tests lanzan un subproceso limpio (import desde cero) en lugar de tocar
el proceso de pytest, que ya tiene la app importada con la configuración de
prueba de `conftest.py`.

El subproceso neutraliza la carga del `.env` local: si el archivo del
desarrollador trae un `SECRET_KEY`, el test "arranca sin SECRET_KEY" no
fallaría y no estaríamos probando nada.
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

# 64 caracteres hexadecimales: pasa la validación de longitud de
# `app/core/config.py`. Se genera en vez de escribirse literal porque un
# literal de 32+ caracteres de alta entropía es indistinguible de un secreto
# filtrado, y gitleaks (que corre en cada PR) lo marcaría como tal.
VALID_SECRET_KEY = secrets.token_hex(32)

# Neutraliza `load_dotenv` ANTES de importar la app: `app/core/config.py` hace
# `from dotenv import load_dotenv`, así que recibe la versión parcheada.
NEUTRALIZE_DOTENV = """
import dotenv

dotenv.load_dotenv = lambda *args, **kwargs: False
"""

IMPORT_APP = """
from app.main import app

print("APP_IMPORTED", app.title)
"""

# Arranca de verdad: el lifespan crea el esquema y siembra el admin bootstrap.
START_APP = """
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    response = client.get("/health")

print("HEALTH_STATUS", response.status_code)
"""


def _run(script: str, env_overrides: dict[str, str], timeout: int = 120):
    """Ejecuta el script en un subproceso con un entorno controlado."""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        # Los mensajes de error están en español: forzamos UTF-8 en el hijo
        # para que no dependan de la configuración regional de la máquina.
        "PYTHONIOENCODING": "utf-8",
    }
    env.update(env_overrides)

    return subprocess.run(
        [sys.executable, "-c", NEUTRALIZE_DOTENV + script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=str(BACKEND_DIR),
        timeout=timeout,
    )


def test_app_fails_to_start_without_secret_key():
    """Sin SECRET_KEY la app no arranca y lo dice con un error claro."""
    result = _run(IMPORT_APP, {"DATABASE_URL": "sqlite:///:memory:"})

    assert result.returncode != 0, (
        f"La app arrancó sin SECRET_KEY.\nstdout: {result.stdout}"
    )
    assert "ConfigurationError" in result.stderr
    assert "SECRET_KEY" in result.stderr
    # El mensaje dice cómo resolverlo, no solo qué falta.
    assert "openssl rand -hex 32" in result.stderr


def test_app_fails_to_start_with_short_secret_key():
    """Una SECRET_KEY de menos de 32 caracteres tampoco vale."""
    result = _run(
        IMPORT_APP,
        {"DATABASE_URL": "sqlite:///:memory:", "SECRET_KEY": "corta"},
    )

    assert result.returncode != 0, (
        f"La app arrancó con una SECRET_KEY corta.\nstdout: {result.stdout}"
    )
    assert "ConfigurationError" in result.stderr
    assert "SECRET_KEY" in result.stderr
    assert "al menos 32" in result.stderr
    assert "openssl rand -hex 32" in result.stderr


def test_app_fails_to_start_without_database_url():
    """Sin DATABASE_URL la app no arranca (no hay URL de respaldo en el código)."""
    result = _run(IMPORT_APP, {"SECRET_KEY": VALID_SECRET_KEY})

    assert result.returncode != 0, (
        f"La app arrancó sin DATABASE_URL.\nstdout: {result.stdout}"
    )
    assert "ConfigurationError" in result.stderr
    assert "DATABASE_URL" in result.stderr


def test_app_starts_with_valid_secret_key(tmp_path):
    """Con SECRET_KEY válida y DATABASE_URL, la app arranca y responde."""
    db_file = tmp_path / "startup.db"

    result = _run(
        START_APP,
        {
            "SECRET_KEY": VALID_SECRET_KEY,
            "DATABASE_URL": f"sqlite:///{db_file}",
        },
    )

    assert result.returncode == 0, (
        f"La app no arrancó con una configuración válida.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "HEALTH_STATUS 200" in result.stdout


def test_secret_key_length_boundary(monkeypatch):
    """El límite es 32 caracteres: 32 vale, 31 no."""
    from app.core.config import ConfigurationError, require_secret_key

    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    assert require_secret_key() == "x" * 32

    monkeypatch.setenv("SECRET_KEY", "x" * 31)
    with pytest.raises(ConfigurationError, match="al menos 32"):
        require_secret_key()

    monkeypatch.setenv("SECRET_KEY", "   ")
    with pytest.raises(ConfigurationError, match="SECRET_KEY"):
        require_secret_key()

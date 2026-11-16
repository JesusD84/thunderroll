"""Almacenamiento seguro y limitado de los archivos subidos por el usuario.

Este módulo concentra las reglas de "subida de archivos":

- El archivo **nunca** se guarda con el nombre que envía el cliente. Ese
  nombre no es confiable (puede traer ``../``, rutas absolutas o bytes de
  control), así que se genera uno en el servidor (``uuid4`` + extensión
  validada) dentro de un directorio que ninguna ruta de la API sirve. El
  nombre original se conserva solo como metadata.
- Los límites (tamaño del archivo, filas por hoja, hojas por archivo) se
  aplican **mientras** se lee el archivo, no después: un archivo enorme se
  corta en el primer bloque que rebasa el límite.
- Los problemas del usuario se reportan con excepciones tipadas, que el
  endpoint traduce a 400/413/422 con un mensaje legible. La causa raíz nunca
  se devuelve al cliente: se registra en el log del servidor.

El módulo no importa FastAPI: recibe objetos file-like, de modo que el parser
(puro, pandas + stdlib) pueda reutilizar los límites sin depender de la web.
"""

from __future__ import annotations

import logging
import ntpath
import os
import re
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

logger = logging.getLogger(__name__)

# --- Extensiones aceptadas -------------------------------------------------

ALLOWED_EXTENSIONS: tuple[str, ...] = (".xlsx", ".xls", ".csv")

# --- Límites (configurables por entorno) -----------------------------------

DEFAULT_MAX_UPLOAD_SIZE_MB = 10
DEFAULT_MAX_ROWS_PER_SHEET = 20_000
DEFAULT_MAX_SHEETS = 50

ENV_MAX_UPLOAD_SIZE_MB = "MAX_UPLOAD_SIZE_MB"
ENV_MAX_ROWS_PER_SHEET = "MAX_IMPORT_ROWS_PER_SHEET"
ENV_MAX_SHEETS = "MAX_IMPORT_SHEETS"
ENV_STORAGE_DIR = "IMPORT_STORAGE_DIR"

# Tamaño del bloque de lectura: el archivo se procesa por partes, nunca entero
# en memoria.
CHUNK_SIZE = 1024 * 1024  # 1 MiB

# Caracteres de control que no deben quedar en el nombre que se muestra.
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_MAX_DISPLAY_NAME_LENGTH = 255


# ---------------------------------------------------------------------------
# Errores tipados
# ---------------------------------------------------------------------------


class UploadError(Exception):
    """Problema del archivo subido que el usuario puede corregir.

    ``status_code`` es el código HTTP que corresponde al problema y
    ``user_message`` el texto que se le muestra (nunca la causa raíz).
    """

    status_code: int = 422

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


class InvalidFileTypeError(UploadError):
    """El archivo no es de un tipo soportado (o no tiene nombre)."""

    status_code = 400


class FileTooLargeError(UploadError):
    """El archivo supera el tamaño máximo permitido."""

    status_code = 413

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        super().__init__(
            "El archivo supera el tamaño máximo permitido "
            f"({format_size(max_bytes)}). Divide el archivo en varios lotes "
            "e inténtalo de nuevo."
        )


class TooManyRowsError(UploadError):
    """Una hoja tiene más filas de las permitidas."""

    status_code = 422

    def __init__(self, sheet: str | None, max_rows: int) -> None:
        self.sheet = sheet
        self.max_rows = max_rows
        where = f"La hoja '{sheet}'" if sheet else "El archivo"
        super().__init__(
            f"{where} tiene demasiadas filas (máximo {max_rows:,}). "
            "Divide el archivo en varios lotes e inténtalo de nuevo."
        )


class TooManySheetsError(UploadError):
    """El archivo tiene más hojas de las permitidas."""

    status_code = 422

    def __init__(self, sheet_count: int, max_sheets: int) -> None:
        self.sheet_count = sheet_count
        self.max_sheets = max_sheets
        super().__init__(
            f"El archivo tiene {sheet_count} hojas (máximo {max_sheets}). "
            "Elimina las hojas que no necesitas e inténtalo de nuevo."
        )


class UnreadableFileError(UploadError):
    """El archivo no se pudo leer con el formato que dice tener."""

    status_code = 422


class ImportValidationError(UploadError):
    """El archivo se leyó, pero su contenido no permite una importación."""

    status_code = 422


# ---------------------------------------------------------------------------
# Límites configurables
# ---------------------------------------------------------------------------


def _positive_int(env_name: str, default: int) -> int:
    """Lee un entero positivo del entorno; si no es válido usa el default."""
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "%s no es un número entero (%r); se usa el valor por defecto %s",
            env_name,
            raw,
            default,
        )
        return default
    if value <= 0:
        logger.warning(
            "%s debe ser mayor que cero (%r); se usa el valor por defecto %s",
            env_name,
            raw,
            default,
        )
        return default
    return value


def max_upload_bytes() -> int:
    """Tamaño máximo permitido por archivo, en bytes."""
    return _positive_int(ENV_MAX_UPLOAD_SIZE_MB, DEFAULT_MAX_UPLOAD_SIZE_MB) * (
        1024 * 1024
    )


def max_rows_per_sheet() -> int:
    """Máximo de filas de datos por hoja."""
    return _positive_int(ENV_MAX_ROWS_PER_SHEET, DEFAULT_MAX_ROWS_PER_SHEET)


def max_sheets() -> int:
    """Máximo de hojas por archivo."""
    return _positive_int(ENV_MAX_SHEETS, DEFAULT_MAX_SHEETS)


def format_size(num_bytes: int) -> str:
    """Formatea un tamaño en bytes para un mensaje legible."""
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):g} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:g} KB"
    return f"{num_bytes} B"


# ---------------------------------------------------------------------------
# Directorio de almacenamiento
# ---------------------------------------------------------------------------


def storage_dir() -> Path:
    """Directorio donde se guardan los archivos subidos.

    **No** es una ruta servida por la API: nada de lo que se guarde aquí es
    accesible por HTTP. Por defecto vive en ``<backend>/var/imports``, fuera
    del paquete de la aplicación y de cualquier ``StaticFiles`` montada.
    """
    raw = os.getenv(ENV_STORAGE_DIR, "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "var" / "imports"


def ensure_storage_dir() -> Path:
    """Devuelve el directorio de almacenamiento, creándolo si hace falta."""
    directory = storage_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# ---------------------------------------------------------------------------
# Nombres
# ---------------------------------------------------------------------------


def _sanitize_display_name(name: str) -> str:
    """Limpia el nombre que se muestra y guarda como metadata."""
    cleaned = _CONTROL_CHARS.sub("", name).strip()
    if len(cleaned) > _MAX_DISPLAY_NAME_LENGTH:
        cleaned = cleaned[:_MAX_DISPLAY_NAME_LENGTH]
    return cleaned or "archivo"


def validate_filename(original_filename: str | None) -> tuple[str, str]:
    """Valida el nombre que envía el cliente.

    Devuelve ``(nombre_para_mostrar, extensión)``. El nombre del cliente
    **nunca** se usa para construir una ruta en disco: solo se conserva
    (limpiado) como metadata. La extensión sí se valida, porque determina con
    qué lector se interpreta el archivo.
    """
    if not original_filename or not original_filename.strip():
        raise InvalidFileTypeError(
            "No se recibió ningún archivo. Sube un Excel (.xlsx, .xls) o un CSV."
        )

    # `ntpath.basename` quita el último componente de la ruta tanto con "/" como
    # con "\", así que "../../etc/passwd.xlsx" se reduce a "passwd.xlsx".
    base = ntpath.basename(original_filename.strip())
    if not base or base in (".", ".."):
        raise InvalidFileTypeError(
            "El nombre del archivo no es válido. Sube un Excel (.xlsx, .xls) o un CSV."
        )

    extension = os.path.splitext(base)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise InvalidFileTypeError(
            "Tipo de archivo no válido. Solo se aceptan Excel (.xlsx, .xls) y CSV."
        )

    return _sanitize_display_name(base), extension


def generate_stored_name(extension: str) -> str:
    """Nombre en disco generado por el servidor: ``uuid4`` + extensión."""
    return f"{uuid4().hex}{extension}"


def resolve_stored_path(stored_name: str | None) -> Path | None:
    """Resuelve un nombre guardado a una ruta dentro del directorio de storage.

    Devuelve ``None`` si el nombre no apunta dentro del directorio (por
    ejemplo, una fila antigua que todavía guarda la ruta relativa de
    ``uploads/``): esos archivos ya no se gestionan.
    """
    if not stored_name:
        return None
    directory = storage_dir().resolve()
    # `basename` neutraliza cualquier componente de ruta: el archivo solo
    # puede quedar dentro del directorio de storage.
    candidate = (directory / os.path.basename(stored_name)).resolve()
    if candidate.parent != directory:
        return None
    return candidate


# ---------------------------------------------------------------------------
# Lectura y escritura
# ---------------------------------------------------------------------------


def save_upload(source: BinaryIO, extension: str, max_bytes: int | None = None) -> Path:
    """Guarda el archivo con un nombre del servidor, leyendo por bloques.

    El archivo se copia al disco por partes, así que nunca se carga entero en
    memoria. Si al copiar se rebasa el límite, la copia se aborta y el
    archivo parcial se borra: el disco nunca queda con un archivo a medio
    escribir.
    """
    limit = max_upload_bytes() if max_bytes is None else max_bytes
    directory = ensure_storage_dir()
    target = directory / generate_stored_name(extension)

    written = 0
    try:
        with open(target, "wb") as buffer:
            while True:
                chunk = source.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit:
                    raise FileTooLargeError(limit)
                buffer.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    return target


def read_upload(source: BinaryIO, max_bytes: int | None = None) -> bytes:
    """Lee el archivo entero en memoria, cortando en cuanto rebasa el límite.

    Se usa en el preview (que no necesita tocar el disco): el archivo nunca
    llega a estar completo en memoria si es más grande de lo permitido.
    """
    limit = max_upload_bytes() if max_bytes is None else max_bytes

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = source.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise FileTooLargeError(limit)
        chunks.append(chunk)

    return b"".join(chunks)

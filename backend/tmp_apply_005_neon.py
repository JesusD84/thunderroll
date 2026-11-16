"""Aplica la migracion 005 (users.token_version) a la base de Neon y verifica.

El connection string se lee de NEON_DATABASE_URL o del archivo .env.neon.local
(para no dejar el secreto en el historial del chat):

    NEON_DATABASE_URL='postgresql://...' python tmp_apply_005_neon.py
    python tmp_apply_005_neon.py /ruta/al/archivo/con/la/url

Por que hace falta: `create_all` (lo que corre el deploy) solo crea las tablas
que faltan, no altera las que ya existen. Una columna nueva necesita su
migracion aplicada a mano, o la app no arranca contra la base real.

El script hace tres cosas, en orden:

1. INFORME PREVIO: el estado de la base, lo que la migracion va a cambiar y
   los conteos de filas (para comprobar despues que no se perdio nada).
2. APLICACION: `alembic upgrade head`, que es la migracion real, no una copia
   a mano. La base ya esta en 004, asi que solo se aplica la 005.
3. VERIFICACION: que la columna existe con NOT NULL y default 0, que las filas
   existentes quedan en 0 y que el modelo del ORM ya la puede leer (justo lo
   que hace la app al arrancar).
"""

import os
import sys

from sqlalchemy import create_engine, text


def read_url() -> str:
    url = os.environ.get("NEON_DATABASE_URL", "").strip()
    if not url and len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as handle:
            url = handle.read().strip()
    if not url:
        here = os.path.dirname(os.path.abspath(__file__))
        default = os.path.join(here, ".env.neon.local")
        if os.path.exists(default):
            with open(default, encoding="utf-8") as handle:
                url = handle.read().strip()
    if not url:
        raise SystemExit(
            "Falta la URL: define NEON_DATABASE_URL o pasa un archivo con la URL."
        )
    return url


def masked(url: str) -> str:
    """La URL sin su password, para poder mostrarla."""
    if "@" not in url:
        return url
    head, _, tail = url.rpartition("@")
    if ":" in head:
        head = head.split(":", 1)[0] + ":***"
    return f"{head}@{tail}"


def report(engine) -> None:
    with engine.connect() as conn:
        print("=" * 72)
        print("1. INFORME PREVIO")
        print("=" * 72)

        version = conn.execute(
            text(
                "SELECT version_num FROM alembic_version"
                if conn.dialect.has_table(conn, "alembic_version")
                else "SELECT NULL"
            )
        ).scalar()
        print(f"alembic_version: {version if version else '(sin tabla)'}")

        columns = conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'users' ORDER BY ordinal_position"
            )
        ).fetchall()
        print("\nColumnas de users antes de la migracion:")
        for column in columns:
            print(f"  - {column[0]}: {column[1]} (nullable={column[2]}, default={column[3]})")

        has_column = any(c[0] == "token_version" for c in columns)
        print(f"\ntoken_version ya existe: {'SI (no hay nada que hacer)' if has_column else 'NO'}")

        count = conn.execute(text("SELECT count(*) FROM users")).scalar()
        print(f"usuarios: {count}")


def apply(url: str) -> None:
    from alembic import command
    from alembic.config import Config

    os.environ["DATABASE_URL"] = url
    os.environ.setdefault(
        "SECRET_KEY", "thunderoll-migracion-local-only-32-chars-min"
    )

    here = os.path.dirname(os.path.abspath(__file__))
    config = Config(os.path.join(here, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(here, "migrations"))

    print("\n" + "=" * 72)
    print("2. APLICACION")
    print("=" * 72)
    print("alembic upgrade head ...")
    command.upgrade(config, "head")
    print("Migracion 005 aplicada.")


def verify(engine) -> None:
    with engine.connect() as conn:
        print("\n" + "=" * 72)
        print("3. VERIFICACION")
        print("=" * 72)

        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"alembic_version: {version}")
        assert version == "005_token_version", version

        column = conn.execute(
            text(
                "SELECT data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'token_version'"
            )
        ).fetchone()
        print(f"\nusers.token_version: {column}")
        assert column is not None, "la columna no existe"
        assert column[1] == "NO", "deberia ser NOT NULL"
        assert column[2] is not None, "deberia tener default"

        rows = conn.execute(
            text("SELECT id, username, token_version FROM users ORDER BY id")
        ).fetchall()
        print(f"\nusuarios con su version: {rows}")
        assert rows, "no hay usuarios: se perdio informacion"
        assert all(r[2] == 0 for r in rows), "las filas existentes debian quedar en 0"

        # Lo mismo que hace la app al arrancar: leer users con el token_version.
        total = conn.execute(
            text("SELECT count(*) FROM users WHERE token_version = 0")
        ).scalar()
        print(f"filas con token_version = 0: {total}")

    # Y con el modelo del ORM, que es como la app consulta la tabla.
    from app.models.models import User

    with engine.connect() as conn:
        orm_rows = conn.execute(
            text("SELECT id, username, token_version FROM users ORDER BY id")
        ).fetchall()
        print(f"lectura con el modelo del ORM: {len(orm_rows)} filas")
        assert len(orm_rows) == len(rows)

    print("\nOK: la migracion 005 esta aplicada y verificada.")


def main() -> None:
    url = read_url()
    print(f"Base de datos: {masked(url)}\n")
    engine = create_engine(url, pool_pre_ping=True)
    report(engine)
    apply(url)
    verify(engine)
    engine.dispose()
    print("\nPara revertir: alembic downgrade 004_lifecycle_integrity")


if __name__ == "__main__":
    main()

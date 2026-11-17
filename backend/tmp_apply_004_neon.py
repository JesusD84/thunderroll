"""Aplica la migracion 004 a la base de datos y verifica que quedó activa.

El connection string se lee de NEON_DATABASE_URL o de un archivo (para no
dejar el secreto en el historial del chat):

    NEON_DATABASE_URL='postgresql://...' python tmp_apply_004_neon.py
    python tmp_apply_004_neon.py /ruta/al/archivo/con/la/url

El script hace tres cosas, en orden:

1. INFORME PREVIO: el estado de la base, lo que la migracion va a cambiar y
   lo que no va a tocar (conteos de filas).
2. APLICACION: `alembic stamp 003_batch_meta` + `alembic upgrade head`, que
   es la migracion real, no una copia a mano.
3. VERIFICACION: que el indice parcial y el UNIQUE existen y que rechazan de
   verdad una segunda transferencia activa y un nombre de ubicacion repetido
   (las dos pruebas se hacen dentro de una transaccion que se revierte).
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

        for table in ("units", "transfers", "locations"):
            exists = conn.dialect.has_table(conn, table)
            count = (
                conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                if exists
                else None
            )
            print(f"{table}: {'presente' if exists else 'AUSENTE'}, filas: {count}")

        indexes = conn.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE tablename IN ('transfers', 'locations') "
                "AND indexname IN ('ix_transfers_unit_id', "
                "'ux_transfers_one_active_per_unit', 'ux_locations_name')"
            )
        ).fetchall()
        print("\nObjetos nuevos antes de la migracion:")
        if indexes:
            for name, definition in indexes:
                print(f"  - {name}: {definition}")
        else:
            print("  (ninguno: la migracion todavia no se aplico)")

        constraints = conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'locations'::regclass AND contype = 'u'"
            )
        ).fetchall()
        print(f"UNIQUE en locations: {[c[0] for c in constraints] or '(ninguno)'}")

        print("\nTransferencias activas duplicadas (la migracion cancela la mas vieja):")
        duplicates = conn.execute(
            text(
                """
                SELECT unit_id, count(*), array_agg(id ORDER BY id)
                FROM transfers
                WHERE status IN ('PENDING', 'IN_TRANSIT')
                GROUP BY unit_id
                HAVING count(*) > 1
                ORDER BY unit_id
                """
            )
        ).fetchall()
        if duplicates:
            for unit_id, count, ids in duplicates:
                print(f"  - unidad {unit_id}: {count} activas (ids {ids}) -> se cancela la mas vieja")
        else:
            print("  (ninguna)")

        print("\nNombres de ubicacion repetidos (la migracion renombra al mas nuevo):")
        dup_names = conn.execute(
            text(
                """
                SELECT name, count(*), array_agg(id ORDER BY id)
                FROM locations GROUP BY name HAVING count(*) > 1 ORDER BY name
                """
            )
        ).fetchall()
        if dup_names:
            for name, count, ids in dup_names:
                print(f"  - '{name}': {count} (ids {ids}) -> el mas nuevo pasa a '{name} ({ids[-1]})'")
        else:
            print("  (ninguno)")


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
    print("alembic stamp 003_batch_meta ...")
    command.stamp(config, "003_batch_meta")
    print("alembic upgrade head ...")
    command.upgrade(config, "head")
    print("Migracion 004 aplicada.")


def verify(engine) -> None:
    with engine.connect() as conn:
        print("\n" + "=" * 72)
        print("3. VERIFICACION")
        print("=" * 72)

        version = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
        print(f"alembic_version: {version}")

        partial = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'ux_transfers_one_active_per_unit'"
            )
        ).scalar()
        print(f"\nIndice parcial: {partial}")
        assert partial is not None, "el indice parcial no existe"
        assert "UNIQUE" in partial.upper(), "el indice no es unico"
        assert "WHERE" in partial.upper(), "el indice no es parcial"
        assert "'PENDING'" in partial and "'IN_TRANSIT'" in partial, (
            "el indice no filtra por las transferencias activas"
        )

        unit_index = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE indexname = 'ix_transfers_unit_id'"
            )
        ).scalar()
        print(f"Indice de transfers.unit_id: {unit_index}")
        assert unit_index is not None, "falta el indice de transfers.unit_id"

        unique = conn.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'locations'::regclass AND contype = 'u'"
            )
        ).fetchall()
        names = [row[0] for row in unique]
        print(f"UNIQUE en locations: {names}")
        assert "locations_name_key" in names, "falta el UNIQUE de locations.name"

        for table in ("units", "transfers", "locations"):
            count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            print(f"{table}: {count} filas")

        # Las dos pruebas funcionales. Cada una va en su propia transaccion y
        # se revierte: en Neon no se escribe nada.
        print("\nPruebas funcionales (cada una se revierte):")
        # Una unidad que YA tiene una transferencia activa: insertar otra
        # activa para la misma unidad es lo que el indice parcial prohibe.
        unit = conn.execute(
            text(
                "SELECT unit_id FROM transfers "
                "WHERE status IN ('PENDING', 'IN_TRANSIT') LIMIT 1"
            )
        ).scalar()
        location = conn.execute(
            text("SELECT id FROM locations ORDER BY id LIMIT 1")
        ).scalar()
        name = conn.execute(
            text("SELECT name FROM locations ORDER BY id LIMIT 1")
        ).scalar()

        if unit is None:
            print("  - ninguna unidad con transferencia activa: prueba omitida")
        else:
            try:
                conn.execute(
                    text(
                        "INSERT INTO transfers (unit_id, origin_location_id, "
                        "destination_location_id, status, dispatched_at) "
                        "VALUES (:u, :l, :l, 'IN_TRANSIT', now())"
                    ),
                    {"u": unit, "l": location},
                )
                conn.rollback()
                raise AssertionError(
                    "el indice parcial no impidio la segunda transferencia"
                )
            except AssertionError:
                raise
            except Exception as exc:  # noqa: BLE001
                conn.rollback()
                culprit = getattr(
                    getattr(getattr(exc, "orig", None), "diag", None),
                    "constraint_name",
                    None,
                )
                print(
                    f"  - segunda transferencia activa rechazada: "
                    f"{type(exc).__name__} ({culprit})"
                )
                assert culprit == "ux_transfers_one_active_per_unit", (
                    f"el rechazo no vino del indice parcial: {culprit}"
                )

        try:
            if name is None:
                print("  - sin ubicaciones: no se prueba el nombre repetido")
            else:
                conn.execute(
                    text(
                        "INSERT INTO locations (name, created_at) VALUES (:n, now())"
                    ),
                    {"n": name},
                )
                conn.rollback()
                raise AssertionError(
                    "el UNIQUE de locations.name no impidio el duplicado"
                )
        except AssertionError:
            raise
        except Exception as exc:  # noqa: BLE001
            conn.rollback()
            culprit = getattr(
                getattr(getattr(exc, "orig", None), "diag", None),
                "constraint_name",
                None,
            )
            print(
                f"  - nombre de ubicacion repetido rechazado: "
                f"{type(exc).__name__} ({culprit})"
            )
            assert culprit == "locations_name_key", (
                f"el rechazo no vino del UNIQUE de locations.name: {culprit}"
            )

        # Comprobacion final: el historial sigue completo.
        counts = {
            table: conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            for table in ("units", "transfers", "locations")
        }
        print(f"  - historial intacto: {counts}")

    print("\nOK: la migracion 004 esta aplicada y verificada.")


def main() -> None:
    url = read_url()
    print(f"Base de datos: {masked(url)}\n")
    engine = create_engine(url, pool_pre_ping=True)
    report(engine)
    apply(url)
    verify(engine)
    engine.dispose()
    print("\nPara revertir: alembic downgrade 003_batch_meta")


if __name__ == "__main__":
    main()

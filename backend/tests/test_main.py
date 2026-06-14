"""Regression tests for app startup wiring (TR-11).

Importing ``app.main`` must not open a database connection. Schema creation
(``create_all``) and demo seeding run in the FastAPI ``lifespan`` (startup),
not at module import time, so importing the app does not require a reachable
``DATABASE_URL`` or any SMTP envs.
"""

import subprocess
import sys
import textwrap


def test_importing_app_main_does_not_connect_to_db():
    """Importing app.main with an unreachable DB and no SMTP envs must succeed.

    Runs in a fresh subprocess so module-level import side effects are exercised
    from scratch. ``DATABASE_URL`` points at an unroutable host; if ``create_all``
    (or anything else) ran at import time it would try to connect and fail. The
    short timeout also guards against an import-time connection hang.
    """
    script = textwrap.dedent(
        """
        import app.main  # noqa: F401
        print("IMPORT_OK")
        """
    )

    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        # Unroutable address: any real connection attempt fails fast / hangs.
        "DATABASE_URL": "postgresql://u:p@192.0.2.1:5432/nope",
    }
    # No SMTP_* and no FRONTEND_URL on purpose.

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, (
        f"Importing app.main failed.\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "IMPORT_OK" in result.stdout


def test_create_all_not_called_at_module_import():
    """``create_all`` must live in the lifespan, not at module top-level (TR-11)."""
    import inspect
    import app.main as main

    source = inspect.getsource(main)
    create_all_line = next(
        line for line in source.splitlines() if "create_all(" in line
    )
    # The call must be indented (inside the lifespan function), never top-level.
    assert create_all_line.startswith(" "), (
        "create_all must run inside lifespan, not at module import time"
    )

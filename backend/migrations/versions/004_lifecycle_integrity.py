"""Lifecycle integrity: one active transfer per unit, unique location names

What this migration does:

1. indexes ``transfers.unit_id``: the history of a unit is always read by
   unit_id;
2. cancels the older active transfer of every unit that has more than one,
   so the unique index below can be created on the data that already exists;
3. creates a *partial* unique index on ``transfers.unit_id`` for the active
   statuses (PENDING, IN_TRANSIT): a unit can have at most one transfer
   that still holds it;
4. renames the duplicated locations and makes ``locations.name`` unique:
   the name is how a location is identified everywhere in the system.

The partial index is PostgreSQL only (SQLite has no partial indexes); the
rule it enforces is also checked by the services, so it holds on both.

Revision ID: 004_lifecycle_integrity
Revises: 003_batch_meta
Create Date: 2026-11-16 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004_lifecycle_integrity"
down_revision = "003_batch_meta"
branch_labels = None
depends_on = None


# Keep the newest active transfer of every unit and cancel the older ones.
# A cancelled transfer is a closed trip: it does not hold the unit, so the
# unique index can be created without losing any history.
_CANCEL_OLDER_ACTIVE_TRANSFERS = """
WITH ranked AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY unit_id
               ORDER BY dispatched_at DESC NULLS LAST, id DESC
           ) AS position
    FROM transfers
    WHERE status IN ('PENDING', 'IN_TRANSIT')
)
UPDATE transfers
SET status = 'CANCELLED'
WHERE id IN (SELECT id FROM ranked WHERE position > 1)
"""

# Renames the duplicated locations, keeping the oldest of each name. The
# suffix carries the id of the row, so the new name cannot collide with the
# name of another location.
_RENAME_DUPLICATED_LOCATIONS = """
WITH ranked AS (
    SELECT id, name,
           ROW_NUMBER() OVER (PARTITION BY name ORDER BY id) AS position
    FROM locations
)
UPDATE locations
SET name = name || ' (' || id || ')'
WHERE id IN (SELECT id FROM ranked WHERE position > 1)
"""

# The same, but looking for a free name before writing it: PostgreSQL only.
_RENAME_DUPLICATED_LOCATIONS_PG = """
DO $$
DECLARE
    duplicated RECORD;
    candidate TEXT;
    suffix INTEGER := 2;
BEGIN
    FOR duplicated IN
        SELECT l.id, l.name
        FROM locations l
        JOIN (
            SELECT name, MIN(id) AS keep_id FROM locations GROUP BY name
        ) grouped ON grouped.name = l.name AND grouped.keep_id <> l.id
        ORDER BY l.id
    LOOP
        candidate := duplicated.name || ' (' || duplicated.id || ')';
        WHILE EXISTS (SELECT 1 FROM locations WHERE name = candidate) LOOP
            candidate := duplicated.name || ' (' || duplicated.id || '-' || suffix || ')';
            suffix := suffix + 1;
        END LOOP;
        UPDATE locations SET name = candidate WHERE id = duplicated.id;
    END LOOP;
END
$$
"""

_ONE_ACTIVE_TRANSFER_PER_UNIT = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_transfers_one_active_per_unit
ON transfers (unit_id)
WHERE status IN ('PENDING', 'IN_TRANSIT')
"""

_ADD_UNIQUE_LOCATION_NAME = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'locations_name_key'
    ) THEN
        ALTER TABLE locations ADD CONSTRAINT locations_name_key UNIQUE (name);
    END IF;
END
$$
"""


def upgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"

    # 1. The history of a unit is read by unit_id all the time.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_transfers_unit_id ON transfers (unit_id)"
    )

    # 2. Leave at most one active transfer per unit.
    op.execute(sa.text(_CANCEL_OLDER_ACTIVE_TRANSFERS))

    # 3. And make it impossible to create a second one.
    if is_postgres:
        op.execute(sa.text(_ONE_ACTIVE_TRANSFER_PER_UNIT))

    # 4. A location is identified by its name.
    if is_postgres:
        op.execute(sa.text(_RENAME_DUPLICATED_LOCATIONS_PG))
        op.execute(sa.text(_ADD_UNIQUE_LOCATION_NAME))
    else:
        op.execute(sa.text(_RENAME_DUPLICATED_LOCATIONS))
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_locations_name "
            "ON locations (name)"
        )


def downgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS ux_transfers_one_active_per_unit")
        op.execute("ALTER TABLE locations DROP CONSTRAINT IF EXISTS locations_name_key")
    else:
        op.execute("DROP INDEX IF EXISTS ux_locations_name")

    op.execute("DROP INDEX IF EXISTS ix_transfers_unit_id")

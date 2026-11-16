"""Add ``users.token_version``: revocation of the sessions already issued

Why this column exists:

Every access token carries the ``token_version`` of the account that minted
it. When the credentials of an account change (password, role, deactivation)
the counter is bumped, and any token minted before the bump stops matching
the stored value: the API rejects it with a 401.

That is how sessions are closed without a session store: there is nothing to
delete, the tokens simply stop being valid. The column starts at 0 for the
accounts that already exist, so their current sessions keep working.

Revision ID: 005_token_version
Revises: 004_lifecycle_integrity
Create Date: 2026-11-16 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "005_token_version"
down_revision = "004_lifecycle_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOT NULL with a default of 0: the existing rows get 0, so the sessions
    # that are already open stay valid.
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")

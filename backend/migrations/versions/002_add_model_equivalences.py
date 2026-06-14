"""Add model_equivalences table (TR-05)

Revision ID: 002_model_equiv
Revises: 1488dad4409f
Create Date: 2026-06-14 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_model_equiv'
down_revision = '1488dad4409f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'model_equivalences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('manufacturer_model', sa.String(length=150), nullable=False),
        sa.Column('internal_model', sa.String(length=150), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_model_equivalences_id', 'model_equivalences', ['id'], unique=False)
    op.create_index(
        'ix_model_equivalences_manufacturer_model',
        'model_equivalences',
        ['manufacturer_model'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_model_equivalences_manufacturer_model', table_name='model_equivalences')
    op.drop_index('ix_model_equivalences_id', table_name='model_equivalences')
    op.drop_table('model_equivalences')

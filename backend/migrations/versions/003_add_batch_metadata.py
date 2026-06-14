"""Add batch_period/product_type metadata to imports and units (TR-06)

Revision ID: 003_batch_meta
Revises: 002_model_equiv
Create Date: 2026-06-14 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_batch_meta'
down_revision = '002_model_equiv'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('imports', sa.Column('batch_period', sa.String(length=100), nullable=True))
    op.add_column('imports', sa.Column('product_type', sa.String(length=100), nullable=True))

    op.add_column('units', sa.Column('batch_period', sa.String(length=100), nullable=True))
    op.add_column('units', sa.Column('product_type', sa.String(length=100), nullable=True))
    op.create_index('ix_units_batch_period', 'units', ['batch_period'], unique=False)
    op.create_index('ix_units_product_type', 'units', ['product_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_units_product_type', table_name='units')
    op.drop_index('ix_units_batch_period', table_name='units')
    op.drop_column('units', 'product_type')
    op.drop_column('units', 'batch_period')

    op.drop_column('imports', 'product_type')
    op.drop_column('imports', 'batch_period')

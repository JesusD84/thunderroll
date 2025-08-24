
"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2025-08-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create locations table
    op.create_table('locations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('type', sa.Enum('BODEGA', 'TALLER', 'SUCURSAL', name='locationtype'), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_locations_id'), 'locations', ['id'], unique=False)
    op.create_index(op.f('ix_locations_name'), 'locations', ['name'], unique=False)

    # Create users table
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('ADMIN', 'INVENTARIO', 'TALLER', 'VENTAS', name='userrole'), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create shipments table
    op.create_table('shipments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('batch_code', sa.String(length=50), nullable=False),
    sa.Column('supplier_invoice', sa.String(length=100), nullable=False),
    sa.Column('imported_by_id', sa.Integer(), nullable=False),
    sa.Column('imported_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['imported_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('batch_code')
    )
    op.create_index(op.f('ix_shipments_batch_code'), 'shipments', ['batch_code'], unique=False)
    op.create_index(op.f('ix_shipments_id'), 'shipments', ['id'], unique=False)

    # Create units table
    op.create_table('units',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('brand', sa.String(length=50), nullable=False),
    sa.Column('model', sa.String(length=50), nullable=False),
    sa.Column('color', sa.String(length=30), nullable=False),
    sa.Column('engine_number', sa.BigInteger(), nullable=True),
    sa.Column('chassis_number', sa.String(length=20), nullable=True),
    sa.Column('supplier_invoice', sa.String(length=100), nullable=False),
    sa.Column('shipment_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('EN_BODEGA_NO_IDENTIFICADA', 'IDENTIFICADA_EN_TALLER', 'EN_TRANSITO_TALLER_SUCURSAL', 'EN_TRANSITO_SUCURSAL_SUCURSAL', 'EN_SUCURSAL_DISPONIBLE', 'RESERVADA', 'VENDIDA', name='unitstatus'), nullable=False),
    sa.Column('location_id', sa.Integer(), nullable=False),
    sa.Column('assigned_branch_id', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('last_updated_by_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['assigned_branch_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['last_updated_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['shipment_id'], ['shipments.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('chassis_number'),
    sa.UniqueConstraint('engine_number')
    )
    op.create_index(op.f('ix_units_chassis_number'), 'units', ['chassis_number'], unique=False)
    op.create_index(op.f('ix_units_engine_number'), 'units', ['engine_number'], unique=False)
    op.create_index(op.f('ix_units_id'), 'units', ['id'], unique=False)

    # Create unit_events table
    op.create_table('unit_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('event_type', sa.Enum('CREATED', 'IMPORTED', 'IDENTIFIED', 'TRANSFER_INITIATED', 'TRANSFER_RECEIVED', 'STATUS_CHANGED', 'SOLD', 'ADJUSTED', 'NOTE_ADDED', name='eventtype'), nullable=False),
    sa.Column('before', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('after', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unit_events_id'), 'unit_events', ['id'], unique=False)
    op.create_index(op.f('ix_unit_events_timestamp'), 'unit_events', ['timestamp'], unique=False)

    # Create transfers table
    op.create_table('transfers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('from_location_id', sa.Integer(), nullable=False),
    sa.Column('to_location_id', sa.Integer(), nullable=False),
    sa.Column('eta', sa.DateTime(), nullable=True),
    sa.Column('created_by_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('received_by_id', sa.Integer(), nullable=True),
    sa.Column('received_at', sa.DateTime(), nullable=True),
    sa.Column('status', sa.Enum('PENDING', 'IN_TRANSIT', 'RECEIVED', 'CANCELLED', name='transferstatus'), nullable=False),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['from_location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['received_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['to_location_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transfers_id'), 'transfers', ['id'], unique=False)

    # Create sales table
    op.create_table('sales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('unit_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('receipt', sa.String(length=100), nullable=False),
    sa.Column('sold_by_id', sa.Integer(), nullable=False),
    sa.Column('branch_id', sa.Integer(), nullable=False),
    sa.Column('sold_at', sa.DateTime(), nullable=False),
    sa.Column('customer_name', sa.String(length=200), nullable=True),
    sa.ForeignKeyConstraint(['branch_id'], ['locations.id'], ),
    sa.ForeignKeyConstraint(['sold_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['unit_id'], ['units.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('receipt'),
    sa.UniqueConstraint('unit_id')
    )
    op.create_index(op.f('ix_sales_id'), 'sales', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sales_id'), table_name='sales')
    op.drop_table('sales')
    op.drop_index(op.f('ix_transfers_id'), table_name='transfers')
    op.drop_table('transfers')
    op.drop_index(op.f('ix_unit_events_timestamp'), table_name='unit_events')
    op.drop_index(op.f('ix_unit_events_id'), table_name='unit_events')
    op.drop_table('unit_events')
    op.drop_index(op.f('ix_units_id'), table_name='units')
    op.drop_index(op.f('ix_units_engine_number'), table_name='units')
    op.drop_index(op.f('ix_units_chassis_number'), table_name='units')
    op.drop_table('units')
    op.drop_index(op.f('ix_shipments_id'), table_name='shipments')
    op.drop_index(op.f('ix_shipments_batch_code'), table_name='shipments')
    op.drop_table('shipments')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_locations_name'), table_name='locations')
    op.drop_index(op.f('ix_locations_id'), table_name='locations')
    op.drop_table('locations')

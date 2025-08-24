
"""Database seeding script."""

import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session
from app.models.location import Location, LocationType
from app.models.user import User, UserRole
from app.models.shipment import Shipment
from app.models.unit import Unit, UnitStatus
from app.models.unit_event import UnitEvent, EventType
from app.core.security import get_password_hash


async def seed_locations(db: AsyncSession):
    """Seed locations."""
    locations_data = [
        {"name": "Bodega Principal", "type": LocationType.BODEGA},
        {"name": "Taller Central", "type": LocationType.TALLER},
        {"name": "Sucursal Centro", "type": LocationType.SUCURSAL},
        {"name": "Sucursal Norte", "type": LocationType.SUCURSAL},
        {"name": "Sucursal Sur", "type": LocationType.SUCURSAL},
    ]
    
    for location_data in locations_data:
        # Check if location already exists
        result = await db.execute(
            select(Location).where(Location.name == location_data["name"])
        )
        if result.scalar_one_or_none():
            continue
        
        location = Location(**location_data)
        db.add(location)
    
    await db.commit()
    print("✓ Locations seeded")


async def seed_users(db: AsyncSession):
    """Seed demo users."""
    users_data = [
        {
            "name": "Administrador",
            "email": "admin@thunderrol.com",
            "password": "admin123",
            "role": UserRole.ADMIN,
        },
        {
            "name": "Usuario Inventario",
            "email": "inventario@thunderrol.com", 
            "password": "inv123",
            "role": UserRole.INVENTARIO,
        },
        {
            "name": "Usuario Taller",
            "email": "taller@thunderrol.com",
            "password": "taller123", 
            "role": UserRole.TALLER,
        },
        {
            "name": "Usuario Ventas",
            "email": "ventas@thunderrol.com",
            "password": "ventas123",
            "role": UserRole.VENTAS,
        },
    ]
    
    for user_data in users_data:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == user_data["email"])
        )
        if result.scalar_one_or_none():
            continue
        
        user = User(
            name=user_data["name"],
            email=user_data["email"],
            password_hash=get_password_hash(user_data["password"]),
            role=user_data["role"]
        )
        db.add(user)
    
    await db.commit()
    print("✓ Users seeded")


async def seed_sample_data(db: AsyncSession):
    """Seed sample shipment and units."""
    
    # Get admin user
    admin_result = await db.execute(
        select(User).where(User.role == UserRole.ADMIN)
    )
    admin_user = admin_result.scalar_one_or_none()
    
    if not admin_user:
        print("! Admin user not found, skipping sample data")
        return
    
    # Get bodega location
    bodega_result = await db.execute(
        select(Location).where(Location.type == LocationType.BODEGA)
    )
    bodega = bodega_result.scalar_one_or_none()
    
    if not bodega:
        print("! Bodega location not found, skipping sample data")
        return
    
    # Check if sample shipment already exists
    shipment_result = await db.execute(
        select(Shipment).where(Shipment.batch_code == "DEMO-2025-001")
    )
    if shipment_result.scalar_one_or_none():
        print("✓ Sample data already exists")
        return
    
    # Create sample shipment
    shipment = Shipment(
        batch_code="DEMO-2025-001",
        supplier_invoice="INV-2025-001",
        imported_by_id=admin_user.id
    )
    db.add(shipment)
    await db.flush()  # Get shipment ID
    
    # Load sample data from JSON (use first 10 records)
    try:
        with open('/home/ubuntu/datos_ejemplo_inventario.json', 'r') as f:
            data = json.load(f)
            sample_units = data['datos'][:10]  # First 10 units
    except FileNotFoundError:
        # Fallback sample data if JSON file not found
        sample_units = [
            {
                "frame_number": "HXY202507498",
                "motor_number": 20250823035834,
                "color": "red",
                "marca": "Thunderrol",
                "modelo": "TR-2025",
            },
            {
                "frame_number": "HXY202507511", 
                "motor_number": 20250823035844,
                "color": "red",
                "marca": "Thunderrol",
                "modelo": "TR-2025",
            },
            {
                "frame_number": "HXY202507521",
                "motor_number": 20250823035830,
                "color": "black",
                "marca": "Thunderrol", 
                "modelo": "TR-2025",
            },
        ]
    
    # Create sample units
    created_units = []
    for i, unit_data in enumerate(sample_units):
        unit = Unit(
            brand=unit_data.get('marca', 'Thunderrol'),
            model=unit_data.get('modelo', 'TR-2025'),
            color=unit_data['color'],
            chassis_number=unit_data['frame_number'],
            engine_number=unit_data['motor_number'],
            supplier_invoice="INV-2025-001",
            shipment_id=shipment.id,
            location_id=bodega.id,
            status=UnitStatus.EN_BODEGA_NO_IDENTIFICADA if i < 5 else UnitStatus.IDENTIFICADA_EN_TALLER,  # Mix of statuses
            last_updated_by_id=admin_user.id
        )
        db.add(unit)
        created_units.append(unit)
    
    await db.flush()  # Get unit IDs
    
    # Create audit events for units
    for unit in created_units:
        event = UnitEvent(
            unit_id=unit.id,
            event_type=EventType.IMPORTED,
            after={
                "brand": unit.brand,
                "model": unit.model,
                "color": unit.color,
                "chassis_number": unit.chassis_number,
                "engine_number": unit.engine_number,
                "status": unit.status.value,
                "location_id": unit.location_id
            },
            user_id=admin_user.id,
            reason="Demo data seeding"
        )
        db.add(event)
    
    await db.commit()
    print(f"✓ Sample data seeded: 1 shipment, {len(created_units)} units")


async def main():
    """Main seeding function."""
    print("🌱 Seeding database...")
    
    async with async_session() as db:
        try:
            await seed_locations(db)
            await seed_users(db)
            await seed_sample_data(db)
            print("✅ Database seeding completed successfully!")
        except Exception as e:
            print(f"❌ Error seeding database: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())

from app.database.database import SessionLocal
from app.models.models import (
    User, UserRole, Location,
    Unit, UnitStatus, Transfer, TransferType
)
from app.services.auth_service import get_password_hash
from datetime import datetime, timedelta
import asyncio

def create_demo_data():
    """Create demo data for the application"""
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(User).first():
            print("Demo data already exists")
            return
        
        print("Creating demo data...")
        
        # Create users
        users = [
            User(
                email="admin@thunderrol.com",
                username="admin",
                first_name="Admin",
                last_name="Usuario",
                role=UserRole.ADMIN,
                hashed_password=get_password_hash("admin123")
            ),
            User(
                email="manager@thunderrol.com",
                username="manager",
                first_name="Manager",
                last_name="Usuario",
                role=UserRole.MANAGER,
                hashed_password=get_password_hash("manager123")
            ),
            User(
                email="operator@thunderrol.com",
                username="operator",
                first_name="Operator",
                last_name="Usuario",
                role=UserRole.OPERATOR,
                hashed_password=get_password_hash("operator123")
            ),
            User(
                email="viewer@thunderrol.com",
                username="viewer",
                first_name="Viewer",
                last_name="Usuario",
                role=UserRole.VIEWER,
                hashed_password=get_password_hash("viewer123")
            )
        ]
        
        for user in users:
            db.add(user)
        db.commit()
        print("✓ Users created")
        
        # Create locations
        locations = [
            Location(
                name="Almacén Principal",
                address="Av. Revolucion 1234",
            ),
            Location(
                name="Sucursal Centro",
                address="Calle Juárez 567",
            ),
            Location(
                name="Sucursal Plaza del Sol",
                address="Av. López Mateos 890",
            ),
            Location(
                name="Taller de Servicio",
                address="Calle Industria 123",
            )
        ]
        
        for location in locations:
            db.add(location)
        db.commit()
        print("✓ Locations created")

        # Create demo units
        admin_user = db.query(User).filter(User.username == "admin").first()
        warehouse = db.query(Location).filter(Location.name == "Almacén Principal").first()
        
        # Get some models, brands and colors for demo units
        ybr125 = "YBR 125"
        cb125f = "CB 125F"
        xtz125 = "XTZ 125"

        yamaha = "Yamaha"
        suzuki = "Suzuki"
        kawasaki = "Kawasaki"
        
        negro = "Negro"
        rojo = "Rojo"
        azul = "Azul"
        blanco = "Blanco"
        
        demo_units = [
            Unit(
                engine_number="YBR125001",
                chassis_number="YBR125CH001",
                model=ybr125,
                brand=yamaha,
                color=negro,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            ),
            Unit(
                engine_number="YBR125002",
                chassis_number="YBR125CH002",
                model=ybr125,
                brand=kawasaki,
                color=rojo,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            ),
            Unit(
                engine_number="CB125F001",
                chassis_number="CB125FCH001",
                model=cb125f,
                brand=kawasaki,
                color=azul,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            ),
            Unit(
                engine_number="CB125F002",
                chassis_number="CB125FCH002",
                brand=suzuki,
                model=cb125f,
                color=blanco,
                current_location_id=warehouse.id,
                status=UnitStatus.SOLD,
                sold_date=datetime.now() - timedelta(days=5)
            ),
            Unit(
                engine_number="XTZ125001",
                chassis_number="XTZ125CH001",
                model=xtz125,
                brand=suzuki,
                color=negro,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            )
        ]
        
        for unit in demo_units:
            db.add(unit)
        db.commit()
        print("✓ Demo units created")
        
        # Create demo transfers for the units
        for unit in demo_units:
            # Import transfer
            import_transfer = Transfer(
                unit_id=unit.id,
                user_id=admin_user.id,
                transfer_type=TransferType.IMPORT,
                to_location_id=warehouse.id,
                notes="Unidad importada - datos de demostración"
            )
            db.add(import_transfer)
            
            # Sale transfer for sold unit
            if unit.status == UnitStatus.SOLD:
                sale_transfer = Transfer(
                    unit_id=unit.id,
                    user_id=admin_user.id,
                    transfer_type=TransferType.SALE,
                    transfer_date=unit.sold_date,
                to_location_id=warehouse.id,
                    notes="Venta de unidad - datos de demostración"
                )
                db.add(sale_transfer)
        
        db.commit()
        print("✓ Demo transfers created")
        
        print("✅ Demo data creation completed successfully!")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {str(e)}", file=sys.stderr, flush=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_demo_data())

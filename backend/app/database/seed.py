
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.models import (
    User, UserRole, Color, Location, Setting,
    Unit, UnitStatus, Movement, MovementType
)
from app.services.auth import get_password_hash
from datetime import datetime, timedelta
import asyncio

async def create_demo_data():
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
        
        # Create colors
        colors = [
            Color(name="Negro", hex_code="#000000"),
            Color(name="Blanco", hex_code="#FFFFFF"),
            Color(name="Rojo", hex_code="#FF0000"),
            Color(name="Azul", hex_code="#0066CC"),
            Color(name="Verde", hex_code="#00AA00"),
            Color(name="Amarillo", hex_code="#FFFF00"),
            Color(name="Naranja", hex_code="#FF6600"),
            Color(name="Gris", hex_code="#808080"),
            Color(name="Plateado", hex_code="#C0C0C0"),
            Color(name="Dorado", hex_code="#FFD700")
        ]
        
        for color in colors:
            db.add(color)
        db.commit()
        print("✓ Colors created")
        
        # Create locations
        locations = [
            Location(
                name="Almacén Principal",
                address="Av. Revolucion 1234",
                city="Guadalajara",
                state="Jalisco",
                zip_code="44100",
                country="México",
                phone="33-1234-5678",
                email="almacen@thunderrol.com",
                manager_name="Juan Pérez"
            ),
            Location(
                name="Sucursal Centro",
                address="Calle Juárez 567",
                city="Guadalajara",
                state="Jalisco",
                zip_code="44100",
                country="México",
                phone="33-2345-6789",
                email="centro@thunderrol.com",
                manager_name="María García"
            ),
            Location(
                name="Sucursal Plaza del Sol",
                address="Av. López Mateos 890",
                city="Guadalajara",
                state="Jalisco",
                zip_code="44110",
                country="México",
                phone="33-3456-7890",
                email="plaza@thunderrol.com",
                manager_name="Carlos Rodríguez"
            ),
            Location(
                name="Taller de Servicio",
                address="Calle Industria 123",
                city="Guadalajara",
                state="Jalisco",
                zip_code="44120",
                country="México",
                phone="33-4567-8901",
                email="taller@thunderrol.com",
                manager_name="Luis Martínez"
            )
        ]
        
        for location in locations:
            db.add(location)
        db.commit()
        print("✓ Locations created")
        
        # Create settings
        settings = [
            Setting(
                key="company_name",
                value="Thunderrol S.A. de C.V.",
                description="Nombre de la empresa",
                category="general",
                data_type="string"
            ),
            Setting(
                key="company_address",
                value="Guadalajara, Jalisco, México",
                description="Dirección de la empresa",
                category="general",
                data_type="string"
            ),
            Setting(
                key="company_phone",
                value="33-1234-5678",
                description="Teléfono de la empresa",
                category="general",
                data_type="string"
            ),
            Setting(
                key="company_email",
                value="info@thunderrol.com",
                description="Email de la empresa",
                category="general",
                data_type="string"
            ),
            Setting(
                key="default_currency",
                value="MXN",
                description="Moneda por defecto",
                category="financial",
                data_type="string"
            ),
            Setting(
                key="tax_rate",
                value="16",
                description="Tasa de IVA (%)",
                category="financial",
                data_type="integer"
            ),
            Setting(
                key="timezone",
                value="America/Mexico_City",
                description="Zona horaria",
                category="general",
                data_type="string"
            ),
            Setting(
                key="auto_backup",
                value="true",
                description="Respaldo automático habilitado",
                category="system",
                data_type="boolean"
            )
        ]
        
        for setting in settings:
            db.add(setting)
        db.commit()
        print("✓ Settings created")

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
        
        negro = db.query(Color).filter(Color.name == "Negro").first()
        rojo = db.query(Color).filter(Color.name == "Rojo").first()
        azul = db.query(Color).filter(Color.name == "Azul").first()
        blanco = db.query(Color).filter(Color.name == "Blanco").first()
        
        demo_units = [
            Unit(
                engine_number="YBR125001",
                chassis_number="YBR125CH001",
                model=ybr125,
                brand=yamaha,
                color_id=negro.id,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            ),
            Unit(
                engine_number="YBR125002",
                chassis_number="YBR125CH002",
                model=ybr125,
                brand=kawasaki,
                color_id=rojo.id,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            ),
            Unit(
                engine_number="CB125F001",
                chassis_number="CB125FCH001",
                model=cb125f,
                brand=kawasaki,
                color_id=azul.id,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            ),
            Unit(
                engine_number="CB125F002",
                chassis_number="CB125FCH002",
                brand=suzuki,
                model=cb125f,
                color_id=blanco.id,
                current_location_id=warehouse.id,
                status=UnitStatus.SOLD,
                sold_date=datetime.now() - timedelta(days=5)
            ),
            Unit(
                engine_number="XTZ125001",
                chassis_number="XTZ125CH001",
                model=xtz125,
                brand=suzuki,
                color_id=negro.id,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE
            )
        ]
        
        for unit in demo_units:
            db.add(unit)
        db.commit()
        print("✓ Demo units created")
        
        # Create demo movements for the units
        for unit in demo_units:
            # Import movement
            import_movement = Movement(
                unit_id=unit.id,
                user_id=admin_user.id,
                movement_type=MovementType.IMPORT,
                to_location_id=warehouse.id,
                notes="Unidad importada - datos de demostración"
            )
            db.add(import_movement)
            
            # Sale movement for sold unit
            if unit.status == UnitStatus.SOLD:
                sale_movement = Movement(
                    unit_id=unit.id,
                    user_id=admin_user.id,
                    movement_type=MovementType.SALE,
                    movement_date=unit.sold_date,
                    notes="Venta de unidad - datos de demostración"
                )
                db.add(sale_movement)
        
        db.commit()
        print("✓ Demo movements created")
        
        print("✅ Demo data creation completed successfully!")
        
    except Exception as e:
        print(f"❌ Error creating demo data: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_demo_data())

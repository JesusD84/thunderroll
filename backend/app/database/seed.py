
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.models import (
    User, UserRole, Brand, Model, Color, Location, 
    Setting, Unit, UnitStatus, Movement, MovementType
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
        
        # Create brands
        brands = [
            Brand(name="YAMAHA"),
            Brand(name="HONDA"),
            Brand(name="SUZUKI"),
            Brand(name="KAWASAKI"),
            Brand(name="BAJAJ"),
            Brand(name="TVS"),
            Brand(name="HERO"),
            Brand(name="KTM")
        ]
        
        for brand in brands:
            db.add(brand)
        db.commit()
        print("✓ Brands created")
        
        # Create models
        yamaha_brand = db.query(Brand).filter(Brand.name == "YAMAHA").first()
        honda_brand = db.query(Brand).filter(Brand.name == "HONDA").first()
        suzuki_brand = db.query(Brand).filter(Brand.name == "SUZUKI").first()
        bajaj_brand = db.query(Brand).filter(Brand.name == "BAJAJ").first()
        
        models = [
            # Yamaha models
            Model(name="YBR 125", brand_id=yamaha_brand.id, year=2024, engine_type="4T", displacement="125cc"),
            Model(name="XTZ 125", brand_id=yamaha_brand.id, year=2024, engine_type="4T", displacement="125cc"),
            Model(name="FZ16", brand_id=yamaha_brand.id, year=2024, engine_type="4T", displacement="150cc"),
            Model(name="MT-03", brand_id=yamaha_brand.id, year=2024, engine_type="4T", displacement="321cc"),
            
            # Honda models
            Model(name="CB 125F", brand_id=honda_brand.id, year=2024, engine_type="4T", displacement="125cc"),
            Model(name="XR 150L", brand_id=honda_brand.id, year=2024, engine_type="4T", displacement="150cc"),
            Model(name="CB 190R", brand_id=honda_brand.id, year=2024, engine_type="4T", displacement="184cc"),
            Model(name="CBR 250R", brand_id=honda_brand.id, year=2024, engine_type="4T", displacement="250cc"),
            
            # Suzuki models
            Model(name="GN 125", brand_id=suzuki_brand.id, year=2024, engine_type="4T", displacement="125cc"),
            Model(name="GSX 150", brand_id=suzuki_brand.id, year=2024, engine_type="4T", displacement="150cc"),
            Model(name="GIXXER 250", brand_id=suzuki_brand.id, year=2024, engine_type="4T", displacement="250cc"),
            
            # Bajaj models
            Model(name="BOXER 150", brand_id=bajaj_brand.id, year=2024, engine_type="4T", displacement="150cc"),
            Model(name="PULSAR 180", brand_id=bajaj_brand.id, year=2024, engine_type="4T", displacement="180cc"),
            Model(name="DOMINAR 400", brand_id=bajaj_brand.id, year=2024, engine_type="4T", displacement="373cc")
        ]
        
        for model in models:
            db.add(model)
        db.commit()
        print("✓ Models created")
        
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
        
        # Get some models and colors for demo units
        ybr125 = db.query(Model).filter(Model.name == "YBR 125").first()
        cb125f = db.query(Model).filter(Model.name == "CB 125F").first()
        xtz125 = db.query(Model).filter(Model.name == "XTZ 125").first()
        
        negro = db.query(Color).filter(Color.name == "Negro").first()
        rojo = db.query(Color).filter(Color.name == "Rojo").first()
        azul = db.query(Color).filter(Color.name == "Azul").first()
        blanco = db.query(Color).filter(Color.name == "Blanco").first()
        
        demo_units = [
            Unit(
                engine_number="YBR125001",
                chassis_number="YBR125CH001",
                model_id=ybr125.id,
                color_id=negro.id,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE,
                purchase_price=45000.00,
                sale_price=52000.00
            ),
            Unit(
                engine_number="YBR125002",
                chassis_number="YBR125CH002",
                model_id=ybr125.id,
                color_id=rojo.id,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE,
                purchase_price=45000.00,
                sale_price=52000.00
            ),
            Unit(
                engine_number="CB125F001",
                chassis_number="CB125FCH001",
                model_id=cb125f.id,
                color_id=azul.id,
                current_location_id=warehouse.id,
                status=UnitStatus.AVAILABLE,
                purchase_price=48000.00,
                sale_price=55000.00
            ),
            Unit(
                engine_number="CB125F002",
                chassis_number="CB125FCH002",
                model_id=cb125f.id,
                color_id=blanco.id,
                current_location_id=warehouse.id,
                status=UnitStatus.SOLD,
                purchase_price=48000.00,
                sale_price=55000.00,
                sold_date=datetime.now() - timedelta(days=5)
            ),
            Unit(
                engine_number="XTZ125001",
                chassis_number="XTZ125CH001",
                model_id=xtz125.id,
                color_id=negro.id,
                current_location_id=warehouse.id,
                status=UnitStatus.RESERVED,
                purchase_price=47000.00,
                sale_price=54000.00
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
                    price=unit.sale_price,
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

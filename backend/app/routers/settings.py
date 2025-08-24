
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole
from app.services.auth import get_current_active_user, require_role, get_password_hash

router = APIRouter()

# Settings endpoints
@router.get("/", response_model=List[schemas.Setting])
def get_settings(
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Setting).filter(models.Setting.is_active == True)
    
    if category:
        query = query.filter(models.Setting.category == category)
    
    settings = query.offset(skip).limit(limit).all()
    return settings

@router.get("/{setting_key}", response_model=schemas.Setting)
def get_setting(
    setting_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    setting = db.query(models.Setting).filter(
        models.Setting.key == setting_key,
        models.Setting.is_active == True
    ).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.post("/", response_model=schemas.Setting)
def create_setting(
    setting: schemas.SettingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    # Check if setting key already exists
    existing_setting = db.query(models.Setting).filter(models.Setting.key == setting.key).first()
    if existing_setting:
        raise HTTPException(status_code=400, detail="Setting key already exists")
    
    db_setting = models.Setting(**setting.dict())
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

@router.put("/{setting_key}", response_model=schemas.Setting)
def update_setting(
    setting_key: str,
    setting_update: schemas.SettingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    db_setting = db.query(models.Setting).filter(models.Setting.key == setting_key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    update_data = setting_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_setting, field, value)
    
    db.commit()
    db.refresh(db_setting)
    return db_setting

@router.delete("/{setting_key}")
def delete_setting(
    setting_key: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    db_setting = db.query(models.Setting).filter(models.Setting.key == setting_key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    db.delete(db_setting)
    db.commit()
    return {"message": "Setting deleted successfully"}

# Brands endpoints
@router.get("/brands/", response_model=List[schemas.Brand])
def get_brands(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    brands = db.query(models.Brand).filter(models.Brand.is_active == True) \
               .offset(skip).limit(limit).all()
    return brands

@router.post("/brands/", response_model=schemas.Brand)
def create_brand(
    brand: schemas.BrandCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    # Check if brand already exists
    existing_brand = db.query(models.Brand).filter(models.Brand.name == brand.name).first()
    if existing_brand:
        raise HTTPException(status_code=400, detail="Brand already exists")
    
    db_brand = models.Brand(**brand.dict())
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.put("/brands/{brand_id}", response_model=schemas.Brand)
def update_brand(
    brand_id: int,
    brand_update: schemas.BrandCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    db_brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Check for duplicate name
    existing_brand = db.query(models.Brand).filter(
        models.Brand.name == brand_update.name,
        models.Brand.id != brand_id
    ).first()
    if existing_brand:
        raise HTTPException(status_code=400, detail="Brand name already exists")
    
    db_brand.name = brand_update.name
    db.commit()
    db.refresh(db_brand)
    return db_brand

@router.delete("/brands/{brand_id}")
def delete_brand(
    brand_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    db_brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Check if brand has models
    model_count = db.query(models.Model).filter(models.Model.brand_id == brand_id).count()
    if model_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete brand with existing models")
    
    db_brand.is_active = False
    db.commit()
    return {"message": "Brand deactivated successfully"}

# Models endpoints
@router.get("/models/", response_model=List[schemas.Model])
def get_models(
    brand_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Model).filter(models.Model.is_active == True)
    
    if brand_id:
        query = query.filter(models.Model.brand_id == brand_id)
    
    models = query.offset(skip).limit(limit).all()
    return models

@router.post("/models/", response_model=schemas.Model)
def create_model(
    model: schemas.ModelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    # Check if brand exists
    brand = db.query(models.Brand).filter(models.Brand.id == model.brand_id).first()
    if not brand:
        raise HTTPException(status_code=400, detail="Brand not found")
    
    # Check if model already exists for this brand
    existing_model = db.query(models.Model).filter(
        models.Model.name == model.name,
        models.Model.brand_id == model.brand_id
    ).first()
    if existing_model:
        raise HTTPException(status_code=400, detail="Model already exists for this brand")
    
    db_model = models.Model(**model.dict())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

@router.put("/models/{model_id}", response_model=schemas.Model)
def update_model(
    model_id: int,
    model_update: schemas.ModelCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    db_model = db.query(models.Model).filter(models.Model.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check for duplicate name within brand
    existing_model = db.query(models.Model).filter(
        models.Model.name == model_update.name,
        models.Model.brand_id == model_update.brand_id,
        models.Model.id != model_id
    ).first()
    if existing_model:
        raise HTTPException(status_code=400, detail="Model name already exists for this brand")
    
    update_data = model_update.dict()
    for field, value in update_data.items():
        setattr(db_model, field, value)
    
    db.commit()
    db.refresh(db_model)
    return db_model

@router.delete("/models/{model_id}")
def delete_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    db_model = db.query(models.Model).filter(models.Model.id == model_id).first()
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check if model has units
    unit_count = db.query(models.Unit).filter(models.Unit.model_id == model_id).count()
    if unit_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete model with existing units")
    
    db_model.is_active = False
    db.commit()
    return {"message": "Model deactivated successfully"}

# Colors endpoints
@router.get("/colors/", response_model=List[schemas.Color])
def get_colors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    colors = db.query(models.Color).filter(models.Color.is_active == True) \
               .offset(skip).limit(limit).all()
    return colors

@router.post("/colors/", response_model=schemas.Color)
def create_color(
    color: schemas.ColorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    # Check if color already exists
    existing_color = db.query(models.Color).filter(models.Color.name == color.name).first()
    if existing_color:
        raise HTTPException(status_code=400, detail="Color already exists")
    
    db_color = models.Color(**color.dict())
    db.add(db_color)
    db.commit()
    db.refresh(db_color)
    return db_color

# Locations endpoints
@router.get("/locations/", response_model=List[schemas.Location])
def get_locations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    locations = db.query(models.Location).filter(models.Location.is_active == True) \
                  .offset(skip).limit(limit).all()
    return locations

@router.post("/locations/", response_model=schemas.Location)
def create_location(
    location: schemas.LocationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    db_location = models.Location(**location.dict())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@router.put("/locations/{location_id}", response_model=schemas.Location)
def update_location(
    location_id: int,
    location_update: schemas.LocationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    update_data = location_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_location, field, value)
    
    db.commit()
    db.refresh(db_location)
    return db_location

@router.delete("/locations/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    db_location = db.query(models.Location).filter(models.Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Check if location has units
    unit_count = db.query(models.Unit).filter(models.Unit.current_location_id == location_id).count()
    if unit_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete location with existing units")
    
    db_location.is_active = False
    db.commit()
    return {"message": "Location deactivated successfully"}

# Users management endpoints
@router.get("/users/", response_model=List[schemas.User])
def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    users = db.query(models.User).filter(models.User.is_active == True) \
              .offset(skip).limit(limit).all()
    return users

@router.post("/users/", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    # Check if user exists
    existing_user = db.query(models.User).filter(
        (models.User.email == user.email) | 
        (models.User.username == user.username)
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email or username already exists")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/users/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_active = False
    db.commit()
    return {"message": "User deactivated successfully"}

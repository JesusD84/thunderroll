"""Model equivalence resolution and administration (TR-05).

Suppliers ship units labelled with their own internal model names. This service
translates a manufacturer model into the client's internal model when an
equivalence exists, and never blocks the import when it does not (the caller
keeps the manufacturer name as-is). It also exposes CRUD + an "unmapped models"
listing so equivalences can be administered after the fact.

Matching is case-insensitive and whitespace-normalized so noisy supplier labels
("X3", "x3 ", "X3\n") resolve to the same equivalence.
"""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import ModelEquivalence, Unit
from app.models import schemas


def normalize_model(value: Optional[str]) -> str:
    """Collapse whitespace/newlines and strip. Empty for blank input."""
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def resolve_internal_model(db: Session, manufacturer_model: Optional[str]) -> Optional[str]:
    """Return the internal model for a manufacturer model, or ``None``.

    ``None`` means "no equivalence" (or blank input); the import keeps the
    manufacturer model verbatim in that case.
    """
    key = normalize_model(manufacturer_model)
    if not key:
        return None
    match = (
        db.query(ModelEquivalence)
        .filter(func.lower(ModelEquivalence.manufacturer_model) == key.lower())
        .first()
    )
    return match.internal_model if match else None


def get_equivalences(db: Session, skip: int = 0, limit: int = 100) -> list[ModelEquivalence]:
    return (
        db.query(ModelEquivalence)
        .order_by(ModelEquivalence.manufacturer_model)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_equivalence(db: Session, equivalence_id: int) -> ModelEquivalence:
    record = db.query(ModelEquivalence).filter(ModelEquivalence.id == equivalence_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Model equivalence not found")
    return record


def _find_by_manufacturer(db: Session, manufacturer_model: str) -> Optional[ModelEquivalence]:
    return (
        db.query(ModelEquivalence)
        .filter(func.lower(ModelEquivalence.manufacturer_model) == manufacturer_model.lower())
        .first()
    )


def create_equivalence(
    db: Session, payload: schemas.ModelEquivalenceCreate
) -> ModelEquivalence:
    manufacturer = normalize_model(payload.manufacturer_model)
    internal = normalize_model(payload.internal_model)
    if not manufacturer or not internal:
        raise HTTPException(
            status_code=400,
            detail="manufacturer_model and internal_model are required",
        )
    if _find_by_manufacturer(db, manufacturer):
        raise HTTPException(
            status_code=409,
            detail=f"An equivalence for '{manufacturer}' already exists",
        )
    record = ModelEquivalence(
        manufacturer_model=manufacturer,
        internal_model=internal,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_equivalence(
    db: Session, equivalence_id: int, payload: schemas.ModelEquivalenceUpdate
) -> ModelEquivalence:
    record = get_equivalence(db, equivalence_id)
    if payload.manufacturer_model is not None:
        manufacturer = normalize_model(payload.manufacturer_model)
        if not manufacturer:
            raise HTTPException(status_code=400, detail="manufacturer_model cannot be blank")
        clash = _find_by_manufacturer(db, manufacturer)
        if clash and clash.id != record.id:
            raise HTTPException(
                status_code=409,
                detail=f"An equivalence for '{manufacturer}' already exists",
            )
        record.manufacturer_model = manufacturer
    if payload.internal_model is not None:
        internal = normalize_model(payload.internal_model)
        if not internal:
            raise HTTPException(status_code=400, detail="internal_model cannot be blank")
        record.internal_model = internal
    if payload.notes is not None:
        record.notes = payload.notes
    db.commit()
    db.refresh(record)
    return record


def delete_equivalence(db: Session, equivalence_id: int) -> dict:
    record = get_equivalence(db, equivalence_id)
    db.delete(record)
    db.commit()
    return {"message": "Model equivalence deleted successfully"}


def list_unmapped_models(db: Session) -> list[str]:
    """Distinct unit models that have no equivalence (manufacturer or internal).

    Lets an admin see which models currently in inventory still need an
    equivalence so they can be mapped later (TR-05 AC4).
    """
    mapped: set[str] = set()
    for record in db.query(ModelEquivalence).all():
        mapped.add(record.manufacturer_model.strip().lower())
        mapped.add(record.internal_model.strip().lower())

    unmapped: list[str] = []
    for (model,) in db.query(Unit.model).distinct().all():
        if not model:
            continue
        if model.strip().lower() not in mapped:
            unmapped.append(model)
    return sorted(unmapped)


def upsert_equivalence(db: Session, manufacturer_model: str, internal_model: str) -> ModelEquivalence:
    """Create or update an equivalence by manufacturer model. Idempotent (seeding)."""
    manufacturer = normalize_model(manufacturer_model)
    internal = normalize_model(internal_model)
    record = _find_by_manufacturer(db, manufacturer)
    if record:
        record.internal_model = internal
    else:
        record = ModelEquivalence(manufacturer_model=manufacturer, internal_model=internal)
        db.add(record)
    db.commit()
    db.refresh(record)
    return record

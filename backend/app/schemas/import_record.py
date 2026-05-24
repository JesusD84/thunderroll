from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user import User


class ImportBase(BaseModel):
    filename: str
    original_filename: str
    total_records: int
    notes: Optional[str] = None


class ImportCreate(ImportBase):
    pass


class Import(ImportBase):
    id: int
    successful_imports: int
    failed_imports: int
    user_id: int
    status: str
    import_date: datetime
    completed_at: Optional[datetime] = None
    user: Optional[User] = None
    model_config = ConfigDict(from_attributes=True)

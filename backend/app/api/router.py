from fastapi import APIRouter
from app.api.v1.router import router as v1_router

router = APIRouter()

router.include_router(v1_router, prefix="/api/v1")

@router.get("/")
def read_root():
    return {"message": "Thunderrol Inventory API"}

@router.get("/health")
def health_check():
    return {"status": "healthy", "service": "Thunderrol API"}
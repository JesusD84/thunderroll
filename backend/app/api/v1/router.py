from fastapi import APIRouter

from app.api.v1.endpoints import auth, units, locations, imports, reports, user, transfers

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(user.router, prefix="/user", tags=["User"])
router.include_router(units.router, prefix="/units", tags=["Units"])
router.include_router(locations.router, prefix="/locations", tags=["Locations"])
router.include_router(imports.router, prefix="/imports", tags=["Imports"])
router.include_router(transfers.router, prefix="/transfers", tags=["Transfers"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
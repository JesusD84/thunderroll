
"""Main API router."""

from fastapi import APIRouter

from app.api.endpoints import auth, units, imports, transfers, sales, reports, catalogs

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(units.router, prefix="/units", tags=["units"])  
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["transfers"])
api_router.include_router(sales.router, prefix="/sales", tags=["sales"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(catalogs.router, prefix="/catalogs", tags=["catalogs"])

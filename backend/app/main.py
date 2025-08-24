
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.database.database import engine, SessionLocal, get_db
from app.models import models
from app.routers import auth, units, imports, transfers, reports, settings
from app.database.seed import create_demo_data

# Create tables
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_demo_data()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Thunderrol Inventory API",
    description="API for Thunderrol inventory management system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

# Static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(units.router, prefix="/api/units", tags=["Units"])
app.include_router(imports.router, prefix="/api/imports", tags=["Imports"])
app.include_router(transfers.router, prefix="/api/transfers", tags=["Transfers"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])

@app.get("/")
def read_root():
    return {"message": "Thunderrol Inventory API"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "Thunderrol API"}

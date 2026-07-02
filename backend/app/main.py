
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.database.database import engine
from app.models import models
from app.api.router import router as api_router
from app.database.seed import create_demo_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create the schema and seed demo data against the prod engine.
    # This runs on app startup (not at module import) so importing app.main does
    # not require a reachable DATABASE_URL. See TR-11.
    models.Base.metadata.create_all(bind=engine)
    create_demo_data()
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
allowed_origins = ["http://localhost:3000", "http://frontend:3000"]
# Single origin (backwards compat)
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)
# Comma-separated list for multiple Vercel/preview URLs
extra_origins = os.getenv("ALLOWED_ORIGINS", "")
if extra_origins:
    allowed_origins.extend(o.strip() for o in extra_origins.split(",") if o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

# Static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers
app.include_router(api_router)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.router import router as api_router
from app.core.cors import build_allowed_origins
from app.core.rate_limit import AccountCaptureMiddleware, limiter
from app.database.database import engine
from app.database.seed import create_demo_data
from app.models import models


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
    title="Thunderoll Inventory API",
    description="API for Thunderoll inventory management system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware.
#
# Los orígenes de localhost solo se permiten en desarrollo (ENV=development):
# en producción, dejarlos abiertos permitiría que cualquier página servida en
# ese puerto hable con la API. FRONTEND_URL y ALLOWED_ORIGINS son los que
# mandan en producción.
allowed_origins = build_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# El limitador necesita leer el cuerpo de las peticiones de autenticación
# para saber a qué cuenta se está atacando. Va por fuera del de CORS para que
# el cuerpo llegue intacto tanto al middleware como al endpoint.
app.add_middleware(AccountCaptureMiddleware)

# Rate limiting: el decorador de cada endpoint registra sus límites, y aquí
# se conecta el limitador con la aplicación y se traduce el exceso a un 429.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(api_router)

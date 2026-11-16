
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Sin DATABASE_URL se usa un placeholder local. Es preferible fallar en
    # la conexión (con un mensaje claro) que apuntar a una credencial fija
    # publicada en el repo.
    print(
        "⚠️  DATABASE_URL no está definida: se usa el placeholder local "
        "postgresql://thunderoll:change-me@localhost:5432/thunderoll.",
        flush=True,
    )
    DATABASE_URL = "postgresql://thunderoll:change-me@localhost:5432/thunderoll"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

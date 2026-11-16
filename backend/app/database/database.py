from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import require_database_url

# La URL de la base de datos viene solo del entorno. Sin ella la app no
# arranca: un default fijo en el código publicaría una credencial y apuntaría
# a una base que no es la de producción. En los tests, `tests/conftest.py`
# define una URL de SQLite antes de importar la app.
DATABASE_URL = require_database_url()

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

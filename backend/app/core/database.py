"""
Connexion à la base de données PostgreSQL via SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency FastAPI : fournit une session DB par requête
    et la ferme proprement à la fin.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

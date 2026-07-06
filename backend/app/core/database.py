"""
Connexion à la base de données PostgreSQL via SQLAlchemy.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# En environnement serverless (Vercel définit automatiquement la variable VERCEL),
# chaque instance de fonction peut créer ses propres connexions : un pool large
# épuiserait vite les connexions disponibles côté PostgreSQL managé. On réduit donc
# drastiquement le pool dans ce contexte, sans rien changer au comportement
# Docker/VPS existant.
_IS_SERVERLESS = bool(os.environ.get("VERCEL"))

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    pool_size=1 if _IS_SERVERLESS else settings.DB_POOL_SIZE,
    max_overflow=1 if _IS_SERVERLESS else settings.DB_MAX_OVERFLOW,
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

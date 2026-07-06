"""
Point d'entrée principal de l'application FastAPI.
China AI Import Assistant - Backend API.
"""
import logging
import sys
from pathlib import Path

# Permet d'importer ai_engine/ et scraper/ (packages frères de backend/)
# quand l'app est lancée avec cwd=backend/ (uvicorn app.main:app), comme
# documenté dans le README - ces packages ne sont pas sous backend/.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API de la plateforme China AI Import Assistant : analyse de produits, "
        "détection de pièges d'achat, scraping fournisseurs et scoring de produits gagnants."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formate proprement les erreurs de validation Pydantic."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Erreur de validation des données", "errors": exc.errors()},
    )


@app.on_event("startup")
def on_startup():
    """Crée les tables en base si elles n'existent pas encore (dev only ; utiliser Alembic en prod)."""
    # Import explicite pour s'assurer que tous les modèles sont enregistrés
    import app.models  # noqa: F401

    if settings.APP_ENV == "development":
        Base.metadata.create_all(bind=engine)
        logger.info("Tables vérifiées/créées (mode développement).")


@app.get("/", tags=["Santé"])
def root():
    """Endpoint racine : vérifie que l'API est en ligne."""
    return {
        "service": settings.APP_NAME,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["Santé"])
def health_check():
    """Healthcheck pour Docker / monitoring."""
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.API_V1_PREFIX)

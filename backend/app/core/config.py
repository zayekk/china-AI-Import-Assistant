"""
Configuration centrale de l'application.
Charge les variables d'environnement via pydantic-settings.
"""
import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Application ---
    APP_NAME: str = "China AI Import Assistant"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Sécurité / JWT ---
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Base de données ---
    DATABASE_URL: str = (
        "postgresql+psycopg2://china_ai_user:china_ai_password@localhost:5432/china_ai_db"
    )
    DATABASE_ECHO: bool = False
    # Taille du pool de connexions SQLAlchemy. Sur un serveur classique (Docker/VPS),
    # les valeurs par défaut conviennent. En environnement serverless (Vercel), le
    # pool est automatiquement réduit (voir database.py) pour éviter d'épuiser les
    # connexions disponibles côté PostgreSQL managé.
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- CORS ---
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    # --- IA : Mistral ---
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-large-latest"
    MISTRAL_API_URL: str = "https://api.mistral.ai/v1/chat/completions"
    MISTRAL_TIMEOUT_SECONDS: int = 60

    # --- OCR / Vision ---
    OCR_LANG: str = "chi_sim+eng+fra"
    TESSERACT_CMD: str = "/usr/bin/tesseract"

    # --- Scraper ---
    SCRAPER_HEADLESS: bool = True
    SCRAPER_TIMEOUT_MS: int = 30000
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    SCRAPER_MAX_RETRIES: int = 3
    SCRAPER_PROXY: str | None = None

    # --- Fichiers / Uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # --- Redis (cache / rate limiting, optionnel) ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Estimation import ---
    IMPORT_AIR_RATE_CNY_PER_KG: float = 55.0
    IMPORT_SEA_RATE_CNY_PER_KG: float = 12.0
    IMPORT_EUR_CNY_RATE: float = 0.13

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique (mise en cache) des settings."""
    s = Settings()

    # Sur Vercel, la plateforme expose automatiquement VERCEL_URL (domaine du
    # déploiement courant, y compris pour les previews). On l'ajoute aux origines
    # CORS autorisées sans configuration manuelle supplémentaire.
    vercel_url = os.environ.get("VERCEL_URL")
    if vercel_url:
        origin = f"https://{vercel_url}"
        if origin not in s.CORS_ORIGINS:
            s.CORS_ORIGINS = [*s.CORS_ORIGINS, origin]

    return s


settings = get_settings()

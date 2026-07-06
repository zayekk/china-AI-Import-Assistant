"""
Agrège tous les routers de l'API sous un routeur unique.
"""
from fastapi import APIRouter

from app.api import analysis, auth, import_estimate, products, scan_guide, score, scrape

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(analysis.router)
api_router.include_router(scrape.router)
api_router.include_router(products.router)
api_router.include_router(score.router)
api_router.include_router(import_estimate.router)
api_router.include_router(scan_guide.router)

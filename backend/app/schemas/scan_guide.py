"""
Schémas Pydantic : étapes du scan guidé ("Scan produit complet").

Le scan guidé encadre l'utilisateur pas-à-pas (jusqu'à 12 étapes) pour capturer
méthodiquement une fiche produit, au lieu de lui laisser envoyer des captures
au hasard. Chaque étape correspond à une catégorie canonique déjà utilisée par
le module d'analyse multi-captures (`ai_engine/services/multi_capture_service.py`).
"""
from typing import Literal

from pydantic import BaseModel, Field

ScanGuideCategory = Literal["main_page", "product_info", "shop", "reviews", "shipping"]


class ScanGuideStep(BaseModel):
    step: int = Field(..., ge=1, le=12)
    instruction: str
    category: ScanGuideCategory
    required: bool

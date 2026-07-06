"""
Router API : estimation du coût d'importation.

POST /import-estimate -> calcule le coût total d'importation (produit + transport
+ douane), la marge estimée et une recommandation d'achat.
"""
import logging

from fastapi import APIRouter, Depends

from app.core.deps import get_optional_user
from app.models.user import User
from app.schemas.import_estimate import ImportEstimateRequest, ImportEstimateResponse
from app.services.import_estimate_service import compute_import_estimate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analyse Importation"])


@router.post("/import-estimate", response_model=ImportEstimateResponse)
def import_estimate(
    payload: ImportEstimateRequest,
    current_user: User | None = Depends(get_optional_user),
):
    """
    Calcule le coût total d'importation (produit + transport + douane), le coût
    par unité, la marge estimée (si un prix de revente cible est fourni) et une
    recommandation d'achat déterministe.

    Calcul 100% local et déterministe : aucun appel réseau/IA, aucune
    persistance en base (endpoint stateless).
    """
    return compute_import_estimate(payload)

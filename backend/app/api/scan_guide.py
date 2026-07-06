"""
Router API : étapes du scan guidé ("Scan produit complet").

GET /scan-guide/steps -> retourne les 12 étapes du parcours guidé (5 obligatoires
couvrant chacune des 5 catégories de `CAPTURE_CATEGORIES`, 7 optionnelles).
"""
from fastapi import APIRouter

from app.schemas.scan_guide import ScanGuideStep

router = APIRouter(tags=["Scan Guidé"])

SCAN_GUIDE_STEPS = [
    ScanGuideStep(step=1, instruction="Prenez le haut de la page produit (nom, image, prix)", category="main_page", required=True),
    ScanGuideStep(step=2, instruction="Descendez vers les détails produit (description, caractéristiques)", category="product_info", required=True),
    ScanGuideStep(step=3, instruction="Ouvrez les variantes (tailles, couleurs, options)", category="product_info", required=False),
    ScanGuideStep(step=4, instruction="Ouvrez les informations vendeur (boutique, ancienneté, note)", category="shop", required=True),
    ScanGuideStep(step=5, instruction="Ouvrez les avis clients (notes, commentaires)", category="reviews", required=True),
    ScanGuideStep(step=6, instruction="Ouvrez les photos clients dans les avis", category="reviews", required=False),
    ScanGuideStep(step=7, instruction="Ouvrez la page livraison (délai, frais)", category="shipping", required=True),
    ScanGuideStep(step=8, instruction="Zoomez sur le prix et les promotions en cours", category="main_page", required=False),
    ScanGuideStep(step=9, instruction="Vérifiez les badges et certifications de la boutique", category="shop", required=False),
    ScanGuideStep(step=10, instruction="Capturez les dimensions/poids si affichés", category="product_info", required=False),
    ScanGuideStep(step=11, instruction="Ouvrez les conditions de retour ou garantie", category="shipping", required=False),
    ScanGuideStep(step=12, instruction="Capturez d'éventuels problèmes récurrents signalés dans les avis", category="reviews", required=False),
]


@router.get("/scan-guide/steps", response_model=list[ScanGuideStep])
def get_scan_guide_steps():
    """Retourne les 12 étapes du scan guidé (5 obligatoires couvrant chacune des 5 catégories, 7 optionnelles)."""
    return SCAN_GUIDE_STEPS

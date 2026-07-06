"""
Service de scoring "produit gagnant" : calcule les 5 sous-scores pondérés
(demande 30%, marge 25%, qualité 20%, fiabilité vendeur 15%, logistique 10%).
"""
import logging

from ai_engine.prompts.product_prompts import (
    SYSTEM_PROMPT_WINNING_PRODUCT,
    build_user_prompt_for_winning_product,
)
from ai_engine.services.mistral_client import MistralAPIError, mistral_client

logger = logging.getLogger(__name__)

WEIGHTS = {
    "demand": 0.30,
    "margin": 0.25,
    "quality": 0.20,
    "supplier_reliability": 0.15,
    "logistics": 0.10,
}


def _clamp(value, default=0) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return float(default)
    return max(0.0, min(100.0, v))


def compute_final_score(sub_scores: dict) -> float:
    """Calcule le score final pondéré à partir des 5 sous-scores."""
    return round(
        sub_scores["demand_score"] * WEIGHTS["demand"]
        + sub_scores["margin_score"] * WEIGHTS["margin"]
        + sub_scores["quality_score"] * WEIGHTS["quality"]
        + sub_scores["supplier_reliability_score"] * WEIGHTS["supplier_reliability"]
        + sub_scores["logistics_score"] * WEIGHTS["logistics"],
        2,
    )


def _heuristic_winning_score(product_data: dict) -> dict:
    """Calcul heuristique de secours si l'IA est indisponible."""
    sales = product_data.get("sales_count") or 0
    price = product_data.get("price_value") or 0
    rating = product_data.get("rating") or 0
    supplier_score = product_data.get("supplier_score") or 50
    weight_kg = product_data.get("weight_kg")

    demand_score = _clamp(min(100, (sales / 50)) if sales else 20)
    margin_score = _clamp(60 if 5 <= price <= 200 else 35)
    quality_score = _clamp((rating / 5) * 100 if rating else 50)
    supplier_reliability_score = _clamp(supplier_score)
    logistics_score = _clamp(80 if (weight_kg is None or weight_kg < 1) else 50)

    sub_scores = {
        "demand_score": demand_score,
        "margin_score": margin_score,
        "quality_score": quality_score,
        "supplier_reliability_score": supplier_reliability_score,
        "logistics_score": logistics_score,
    }
    final = compute_final_score(sub_scores)

    return {
        **sub_scores,
        "final_score": final,
        "strengths": ["Score estimé via heuristique locale (IA indisponible)"],
        "risks": ["Analyse IA indisponible : données à considérer avec prudence"],
        "explanation": "Score calculé via heuristique locale (IA indisponible).",
    }


def score_winning_product(product_data: dict) -> dict:
    """
    Calcule le score complet 'produit gagnant' pour un produit donné.
    product_data attend des clés telles que :
    name, sales_count, price_value, rating, supplier_score, weight_kg, category.
    """
    try:
        user_prompt = build_user_prompt_for_winning_product(product_data)
        raw_result = mistral_client.chat_completion_json(
            system_prompt=SYSTEM_PROMPT_WINNING_PRODUCT,
            user_prompt=user_prompt,
        )

        sub_scores = {
            "demand_score": _clamp(raw_result.get("demand_score")),
            "margin_score": _clamp(raw_result.get("margin_score")),
            "quality_score": _clamp(raw_result.get("quality_score")),
            "supplier_reliability_score": _clamp(raw_result.get("supplier_reliability_score")),
            "logistics_score": _clamp(raw_result.get("logistics_score")),
        }
        final_score = compute_final_score(sub_scores)

        return {
            **sub_scores,
            "final_score": final_score,
            "strengths": list(raw_result.get("strengths") or []),
            "risks": list(raw_result.get("risks") or []),
            "explanation": str(raw_result.get("explanation", "")),
        }

    except MistralAPIError as exc:
        logger.error("Échec scoring produit gagnant IA, fallback heuristique activé: %s", exc)
        return _heuristic_winning_score(product_data)

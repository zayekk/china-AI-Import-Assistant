"""
Service d'analyse fournisseur : calcule un score de fiabilité /100
à partir des données scrapées (ancienneté, avis, litiges, etc.).
"""
import logging

from ai_engine.prompts.product_prompts import (
    SYSTEM_PROMPT_SUPPLIER_ANALYSIS,
    build_user_prompt_for_supplier_analysis,
)
from ai_engine.services.mistral_client import MistralAPIError, mistral_client

logger = logging.getLogger(__name__)


def _heuristic_supplier_score(supplier_data: dict) -> dict:
    """
    Calcul heuristique de secours (sans IA), utilisé si Mistral est indisponible.
    Règles simples mais raisonnables, jamais 100/100.
    """
    score = 50.0
    strengths: list[str] = []
    risks: list[str] = []

    years_active = supplier_data.get("years_active") or 0
    rating = supplier_data.get("rating") or 0
    total_reviews = supplier_data.get("total_reviews") or 0
    dispute_rate = supplier_data.get("dispute_rate") or 0

    if years_active >= 3:
        score += 15
        strengths.append("Vendeur établi depuis plusieurs années")
    elif years_active < 1:
        score -= 15
        risks.append("Vendeur récent, peu d'historique disponible")

    if rating >= 4.5:
        score += 10
        strengths.append("Note moyenne élevée")
    elif rating and rating < 3.5:
        score -= 15
        risks.append("Note moyenne faible")

    if total_reviews >= 1000:
        score += 10
        strengths.append("Grand volume d'avis clients")
    elif total_reviews < 50:
        risks.append("Peu d'avis disponibles, fiabilité incertaine")

    if dispute_rate and dispute_rate > 5:
        score -= 20
        risks.append("Taux de litiges élevé")

    score = max(0, min(95, round(score)))  # jamais 100/100

    return {
        "supplier_score": score,
        "strengths": strengths,
        "risks": risks or ["Données insuffisantes pour une évaluation complète"],
        "explanation": "Score calculé via heuristique locale (IA indisponible).",
    }


def analyze_supplier(supplier_data: dict) -> dict:
    """
    Analyse un fournisseur à partir de ses données brutes (scrapées ou saisies).
    supplier_data attend des clés telles que :
    years_active, rating, total_reviews, total_sales, response_rate,
    dispute_rate, repeat_buyer_rate, sample_reviews (liste de textes).
    """
    try:
        user_prompt = build_user_prompt_for_supplier_analysis(supplier_data)
        raw_result = mistral_client.chat_completion_json(
            system_prompt=SYSTEM_PROMPT_SUPPLIER_ANALYSIS,
            user_prompt=user_prompt,
        )
        score = raw_result.get("supplier_score", 0)
        try:
            score = max(0, min(100, int(score)))
        except (TypeError, ValueError):
            score = 0

        return {
            "supplier_score": score,
            "strengths": list(raw_result.get("strengths") or []),
            "risks": list(raw_result.get("risks") or []),
            "explanation": str(raw_result.get("explanation", "")),
        }

    except MistralAPIError as exc:
        logger.error("Échec analyse fournisseur IA, fallback heuristique activé: %s", exc)
        return _heuristic_supplier_score(supplier_data)

"""
Service d'analyse produit : combine le client Mistral, les prompts optimisés
et une couche de sécurité locale (détection de mots-clés pièges) en complément de l'IA.
"""
import logging
import re

from ai_engine.prompts.product_prompts import (
    SYSTEM_PROMPT_PRODUCT_ANALYSIS,
    TRAP_KEYWORDS,
    build_user_prompt_for_text_analysis,
)
from ai_engine.services.mistral_client import MistralAPIError, mistral_client

logger = logging.getLogger(__name__)

# Schéma de secours utilisé si l'IA est indisponible (dégradation gracieuse)
FALLBACK_RESULT = {
    "product_name": "",
    "included": [],
    "not_included": [],
    "warnings": [
        "Le moteur IA est momentanément indisponible. "
        "Cette analyse est partielle et basée uniquement sur une détection de mots-clés locale."
    ],
    "quality_score": 0,
    "supplier_score": 0,
    "profit_score": 0,
    "final_score": 0,
    "recommendation": "CAUTION",
    "detected_data": {},
    "ai_estimations": {},
    "missing_information": [
        "Analyse IA indisponible — seule une détection de mots-clés locale a été appliquée."
    ],
    "confidence_score": 0,
    "confidence_level": "insufficient",
    "confidence_reasons": ["Aucun appel IA n'a pu être effectué."],
    "confidence_risks": ["Impossible de vérifier les informations sans analyse IA complète."],
    "mobile_summary": "CAUTION — 0/100 — Analyse IA indisponible",
}


def detect_trap_keywords(text: str) -> list[str]:
    """
    Détection locale (sans IA) des mots-clés pièges les plus courants.
    Sert de filet de sécurité, y compris si l'appel IA échoue.
    """
    text_lower = text.lower()
    found = []
    for keyword in TRAP_KEYWORDS:
        # \b ne fonctionne pas bien avec des expressions multi-mots contenant des espaces simples,
        # on utilise donc une recherche de sous-chaîne robuste avec délimitation souple.
        pattern = r"(?<![a-z])" + re.escape(keyword) + r"(?![a-z])"
        if re.search(pattern, text_lower):
            found.append(keyword)
    return found


def _confidence_level(score: int) -> str:
    """
    Détermine STRICTEMENT côté serveur le niveau de confiance à partir du score numérique.
    Ce mapping ne doit jamais être délégué à l'IA : le champ "confidence_level" renvoyé
    par le modèle brut est toujours ignoré et recalculé ici.
    """
    if score <= 30:
        return "insufficient"
    if score <= 60:
        return "approximate"
    if score <= 80:
        return "reliable"
    return "high"


def _normalize_ai_result(raw: dict) -> dict:
    """S'assure que le résultat IA respecte bien le contrat de sortie, avec valeurs par défaut sûres."""
    def _clamp_score(value) -> int:
        try:
            v = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(100, v))

    recommendation = raw.get("recommendation", "CAUTION")
    if recommendation not in ("BUY", "AVOID", "CAUTION"):
        recommendation = "CAUTION"

    confidence_score = _clamp_score(raw.get("confidence_score", 0))
    final_score = _clamp_score(raw.get("final_score", 0))
    warnings = list(raw.get("warnings") or [])

    result = {
        "product_name": str(raw.get("product_name", "") or ""),
        "included": list(raw.get("included") or []),
        "not_included": list(raw.get("not_included") or []),
        "warnings": warnings,
        "quality_score": _clamp_score(raw.get("quality_score", 0)),
        "supplier_score": _clamp_score(raw.get("supplier_score", 0)),
        "profit_score": _clamp_score(raw.get("profit_score", 0)),
        "final_score": final_score,
        "recommendation": recommendation,
        "detected_data": dict(raw.get("detected_data") or {}),
        "ai_estimations": dict(raw.get("ai_estimations") or {}),
        "missing_information": list(raw.get("missing_information") or []),
        "confidence_score": confidence_score,
        # NB: on ignore volontairement toute valeur "confidence_level" fournie par l'IA brute ;
        # ce champ dérivé est toujours recalculé côté serveur via _confidence_level().
        "confidence_level": _confidence_level(confidence_score),
        "confidence_reasons": list(raw.get("confidence_reasons") or []),
        "confidence_risks": list(raw.get("confidence_risks") or []),
    }

    # Résumé compact sur une ligne, calculé STRICTEMENT côté serveur (jamais par l'IA),
    # destiné au futur affichage dans une bulle flottante mobile
    # (voir docs/mobile_architecture.md, section 5). Toujours recalculé ici pour que
    # TOUTES les analyses (texte/image/URL/multi-captures) en bénéficient automatiquement,
    # puisque `analyze_multi_capture()` réutilise cette même fonction de normalisation.
    result["mobile_summary"] = (
        f"{recommendation} — {final_score}/100 — "
        f"{warnings[0] if warnings else 'Aucun risque majeur détecté'}"
    )

    return result


def _apply_local_safety_net(result: dict, raw_text: str) -> dict:
    """
    Filet de sécurité local (indépendant de l'IA), factorisé pour être partagé entre
    `analyze_product_text()` (analyse texte simple) et `analyze_multi_capture()`
    (analyse multi-captures) :
    1. Détecte les mots-clés pièges dans `raw_text`.
    2. Ajoute un warning explicite pour chaque piège détecté qui n'apparaît dans
       aucun warning déjà présent dans `result`.
    3. Requalifie prudemment une recommandation IA "BUY" en "CAUTION" si des pièges
       ont été détectés localement (règle métier de protection acheteur).

    Modifie et retourne `result` (mutation in-place puis retour, pour usage direct
    en tant qu'expression `result = _apply_local_safety_net(result, raw_text)`).
    """
    local_traps = detect_trap_keywords(raw_text)

    existing_warnings_blob = " ".join(result["warnings"]).lower()
    for trap in local_traps:
        if trap not in existing_warnings_blob:
            result["warnings"].append(
                f"Mot-clé à risque détecté : \"{trap}\" — vérifiez precisément ce qui est inclus dans la vente."
            )

    if local_traps and result["recommendation"] == "BUY":
        result["recommendation"] = "CAUTION"
        result["warnings"].append(
            "Recommandation ajustée automatiquement en CAUTION suite à la détection de mots-clés à risque."
        )

    return result


def analyze_product_text(raw_text: str) -> dict:
    """
    Analyse un texte produit brut (titre/description, toute langue) :
    1. Détection locale de mots-clés pièges (filet de sécurité).
    2. Appel à l'IA Mistral pour l'analyse complète et la traduction.
    3. Fusion : les pièges détectés localement sont ajoutés aux warnings
       si l'IA ne les a pas explicitement mentionnés.
    """
    try:
        user_prompt = build_user_prompt_for_text_analysis(raw_text)
        raw_result = mistral_client.chat_completion_json(
            system_prompt=SYSTEM_PROMPT_PRODUCT_ANALYSIS,
            user_prompt=user_prompt,
        )
        result = _normalize_ai_result(raw_result)

    except MistralAPIError as exc:
        logger.error("Échec analyse IA, fallback local activé: %s", exc)
        result = dict(FALLBACK_RESULT)
        result["product_name"] = raw_text[:120]

    return _apply_local_safety_net(result, raw_text)

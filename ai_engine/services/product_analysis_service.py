"""
Service d'analyse produit : combine le client Mistral, les prompts optimisés
et une couche de sécurité locale (détection de mots-clés pièges) en complément de l'IA.
"""
import copy
import logging
import re

from app.core.config import settings
from app.services.import_estimate_service import (
    MARGIN_THRESHOLD_AVOID_PCT,
    MARGIN_THRESHOLD_BUY_PCT,
)

from ai_engine.prompts.product_prompts import (
    DEFAULT_LANGUAGE,
    TRAP_KEYWORDS,
    build_system_prompt,
    build_user_prompt_for_text_analysis,
)
from ai_engine.services.mistral_client import MistralAPIError, mistral_client

logger = logging.getLogger(__name__)

_VALID_DEMAND_LEVELS = ("very_high", "high", "medium", "low", "very_low")
_VALID_LANGUAGES = ("fr", "en")

# Chaînes localisées pour tout ce qui est généré côté SERVEUR (pas par l'IA) : filet de
# sécurité local et repli en cas d'échec IA. Sans ceci, ces messages resteraient toujours
# en français même quand l'utilisateur a choisi l'anglais -> mélange de langues.
_STRINGS = {
    "fr": {
        "fallback_warning": (
            "Le moteur IA est momentanément indisponible. "
            "Cette analyse est partielle et basée uniquement sur une détection de mots-clés locale."
        ),
        "fallback_missing_info": (
            "Analyse IA indisponible — seule une détection de mots-clés locale a été appliquée."
        ),
        "fallback_confidence_reason": "Aucun appel IA n'a pu être effectué.",
        "fallback_confidence_risk": "Impossible de vérifier les informations sans analyse IA complète.",
        "fallback_recommendation_summary": (
            "Analyse IA indisponible : impossible de formuler une recommandation fiable pour le moment."
        ),
        "fallback_import_decision_explanation": (
            "Analyse IA indisponible : décision d'import non évaluable pour le moment."
        ),
        "fallback_demand_explanation": (
            "Analyse IA indisponible : demande de marché non évaluable pour le moment."
        ),
        "fallback_commercial_potential_explanation": (
            "Analyse IA indisponible : potentiel commercial non évaluable pour le moment."
        ),
        "fallback_financial_reason": "Analyse IA indisponible — aucune estimation ne peut être calculée.",
        "fallback_quick_report": ["⚠ Analyse IA indisponible pour le moment."],
        "no_major_risk_detected": "Aucun risque majeur détecté",
        "insufficient_price_data": (
            "Données de prix/coût insuffisantes dans le texte source pour estimer une marge."
        ),
        "trap_warning": lambda trap: (
            f'Mot-clé à risque détecté : "{trap}" — vérifiez precisément ce qui est inclus dans la vente.'
        ),
        "recommendation_downgraded": (
            "Recommandation ajustée automatiquement en CAUTION suite à la détection de mots-clés à risque."
        ),
    },
    "en": {
        "fallback_warning": (
            "The AI engine is temporarily unavailable. "
            "This analysis is partial and based only on local keyword detection."
        ),
        "fallback_missing_info": (
            "AI analysis unavailable — only local keyword detection was applied."
        ),
        "fallback_confidence_reason": "No AI call could be made.",
        "fallback_confidence_risk": "Unable to verify information without a full AI analysis.",
        "fallback_recommendation_summary": (
            "AI analysis unavailable: unable to provide a reliable recommendation right now."
        ),
        "fallback_import_decision_explanation": (
            "AI analysis unavailable: import decision cannot be evaluated right now."
        ),
        "fallback_demand_explanation": (
            "AI analysis unavailable: market demand cannot be evaluated right now."
        ),
        "fallback_commercial_potential_explanation": (
            "AI analysis unavailable: commercial potential cannot be evaluated right now."
        ),
        "fallback_financial_reason": "AI analysis unavailable — no estimate can be computed.",
        "fallback_quick_report": ["⚠ AI analysis temporarily unavailable."],
        "no_major_risk_detected": "No major risk detected",
        "insufficient_price_data": (
            "Insufficient price/cost data in the source text to estimate a margin."
        ),
        "trap_warning": lambda trap: (
            f'Risky keyword detected: "{trap}" — check precisely what is included in the sale.'
        ),
        "recommendation_downgraded": (
            "Recommendation automatically downgraded to CAUTION due to a detected risky keyword."
        ),
    },
}


def _strings(language: str) -> dict:
    return _STRINGS.get(language, _STRINGS[DEFAULT_LANGUAGE])


def _fallback_result(language: str) -> dict:
    """Schéma de secours utilisé si l'IA est indisponible (dégradation gracieuse), localisé."""
    s = _strings(language)
    return {
        "product_name": "",
        "included": [],
        "not_included": [],
        "warnings": [s["fallback_warning"]],
        "quality_score": 0,
        "supplier_score": 0,
        "profit_score": 0,
        "final_score": 0,
        "recommendation": "CAUTION",
        "detected_data": {},
        "ai_estimations": {},
        "missing_information": [s["fallback_missing_info"]],
        "confidence_score": 0,
        "confidence_level": "insufficient",
        "confidence_reasons": [s["fallback_confidence_reason"]],
        "confidence_risks": [s["fallback_confidence_risk"]],
        "mobile_summary": f"CAUTION — 0/100 — {s['fallback_warning'][:40]}...",
        "critical_alerts": [],
        "ai_recommendation_summary": s["fallback_recommendation_summary"],
        "commercial_estimate": {
            "possible": False,
            "reason_if_not_possible": s["fallback_financial_reason"],
            "purchase_price_eur": None,
            "estimated_transport_eur": None,
            "estimated_customs_eur": None,
            "landed_cost_eur": None,
            "suggested_resale_price_eur": None,
            "estimated_profit_eur": None,
            "margin_percentage": None,
            "estimated_profit_fcfa": None,
            "commercial_potential": "low",
        },
        "supplier_reliability": "no",
        "margin_potential": "low",
        "language": language if language in _VALID_LANGUAGES else DEFAULT_LANGUAGE,
        "commercial_potential_rating": 1,
        "commercial_potential_explanation": s["fallback_commercial_potential_explanation"],
        "import_decision_explanation": s["fallback_import_decision_explanation"],
        "market_comparisons": [],
        "demand_level": "medium",
        "demand_explanation": s["fallback_demand_explanation"],
        "quick_report": list(s["fallback_quick_report"]),
        # decision_badge/risk_level/import_decision : simples valeurs par défaut, toujours
        # recalculées par `_apply_local_safety_net()` (appelée juste après dans tous les cas).
        "decision_badge": "caution",
        "risk_level": "high",
        "import_decision": "study",
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


def _supplier_reliability(score: int) -> str:
    """Fiabilité fournisseur Oui/Moyen/Non, mêmes seuils que ScoreBadge.jsx (70/40)."""
    if score >= 70:
        return "yes"
    if score >= 40:
        return "medium"
    return "no"


def _margin_potential(score: int) -> str:
    """Potentiel de marge Faible/Moyenne/Forte, mêmes seuils que ScoreBadge.jsx (70/40)."""
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _risk_level(warnings: list, confidence_risks: list, critical_alerts: list, recommendation: str) -> str:
    """
    Niveau de risque global, déduit localement du nombre de signaux d'alerte déjà
    calculés (aucun nouvel appel IA). Une recommandation "AVOID" ou la moindre alerte
    critique (contradiction factuelle avérée) force directement le niveau "high" :
    plus grave qu'une simple incertitude, ne doit jamais se fondre dans une moyenne.
    """
    if recommendation == "AVOID" or critical_alerts:
        return "high"
    weighted = len(warnings) + len(confidence_risks)
    if weighted == 0:
        return "low"
    if weighted <= 3:
        return "medium"
    return "high"


def _decision_badge(final_score: int, recommendation: str, confidence_level: str, critical_alerts: list) -> str:
    """
    Badge de décision (🟢/🟡/🟠/🔴 côté frontend), calculé STRICTEMENT côté serveur à partir
    du score final, de la recommandation IA, du niveau de confiance et des alertes critiques.
    Jamais délégué à l'IA : garantit un mapping déterministe et testable.
    """
    if recommendation == "AVOID" or final_score < 35:
        return "avoid"
    if critical_alerts:
        return "caution"
    if recommendation == "CAUTION":
        return "verify" if final_score >= 55 else "caution"
    # recommendation == "BUY" à partir d'ici
    if confidence_level == "insufficient":
        return "verify"
    if final_score >= 70:
        return "recommended"
    if final_score >= 55:
        return "verify"
    return "caution"


def _import_decision(
    decision_badge: str, margin_potential: str, commercial_potential_rating: int, critical_alerts: list
) -> str:
    """
    "Décision Import" (carte dédiée, distincte de decision_badge qui porte sur la sécurité de
    l'achat) : calculée STRICTEMENT côté serveur en agrégeant des signaux déjà produits
    (decision_badge, margin_potential, commercial_potential_rating, critical_alerts) — aucun
    appel IA supplémentaire, aucune duplication de logique de scoring.
    """
    if decision_badge == "avoid" or critical_alerts:
        return "avoid"
    if decision_badge == "recommended" and margin_potential != "low" and commercial_potential_rating >= 3:
        return "import"
    if decision_badge == "verify" and margin_potential == "high" and commercial_potential_rating >= 4:
        return "import"
    return "study"


def _clamp_optional_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_rating(value) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 3
    return max(1, min(5, v))


def _normalize_demand_level(raw_value) -> str:
    value = str(raw_value or "").strip().lower()
    return value if value in _VALID_DEMAND_LEVELS else "medium"


def _normalize_market_comparisons(raw: dict) -> list[dict]:
    items = raw.get("market_comparisons")
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        component = str(item.get("component", "")).strip()
        detected_value = str(item.get("detected_value", "")).strip()
        comparison = str(item.get("comparison", "")).strip()
        if component and detected_value and comparison:
            result.append(
                {"component": component, "detected_value": detected_value, "comparison": comparison}
            )
    return result


def _normalize_commercial_estimate(raw: dict, profit_score: int, language: str) -> tuple[dict, str]:
    """
    Normalise l'estimation commerciale/financière : l'IA ne fournit que 4 montants "input" en
    euros (purchase_price_eur, estimated_transport_eur, estimated_customs_eur,
    suggested_resale_price_eur) ; TOUTE l'arithmétique dérivée (coût rendu, bénéfice, marge %,
    conversion FCFA au taux fixe réel) est calculée ici, jamais par l'IA.

    Retourne (commercial_estimate_dict, margin_potential). "margin_potential" est dérivé de
    margin_percentage quand une marge concrète est calculable (seuils réels réutilisés de
    app.services.import_estimate_service, la même règle métier que le calculateur d'import
    manuel) ; sinon repli sur le score de profit IA (mêmes seuils que ScoreBadge.jsx : 70/40).
    """
    raw_estimate = raw.get("commercial_estimate")
    if not isinstance(raw_estimate, dict):
        raw_estimate = {}

    purchase_price = _clamp_optional_float(raw_estimate.get("purchase_price_eur"))
    transport = _clamp_optional_float(raw_estimate.get("estimated_transport_eur"))
    customs = _clamp_optional_float(raw_estimate.get("estimated_customs_eur"))
    resale_price = _clamp_optional_float(raw_estimate.get("suggested_resale_price_eur"))
    reason_if_not_possible = raw_estimate.get("reason_if_not_possible") or None

    possible = bool(raw_estimate.get("possible", False)) and purchase_price is not None

    landed_cost = None
    profit = None
    margin_pct = None
    profit_fcfa = None
    margin_potential = _margin_potential(profit_score)  # repli par défaut

    if possible:
        landed_cost = purchase_price + (transport or 0.0) + (customs or 0.0)
        if resale_price is not None and resale_price > 0:
            profit = resale_price - landed_cost
            margin_pct = (profit / resale_price) * 100
            profit_fcfa = round(profit * settings.IMPORT_EUR_XOF_RATE)
            if margin_pct >= MARGIN_THRESHOLD_BUY_PCT:
                margin_potential = "high"
            elif margin_pct < MARGIN_THRESHOLD_AVOID_PCT:
                margin_potential = "low"
            else:
                margin_potential = "medium"
    else:
        purchase_price = transport = customs = resale_price = None
        reason_if_not_possible = reason_if_not_possible or _strings(language)["insufficient_price_data"]

    return (
        {
            "possible": possible,
            "reason_if_not_possible": reason_if_not_possible,
            "purchase_price_eur": round(purchase_price, 2) if purchase_price is not None else None,
            "estimated_transport_eur": round(transport, 2) if transport is not None else None,
            "estimated_customs_eur": round(customs, 2) if customs is not None else None,
            "landed_cost_eur": round(landed_cost, 2) if landed_cost is not None else None,
            "suggested_resale_price_eur": round(resale_price, 2) if resale_price is not None else None,
            "estimated_profit_eur": round(profit, 2) if profit is not None else None,
            "margin_percentage": round(margin_pct, 2) if margin_pct is not None else None,
            "estimated_profit_fcfa": profit_fcfa,
            "commercial_potential": margin_potential,
        },
        margin_potential,
    )


def _normalize_ai_result(raw: dict, language: str = DEFAULT_LANGUAGE) -> dict:
    """S'assure que le résultat IA respecte bien le contrat de sortie, avec valeurs par défaut sûres."""
    def _clamp_score(value) -> int:
        try:
            v = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(100, v))

    language = language if language in _VALID_LANGUAGES else DEFAULT_LANGUAGE

    recommendation = raw.get("recommendation", "CAUTION")
    if recommendation not in ("BUY", "AVOID", "CAUTION"):
        recommendation = "CAUTION"

    confidence_score = _clamp_score(raw.get("confidence_score", 0))
    final_score = _clamp_score(raw.get("final_score", 0))
    supplier_score = _clamp_score(raw.get("supplier_score", 0))
    profit_score = _clamp_score(raw.get("profit_score", 0))
    warnings = list(raw.get("warnings") or [])
    confidence_level = _confidence_level(confidence_score)
    critical_alerts = [str(item) for item in (raw.get("critical_alerts") or [])]
    commercial_estimate, margin_potential = _normalize_commercial_estimate(raw, profit_score, language)

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
        "confidence_level": confidence_level,
        "confidence_reasons": list(raw.get("confidence_reasons") or []),
        "confidence_risks": list(raw.get("confidence_risks") or []),
        "critical_alerts": critical_alerts,
        "ai_recommendation_summary": str(raw.get("ai_recommendation_summary", "") or "").strip(),
        "commercial_estimate": commercial_estimate,
        "supplier_reliability": _supplier_reliability(supplier_score),
        "margin_potential": margin_potential,
        "language": language,
        "commercial_potential_rating": _clamp_rating(raw.get("commercial_potential_rating")),
        "commercial_potential_explanation": str(
            raw.get("commercial_potential_explanation", "") or ""
        ).strip(),
        "import_decision_explanation": str(raw.get("import_decision_explanation", "") or "").strip(),
        "market_comparisons": _normalize_market_comparisons(raw),
        "demand_level": _normalize_demand_level(raw.get("demand_level")),
        "demand_explanation": str(raw.get("demand_explanation", "") or "").strip(),
        "quick_report": [str(item) for item in (raw.get("quick_report") or [])],
    }

    # Résumé compact sur une ligne, calculé STRICTEMENT côté serveur (jamais par l'IA),
    # destiné au futur affichage dans une bulle flottante mobile
    # (voir docs/mobile_architecture.md, section 5). Toujours recalculé ici pour que
    # TOUTES les analyses (texte/image/URL/multi-captures) en bénéficient automatiquement,
    # puisque `analyze_multi_capture()` réutilise cette même fonction de normalisation.
    result["mobile_summary"] = (
        f"{recommendation} — {final_score}/100 — "
        f"{warnings[0] if warnings else _strings(language)['no_major_risk_detected']}"
    )

    # decision_badge, risk_level et import_decision ne sont PAS calculés ici : ils dépendent de
    # "recommendation"/"warnings", qui peuvent encore être modifiés par
    # `_apply_local_safety_net()` (ex: un "BUY" rétrogradé en "CAUTION" suite à un mot-clé piège
    # détecté localement). Les calculer ici risquerait un badge incohérent avec la
    # recommandation finalement affichée. Voir `_apply_local_safety_net()`, qui les calcule en
    # tout dernier, sur l'état définitif.
    result["decision_badge"] = "caution"
    result["risk_level"] = "medium"
    result["import_decision"] = "study"

    return result


def _apply_local_safety_net(result: dict, raw_text: str, language: str = DEFAULT_LANGUAGE) -> dict:
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
    en tant qu'expression `result = _apply_local_safety_net(result, raw_text, language)`).
    """
    language = language if language in _VALID_LANGUAGES else DEFAULT_LANGUAGE
    s = _strings(language)
    local_traps = detect_trap_keywords(raw_text)

    existing_warnings_blob = " ".join(result["warnings"]).lower()
    for trap in local_traps:
        if trap not in existing_warnings_blob:
            result["warnings"].append(s["trap_warning"](trap))

    if local_traps and result["recommendation"] == "BUY":
        result["recommendation"] = "CAUTION"
        result["warnings"].append(s["recommendation_downgraded"])

    # Calculés en tout dernier, sur l'état définitif de "recommendation"/"warnings"
    # (potentiellement modifiés ci-dessus) : voir la note dans `_normalize_ai_result()`.
    result["risk_level"] = _risk_level(
        result["warnings"],
        result["confidence_risks"],
        result["critical_alerts"],
        result["recommendation"],
    )
    result["decision_badge"] = _decision_badge(
        result["final_score"],
        result["recommendation"],
        result["confidence_level"],
        result["critical_alerts"],
    )
    result["import_decision"] = _import_decision(
        result["decision_badge"],
        result["margin_potential"],
        result["commercial_potential_rating"],
        result["critical_alerts"],
    )

    return result


def analyze_product_text(raw_text: str, language: str = DEFAULT_LANGUAGE) -> dict:
    """
    Analyse un texte produit brut (titre/description, toute langue source) :
    1. Détection locale de mots-clés pièges (filet de sécurité).
    2. Appel à l'IA Mistral pour l'analyse complète, la traduction et la génération du
       rapport dans la langue cible `language` ("fr"/"en", choisie par l'utilisateur — voir
       le sélecteur frontend et l'en-tête HTTP X-Language).
    3. Fusion : les pièges détectés localement sont ajoutés aux warnings
       si l'IA ne les a pas explicitement mentionnés.
    """
    language = language if language in _VALID_LANGUAGES else DEFAULT_LANGUAGE
    try:
        user_prompt = build_user_prompt_for_text_analysis(raw_text)
        raw_result = mistral_client.chat_completion_json(
            system_prompt=build_system_prompt(language),
            user_prompt=user_prompt,
        )
        result = _normalize_ai_result(raw_result, language)

    except MistralAPIError as exc:
        logger.error("Échec analyse IA, fallback local activé: %s", exc)
        # deepcopy (pas dict()) : _fallback_result() contient des listes/dicts imbriqués —
        # un simple dict() superficiel laisserait `_apply_local_safety_net()` muter (ex:
        # result["warnings"].append(...)) un objet potentiellement partagé.
        result = copy.deepcopy(_fallback_result(language))
        result["product_name"] = raw_text[:120]

    return _apply_local_safety_net(result, raw_text, language)

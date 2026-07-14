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
from ai_engine.services.timing import StepTimer, log_step

logger = logging.getLogger(__name__)

_VALID_DEMAND_LEVELS = ("very_high", "high", "medium", "low", "very_low")
_VALID_COMPETITION_LEVELS = ("low", "medium", "high", "very_high")
_VALID_MARKET_POSITIONING = ("premium", "mid_range", "entry_level", "saturated", "unknown")
_VALID_LANGUAGES = ("fr", "en")
_MAX_DECISION_REASONS = 5

# --- v1.3 : listes fermées de valeurs enum acceptées ---
_VALID_REVIEW_SATISFACTION = ("very_high", "high", "medium", "low", "very_low")
_VALID_TARGET_AUDIENCES = (
    "students", "children", "professionals", "gamers", "women", "men",
    "gifts", "luxury", "daily_use", "other",
)
_VALID_SATURATION_LEVELS = ("low", "competitive", "saturated", "extremely_saturated")
_VALID_TRANSPORT = ("air", "sea", "mixed")
_VALID_IMPORT_DIFFICULTY = ("very_easy", "easy", "medium", "hard")
# supplier_profile.overall_trust est TOUJOURS recalculé côté serveur à partir de
# _supplier_reliability() (yes/medium/no), jamais lu depuis la réponse IA brute.
_OVERALL_TRUST_MAP = {"yes": "high", "medium": "medium", "no": "low"}
_MAX_REVIEW_ITEMS = 4
_MAX_COMPLEMENTARY_PRODUCTS = 6
_MAX_IMPORTER_SUMMARY = 8
# Si une contradiction factuelle avérée existe, le potentiel "produit gagnant" ne peut pas être
# élevé, quels que soient les autres facteurs (règle également imposée à l'IA dans le prompt,
# mais jamais fait confiance à elle seule — voir RÈGLE ABSOLUE ailleurs dans ce module).
_WINNING_SCORE_CAP_WITH_CRITICAL_ALERTS = 3

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
        "fallback_decision_reasons": ["analyse IA indisponible"],
        "fallback_winning_product_explanation": (
            "Analyse IA indisponible : score produit gagnant non évaluable pour le moment."
        ),
        "fallback_competition_explanation": (
            "Analyse IA indisponible : niveau de concurrence non évaluable pour le moment."
        ),
        "fallback_market_positioning_explanation": (
            "Analyse IA indisponible : positionnement marché non évaluable pour le moment."
        ),
        "fallback_resale_ease_explanation": (
            "Analyse IA indisponible : facilité de revente non évaluable pour le moment."
        ),
        "fallback_target_audience_explanation": (
            "Analyse IA indisponible : public cible non évaluable pour le moment."
        ),
        "fallback_saturation_explanation": (
            "Analyse IA indisponible : niveau de saturation non évaluable pour le moment."
        ),
        "fallback_transport_explanation": (
            "Analyse IA indisponible : mode de transport recommandé non évaluable pour le moment."
        ),
        "fallback_import_difficulty_explanation": (
            "Analyse IA indisponible : difficulté d'importation non évaluable pour le moment."
        ),
        "fallback_importer_summary": ["⚠ Analyse IA indisponible pour le moment."],
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
        "fallback_decision_reasons": ["AI analysis unavailable"],
        "fallback_winning_product_explanation": (
            "AI analysis unavailable: winning product score cannot be evaluated right now."
        ),
        "fallback_competition_explanation": (
            "AI analysis unavailable: competition level cannot be evaluated right now."
        ),
        "fallback_market_positioning_explanation": (
            "AI analysis unavailable: market positioning cannot be evaluated right now."
        ),
        "fallback_resale_ease_explanation": (
            "AI analysis unavailable: resale ease cannot be evaluated right now."
        ),
        "fallback_target_audience_explanation": (
            "AI analysis unavailable: target audience cannot be evaluated right now."
        ),
        "fallback_saturation_explanation": (
            "AI analysis unavailable: saturation level cannot be evaluated right now."
        ),
        "fallback_transport_explanation": (
            "AI analysis unavailable: recommended transport cannot be evaluated right now."
        ),
        "fallback_import_difficulty_explanation": (
            "AI analysis unavailable: import difficulty cannot be evaluated right now."
        ),
        "fallback_importer_summary": ["⚠ AI analysis temporarily unavailable."],
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
            "purchase_price_cny": None,
            "estimated_transport_cny": None,
            "estimated_customs_cny": None,
            "misc_fees_cny": None,
            "suggested_resale_price_fcfa": None,
            "landed_cost_fcfa": None,
            "estimated_profit_fcfa": None,
            "margin_percentage": None,
            "roi_percentage": None,
            "commercial_potential": "low",
            "purchase_price_eur": None,
            "estimated_transport_eur": None,
            "estimated_customs_eur": None,
            "suggested_resale_price_eur": None,
            "landed_cost_eur": None,
            "estimated_profit_eur": None,
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
        "decision_reasons": list(s["fallback_decision_reasons"]),
        "winning_product_score": 0,
        "winning_product_explanation": s["fallback_winning_product_explanation"],
        "competition_level": "medium",
        "competition_explanation": s["fallback_competition_explanation"],
        "data_confidence": {"price": 0, "specifications": 0, "photos": 0, "reviews": 0, "ocr": 0},
        "average_market_price": None,
        "market_positioning": "unknown",
        "market_positioning_explanation": s["fallback_market_positioning_explanation"],
        "resale_ease_rating": 1,
        "resale_ease_explanation": s["fallback_resale_ease_explanation"],
        # --- v1.3 : valeurs neutres localisées (aucune donnée exploitable sans IA) ---
        "reviews_available": False,
        "review_highlights": [],
        "review_complaints": [],
        "review_recurring_defects": [],
        "review_satisfaction": "medium",
        # overall_trust "low" cohérent avec supplier_reliability "no" ci-dessus.
        "supplier_profile": {
            "estimated_age": None,
            "sales_volume": None,
            "reputation": "",
            "service_quality": "",
            "shipping_speed": "",
            "return_policy": "",
            "dispute_history": None,
            "overall_trust": "low",
        },
        "target_audiences": [],
        "target_audience_explanation": s["fallback_target_audience_explanation"],
        "import_strategy": {
            "suggested_initial_quantity": "",
            "quantity_reason": "",
            "sales_tips": "",
            "launch_strategy": "",
        },
        "seasonality": {
            "is_seasonal": False,
            "ideal_period": None,
            "favorable_months": [],
            "unfavorable_months": [],
        },
        "saturation_level": "competitive",
        "saturation_explanation": s["fallback_saturation_explanation"],
        "complementary_products": [],
        "logistics_profile": {
            "fragile": False,
            "heavy": False,
            "bulky": False,
            "liquid": False,
            "has_battery": False,
            "textile": False,
            "electronic": False,
        },
        "recommended_transport": "air",
        "transport_explanation": s["fallback_transport_explanation"],
        "import_difficulty": "medium",
        "import_difficulty_explanation": s["fallback_import_difficulty_explanation"],
        "marketing_claims": [],
        "importer_summary": list(s["fallback_importer_summary"]),
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


def _normalize_enum(raw_value, valid_values: tuple[str, ...], default: str) -> str:
    """Normalise une valeur enum : la retourne si elle appartient à `valid_values`
    (après strip/lower), sinon retombe sur `default`. Helper unique partagé par tous les
    champs enum (demande, concurrence, positionnement, satisfaction, saturation, transport,
    difficulté d'import...)."""
    value = str(raw_value or "").strip().lower()
    return value if value in valid_values else default


# Wrappers nommés conservés pour compatibilité (importés tels quels par les tests et par
# multi_capture_service) — ils délèguent désormais au helper générique _normalize_enum().
def _normalize_demand_level(raw_value) -> str:
    return _normalize_enum(raw_value, _VALID_DEMAND_LEVELS, "medium")


def _normalize_competition_level(raw_value) -> str:
    return _normalize_enum(raw_value, _VALID_COMPETITION_LEVELS, "medium")


def _normalize_market_positioning(raw_value) -> str:
    return _normalize_enum(raw_value, _VALID_MARKET_POSITIONING, "unknown")


def _normalize_decision_reasons(raw: dict) -> list[str]:
    items = raw.get("decision_reasons")
    if not isinstance(items, list):
        return []
    return [str(item).strip() for item in items if str(item).strip()][:_MAX_DECISION_REASONS]


def _clamp_winning_score(value) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 5
    return max(0, min(10, v))


def _normalize_data_confidence(raw: dict) -> dict:
    def _clamp_pct(value) -> int:
        try:
            v = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(100, v))

    raw_confidence = raw.get("data_confidence")
    if not isinstance(raw_confidence, dict):
        raw_confidence = {}
    return {
        "price": _clamp_pct(raw_confidence.get("price")),
        "specifications": _clamp_pct(raw_confidence.get("specifications")),
        "photos": _clamp_pct(raw_confidence.get("photos")),
        "reviews": _clamp_pct(raw_confidence.get("reviews")),
        "ocr": _clamp_pct(raw_confidence.get("ocr")),
    }


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


# ---------------------------------------------------------------------------
# v1.3 : coercition de types + normalisation des sous-objets IA
# ---------------------------------------------------------------------------

def _coerce_str(value) -> str:
    return str(value or "").strip()


def _coerce_str_or_none(value):
    """String nettoyée, ou None si vide/absente (pour les champs `str | None`)."""
    text = str(value or "").strip()
    return text or None


def _coerce_bool(value) -> bool:
    """Booléen tolérant : accepte les vrais bool, ainsi que les chaînes IA usuelles
    ("true"/"yes"/"oui"/"1") — l'IA renvoie parfois un booléen sous forme de texte."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "oui", "1")
    return bool(value)


def _coerce_str_list(value, max_items: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:max_items] if max_items is not None else items


# Spécification {clé: type} des sous-objets à champs "plats" (string / string|None / booléen).
# La saisonnalité est traitée à part (_normalize_seasonality) car elle contient des listes et
# une règle de cohérence (mois vides si non saisonnier).
_STR = "str"
_STR_OR_NONE = "str_or_none"
_BOOL = "bool"
_COERCERS = {_STR: _coerce_str, _STR_OR_NONE: _coerce_str_or_none, _BOOL: _coerce_bool}

_SUPPLIER_PROFILE_SPEC = {
    "estimated_age": _STR_OR_NONE,
    "sales_volume": _STR_OR_NONE,
    "reputation": _STR,
    "service_quality": _STR,
    "shipping_speed": _STR,
    "return_policy": _STR,
    "dispute_history": _STR_OR_NONE,
}
_IMPORT_STRATEGY_SPEC = {
    "suggested_initial_quantity": _STR,
    "quantity_reason": _STR,
    "sales_tips": _STR,
    "launch_strategy": _STR,
}
_LOGISTICS_PROFILE_SPEC = {
    "fragile": _BOOL,
    "heavy": _BOOL,
    "bulky": _BOOL,
    "liquid": _BOOL,
    "has_battery": _BOOL,
    "textile": _BOOL,
    "electronic": _BOOL,
}


def _normalize_submodel(raw: dict, key: str, spec: dict) -> dict:
    """Normalise un sous-objet IA à champs plats à partir d'une spec {clé: type}, avec un
    défaut sûr par clé et en ignorant toute clé superflue renvoyée par l'IA."""
    obj = raw.get(key)
    if not isinstance(obj, dict):
        obj = {}
    return {field: _COERCERS[kind](obj.get(field)) for field, kind in spec.items()}


def _normalize_seasonality(raw: dict) -> dict:
    obj = raw.get("seasonality")
    if not isinstance(obj, dict):
        obj = {}
    is_seasonal = _coerce_bool(obj.get("is_seasonal"))
    favorable = _coerce_str_list(obj.get("favorable_months"))
    unfavorable = _coerce_str_list(obj.get("unfavorable_months"))
    ideal_period = _coerce_str_or_none(obj.get("ideal_period"))
    # Cohérence : sans saisonnalité, aucun mois ne doit être renseigné (pas d'hallucination).
    if not is_seasonal:
        favorable = []
        unfavorable = []
    return {
        "is_seasonal": is_seasonal,
        "ideal_period": ideal_period,
        "favorable_months": favorable,
        "unfavorable_months": unfavorable,
    }


def _normalize_target_audiences(raw: dict) -> list[str]:
    """Sous-ensemble filtré de _VALID_TARGET_AUDIENCES (retire toute valeur hors liste et les
    doublons, en préservant l'ordre de l'IA)."""
    items = raw.get("target_audiences")
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        value = str(item or "").strip().lower()
        if value in _VALID_TARGET_AUDIENCES and value not in result:
            result.append(value)
    return result


def _normalize_marketing_claims(raw: dict) -> list[dict]:
    """Liste d'objets {claim, justified, explanation}. Ignore les items sans "claim" concret
    (l'IA ne doit signaler que des termes réellement présents — liste vide sinon)."""
    items = raw.get("marketing_claims")
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", "")).strip()
        if not claim:
            continue
        result.append(
            {
                "claim": claim,
                "justified": _coerce_bool(item.get("justified")),
                "explanation": str(item.get("explanation", "")).strip(),
            }
        )
    return result


def _normalize_commercial_estimate(raw: dict, profit_score: int, language: str) -> tuple[dict, str]:
    """
    Normalise l'estimation commerciale/financière. L'IA ne fournit que des montants "input" :
    - Pipeline PRIMAIRE (yuan -> FCFA, public cible africain) : purchase_price_cny,
      estimated_transport_cny, estimated_customs_cny, misc_fees_cny, suggested_resale_price_fcfa.
    - Pipeline SECONDAIRE (euro, repli v1.1) : purchase_price_eur, estimated_transport_eur,
      estimated_customs_eur, suggested_resale_price_eur.
    TOUTE l'arithmétique dérivée (coût rendu, bénéfice, marge %, ROI, conversion FCFA) est
    calculée ici, jamais par l'IA. Les deux pipelines sont calculés indépendamment quand leurs
    données sont disponibles (aucun n'écrase l'autre) ; si le pipeline yuan n'a pas assez de
    données, le pipeline euro sert de repli pour peupler les champs FCFA (conversion via la
    parité fixe réelle EUR/XOF) afin que la carte "Calculateur Import" reste renseignée.

    Retourne (commercial_estimate_dict, margin_potential). "margin_potential" est dérivé de
    margin_percentage (priorité au calcul yuan, plus réaliste que le calcul euro) quand une marge
    concrète est calculable (seuils réels réutilisés de app.services.import_estimate_service, la
    même règle métier que le calculateur d'import manuel) ; sinon repli sur le score de profit IA
    (mêmes seuils que ScoreBadge.jsx : 70/40).
    """
    raw_estimate = raw.get("commercial_estimate")
    if not isinstance(raw_estimate, dict):
        raw_estimate = {}

    # --- Pipeline primaire : yuan (source réelle des plateformes chinoises) -> FCFA ---
    purchase_cny = _clamp_optional_float(raw_estimate.get("purchase_price_cny"))
    transport_cny = _clamp_optional_float(raw_estimate.get("estimated_transport_cny"))
    customs_cny = _clamp_optional_float(raw_estimate.get("estimated_customs_cny"))
    misc_cny = _clamp_optional_float(raw_estimate.get("misc_fees_cny"))
    resale_fcfa = _clamp_optional_float(raw_estimate.get("suggested_resale_price_fcfa"))

    # --- Pipeline secondaire : euro (repli v1.1) ---
    purchase_eur = _clamp_optional_float(raw_estimate.get("purchase_price_eur"))
    transport_eur = _clamp_optional_float(raw_estimate.get("estimated_transport_eur"))
    customs_eur = _clamp_optional_float(raw_estimate.get("estimated_customs_eur"))
    resale_eur = _clamp_optional_float(raw_estimate.get("suggested_resale_price_eur"))

    reason_if_not_possible = raw_estimate.get("reason_if_not_possible") or None
    ai_says_possible = bool(raw_estimate.get("possible", False))
    possible_cny = ai_says_possible and purchase_cny is not None
    possible_eur = ai_says_possible and purchase_eur is not None
    possible = possible_cny or possible_eur

    landed_cost_fcfa = None
    profit_fcfa = None
    margin_pct_cny = None
    landed_cost_eur = None
    profit_eur = None
    margin_pct_eur = None
    roi_pct = None

    if possible_cny:
        landed_cost_fcfa = (
            purchase_cny + (transport_cny or 0.0) + (customs_cny or 0.0) + (misc_cny or 0.0)
        ) * settings.IMPORT_CNY_XOF_RATE
        if resale_fcfa is not None and resale_fcfa > 0:
            profit_fcfa_float = resale_fcfa - landed_cost_fcfa
            profit_fcfa = round(profit_fcfa_float)
            margin_pct_cny = (profit_fcfa_float / resale_fcfa) * 100
            if landed_cost_fcfa > 0:
                roi_pct = (profit_fcfa_float / landed_cost_fcfa) * 100

    if possible_eur:
        landed_cost_eur = purchase_eur + (transport_eur or 0.0) + (customs_eur or 0.0)
        if resale_eur is not None and resale_eur > 0:
            profit_eur = resale_eur - landed_cost_eur
            margin_pct_eur = (profit_eur / resale_eur) * 100

    # Repli : si le pipeline yuan n'a pas produit de chiffres FCFA exploitables, utiliser le
    # pipeline euro converti via la parité fixe réelle EUR/XOF (comportement v1.1 conservé).
    if landed_cost_fcfa is None and landed_cost_eur is not None:
        landed_cost_fcfa = landed_cost_eur * settings.IMPORT_EUR_XOF_RATE
    if profit_fcfa is None and profit_eur is not None:
        profit_fcfa = round(profit_eur * settings.IMPORT_EUR_XOF_RATE)
        if roi_pct is None and landed_cost_eur:
            roi_pct = (profit_eur / landed_cost_eur) * 100

    margin_pct = margin_pct_cny if margin_pct_cny is not None else margin_pct_eur
    margin_potential = _margin_potential(profit_score)  # repli par défaut
    if margin_pct is not None:
        if margin_pct >= MARGIN_THRESHOLD_BUY_PCT:
            margin_potential = "high"
        elif margin_pct < MARGIN_THRESHOLD_AVOID_PCT:
            margin_potential = "low"
        else:
            margin_potential = "medium"

    if not possible:
        purchase_cny = transport_cny = customs_cny = misc_cny = resale_fcfa = None
        purchase_eur = transport_eur = customs_eur = resale_eur = None
        reason_if_not_possible = reason_if_not_possible or _strings(language)["insufficient_price_data"]

    return (
        {
            "possible": possible,
            "reason_if_not_possible": reason_if_not_possible,
            "purchase_price_cny": round(purchase_cny, 2) if purchase_cny is not None else None,
            "estimated_transport_cny": round(transport_cny, 2) if transport_cny is not None else None,
            "estimated_customs_cny": round(customs_cny, 2) if customs_cny is not None else None,
            "misc_fees_cny": round(misc_cny, 2) if misc_cny is not None else None,
            "suggested_resale_price_fcfa": round(resale_fcfa, 2) if resale_fcfa is not None else None,
            "landed_cost_fcfa": round(landed_cost_fcfa, 2) if landed_cost_fcfa is not None else None,
            "estimated_profit_fcfa": profit_fcfa,
            "margin_percentage": round(margin_pct, 2) if margin_pct is not None else None,
            "roi_percentage": round(roi_pct, 2) if roi_pct is not None else None,
            "commercial_potential": margin_potential,
            "purchase_price_eur": round(purchase_eur, 2) if purchase_eur is not None else None,
            "estimated_transport_eur": round(transport_eur, 2) if transport_eur is not None else None,
            "estimated_customs_eur": round(customs_eur, 2) if customs_eur is not None else None,
            "suggested_resale_price_eur": round(resale_eur, 2) if resale_eur is not None else None,
            "landed_cost_eur": round(landed_cost_eur, 2) if landed_cost_eur is not None else None,
            "estimated_profit_eur": round(profit_eur, 2) if profit_eur is not None else None,
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
        "decision_reasons": _normalize_decision_reasons(raw),
        "winning_product_score": _clamp_winning_score(raw.get("winning_product_score")),
        "winning_product_explanation": str(raw.get("winning_product_explanation", "") or "").strip(),
        "competition_level": _normalize_competition_level(raw.get("competition_level")),
        "competition_explanation": str(raw.get("competition_explanation", "") or "").strip(),
        "data_confidence": _normalize_data_confidence(raw),
        "average_market_price": (str(raw.get("average_market_price")).strip() or None)
        if raw.get("average_market_price")
        else None,
        "market_positioning": _normalize_market_positioning(raw.get("market_positioning")),
        "market_positioning_explanation": str(
            raw.get("market_positioning_explanation", "") or ""
        ).strip(),
        "resale_ease_rating": _clamp_rating(raw.get("resale_ease_rating")),
        "resale_ease_explanation": str(raw.get("resale_ease_explanation", "") or "").strip(),
        # --- v1.3 : avis clients, profil vendeur, public cible, stratégie, saisonnalité,
        # saturation, produits complémentaires, logistique, difficulté d'import, marketing ---
        "reviews_available": _coerce_bool(raw.get("reviews_available")),
        "review_highlights": _coerce_str_list(raw.get("review_highlights"), _MAX_REVIEW_ITEMS),
        "review_complaints": _coerce_str_list(raw.get("review_complaints"), _MAX_REVIEW_ITEMS),
        "review_recurring_defects": _coerce_str_list(
            raw.get("review_recurring_defects"), _MAX_REVIEW_ITEMS
        ),
        "review_satisfaction": _normalize_enum(
            raw.get("review_satisfaction"), _VALID_REVIEW_SATISFACTION, "medium"
        ),
        # supplier_profile.overall_trust est écrasé côté serveur juste après (voir plus bas).
        "supplier_profile": _normalize_submodel(raw, "supplier_profile", _SUPPLIER_PROFILE_SPEC),
        "target_audiences": _normalize_target_audiences(raw),
        "target_audience_explanation": str(
            raw.get("target_audience_explanation", "") or ""
        ).strip(),
        "import_strategy": _normalize_submodel(raw, "import_strategy", _IMPORT_STRATEGY_SPEC),
        "seasonality": _normalize_seasonality(raw),
        "saturation_level": _normalize_enum(
            raw.get("saturation_level"), _VALID_SATURATION_LEVELS, "competitive"
        ),
        "saturation_explanation": str(raw.get("saturation_explanation", "") or "").strip(),
        "complementary_products": _coerce_str_list(
            raw.get("complementary_products"), _MAX_COMPLEMENTARY_PRODUCTS
        ),
        "logistics_profile": _normalize_submodel(raw, "logistics_profile", _LOGISTICS_PROFILE_SPEC),
        "recommended_transport": _normalize_enum(
            raw.get("recommended_transport"), _VALID_TRANSPORT, "air"
        ),
        "transport_explanation": str(raw.get("transport_explanation", "") or "").strip(),
        "import_difficulty": _normalize_enum(
            raw.get("import_difficulty"), _VALID_IMPORT_DIFFICULTY, "medium"
        ),
        "import_difficulty_explanation": str(
            raw.get("import_difficulty_explanation", "") or ""
        ).strip(),
        "marketing_claims": _normalize_marketing_claims(raw),
        "importer_summary": _coerce_str_list(raw.get("importer_summary"), _MAX_IMPORTER_SUMMARY),
    }

    # supplier_profile.overall_trust : TOUJOURS calculé côté serveur à partir de
    # "supplier_reliability" déjà déterminé (yes/medium/no), jamais lu depuis la réponse IA
    # brute — même principe déterministe que confidence_level. La spec de _normalize_submodel
    # omet volontairement overall_trust pour que la valeur IA soit ignorée puis écrasée ici.
    result["supplier_profile"]["overall_trust"] = _OVERALL_TRUST_MAP[result["supplier_reliability"]]

    # Garde-fou serveur (même esprit que le nettoyage des mois de "seasonality") : si l'IA
    # indique qu'aucun avis n'est disponible, on ne fait pas confiance à elle seule pour avoir
    # respecté la consigne de laisser les listes vides — on les force ici.
    if not result["reviews_available"]:
        result["review_highlights"] = []
        result["review_complaints"] = []
        result["review_recurring_defects"] = []

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

    # Garde-fou serveur (ne fait jamais confiance uniquement à l'instruction prompt) : une
    # contradiction factuelle avérée plafonne le potentiel "produit gagnant", quel que soit le
    # score renvoyé par l'IA.
    if result["critical_alerts"] and result["winning_product_score"] > _WINNING_SCORE_CAP_WITH_CRITICAL_ALERTS:
        result["winning_product_score"] = _WINNING_SCORE_CAP_WITH_CRITICAL_ALERTS

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
        prompt_timer = StepTimer()
        user_prompt = build_user_prompt_for_text_analysis(raw_text)
        system_prompt = build_system_prompt(language)
        log_step(
            "prompt_build",
            prompt_timer.elapsed(),
            system_chars=len(system_prompt),
            user_chars=len(user_prompt),
        )
        raw_result = mistral_client.chat_completion_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        normalize_timer = StepTimer()
        result = _normalize_ai_result(raw_result, language)
        log_step("normalize", normalize_timer.elapsed())

    except MistralAPIError as exc:
        # Log explicite AVANT le repli, avec le type d'exception d'origine (souvent la vraie
        # piste de diagnostic : clé absente, timeout réseau, statut HTTP, JSON non parsable —
        # voir MistralClient.chat_completion_json() pour le détail de chaque cas).
        logger.error(
            "Échec de l'appel Mistral (analyse texte) — repli local activé. Cause : [%s] %s",
            type(exc).__name__,
            exc,
        )
        # deepcopy (pas dict()) : _fallback_result() contient des listes/dicts imbriqués —
        # un simple dict() superficiel laisserait `_apply_local_safety_net()` muter (ex:
        # result["warnings"].append(...)) un objet potentiellement partagé.
        result = copy.deepcopy(_fallback_result(language))
        result["product_name"] = raw_text[:120]

    return _apply_local_safety_net(result, raw_text, language)

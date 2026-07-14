"""
Tests unitaires : service d'analyse produit, en particulier la détection
locale de mots-clés pièges (filet de sécurité indépendant de l'IA) et le
rapport de décision enrichi (badge, risque, fiabilité, marge, estimation
commerciale) toujours calculé côté serveur, jamais délégué à l'IA.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[2]))

from ai_engine.services.mistral_client import MistralAPIError
from ai_engine.services.product_analysis_service import (
    _clamp_winning_score,
    _coerce_bool,
    _coerce_str_list,
    _decision_badge,
    _import_decision,
    _margin_potential,
    _normalize_commercial_estimate,
    _normalize_competition_level,
    _normalize_data_confidence,
    _normalize_decision_reasons,
    _normalize_enum,
    _normalize_market_positioning,
    _normalize_marketing_claims,
    _normalize_seasonality,
    _normalize_submodel,
    _normalize_target_audiences,
    _risk_level,
    _supplier_reliability,
    analyze_product_text,
    detect_trap_keywords,
)


def test_detect_case_only():
    text = "Cooltech CP25 protective case only"
    found = detect_trap_keywords(text)
    assert "case only" in found
    assert "only" in found


def test_detect_no_battery():
    text = "Replacement battery pack, no battery included"
    found = detect_trap_keywords(text)
    assert "no battery included" in found


def test_detect_without_charger():
    text = "USB-C fast charging cable without charger"
    found = detect_trap_keywords(text)
    assert "without charger" in found


def test_no_false_positive_on_clean_text():
    text = "Complete wireless earbuds set with charging case and cable included"
    found = detect_trap_keywords(text)
    # "case" seul ne doit pas matcher "case only"
    assert "case only" not in found


def test_detect_replacement_part():
    text = "iPhone 13 screen replacement part, DIY repair kit"
    found = detect_trap_keywords(text)
    assert "replacement part" in found


def test_detect_accessory_only():
    text = "Car phone holder accessory only, phone not included"
    found = detect_trap_keywords(text)
    assert "accessory only" in found


# ---------------------------------------------------------------------------
# _supplier_reliability() / _margin_potential() : mêmes seuils que ScoreBadge.jsx (70/40)
# ---------------------------------------------------------------------------


def test_supplier_reliability_thresholds():
    assert _supplier_reliability(70) == "yes"
    assert _supplier_reliability(69) == "medium"
    assert _supplier_reliability(40) == "medium"
    assert _supplier_reliability(39) == "no"


def test_margin_potential_thresholds():
    assert _margin_potential(70) == "high"
    assert _margin_potential(69) == "medium"
    assert _margin_potential(40) == "medium"
    assert _margin_potential(39) == "low"


# ---------------------------------------------------------------------------
# _risk_level()
# ---------------------------------------------------------------------------


def test_risk_level_no_signals_is_low():
    assert _risk_level([], [], [], "BUY") == "low"


def test_risk_level_few_signals_is_medium():
    assert _risk_level(["w1"], ["r1"], [], "CAUTION") == "medium"


def test_risk_level_many_signals_is_high():
    assert _risk_level(["w1", "w2"], ["r1", "r2"], [], "CAUTION") == "high"


def test_risk_level_critical_alert_alone_forces_high():
    # Une seule alerte critique (contradiction avérée), sans autre warning, force "high"
    assert _risk_level([], [], ["contradiction"], "CAUTION") == "high"


def test_risk_level_avoid_recommendation_is_always_high():
    assert _risk_level([], [], [], "AVOID") == "high"


# ---------------------------------------------------------------------------
# _decision_badge()
# ---------------------------------------------------------------------------


def test_decision_badge_avoid_recommendation_forces_avoid():
    assert _decision_badge(90, "AVOID", "high", []) == "avoid"


def test_decision_badge_low_score_forces_avoid_even_if_buy():
    assert _decision_badge(20, "BUY", "high", []) == "avoid"


def test_decision_badge_buy_high_score_high_confidence_is_recommended():
    assert _decision_badge(85, "BUY", "high", []) == "recommended"


def test_decision_badge_buy_insufficient_confidence_is_verify_not_recommended():
    # Même avec un score élevé, une confiance insuffisante ne peut pas donner "recommended"
    assert _decision_badge(90, "BUY", "insufficient", []) == "verify"


def test_decision_badge_critical_alert_floors_to_caution():
    # Un score autrement "recommended" est plafonné à "caution" si une contradiction existe
    assert _decision_badge(90, "BUY", "high", ["RTX 5060 annoncé mais HD 7670 détecté"]) == "caution"


def test_decision_badge_caution_recommendation_never_recommended():
    assert _decision_badge(95, "CAUTION", "high", []) == "verify"


def test_decision_badge_caution_low_score_is_caution():
    assert _decision_badge(50, "CAUTION", "high", []) == "caution"


# ---------------------------------------------------------------------------
# _normalize_commercial_estimate() : l'IA ne fournit que 4 montants "input" en euros ;
# toute l'arithmétique dérivée (coût rendu, bénéfice, marge %, FCFA) est calculée ici.
# ---------------------------------------------------------------------------


def test_commercial_estimate_full_data_computes_financial_breakdown():
    raw = {
        "commercial_estimate": {
            "possible": True,
            "purchase_price_eur": 10.0,
            "estimated_transport_eur": 2.0,
            "estimated_customs_eur": 1.0,
            "suggested_resale_price_eur": 26.0,
        }
    }
    result, margin_potential = _normalize_commercial_estimate(raw, profit_score=50, language="fr")
    assert result["possible"] is True
    assert result["landed_cost_eur"] == 13.0
    assert result["estimated_profit_eur"] == 13.0
    # marge = 13/26*100 = 50% -> largement au-dessus du seuil ACHETER (30%) -> "high"
    assert result["margin_percentage"] == 50.0
    assert margin_potential == "high"
    assert result["commercial_potential"] == "high"
    # conversion FCFA au taux fixe réel (655.957) : 13 * 655.957 ≈ 8527
    assert result["estimated_profit_fcfa"] == round(13.0 * 655.957)


def test_commercial_estimate_possible_without_resale_price_skips_profit_only():
    """possible=True dès que purchase_price_eur est fourni ; sans prix de revente, le coût
    rendu reste calculable mais le bénéfice/marge/FCFA restent None (pas de division par zéro)."""
    raw = {"commercial_estimate": {"possible": True, "purchase_price_eur": 10.0}}
    result, _ = _normalize_commercial_estimate(raw, profit_score=50, language="fr")
    assert result["possible"] is True
    assert result["landed_cost_eur"] == 10.0
    assert result["estimated_profit_eur"] is None
    assert result["margin_percentage"] is None
    assert result["estimated_profit_fcfa"] is None


def test_commercial_estimate_possible_true_but_no_purchase_price_is_forced_false():
    raw = {"commercial_estimate": {"possible": True, "suggested_resale_price_eur": 20.0}}
    result, _ = _normalize_commercial_estimate(raw, profit_score=50, language="fr")
    assert result["possible"] is False
    assert result["reason_if_not_possible"]
    assert result["landed_cost_eur"] is None


def test_commercial_estimate_missing_key_defaults_to_not_possible():
    result, margin_potential = _normalize_commercial_estimate({}, profit_score=20, language="fr")
    assert result["possible"] is False
    assert margin_potential == "low"  # repli sur profit_score (mêmes seuils que ScoreBadge.jsx)


def test_commercial_estimate_falls_back_to_profit_score_when_margin_not_computable():
    """Sans marge concrète calculable, margin_potential retombe sur profit_score (70/40)."""
    _, margin_potential = _normalize_commercial_estimate({}, profit_score=75, language="fr")
    assert margin_potential == "high"


def test_commercial_estimate_not_possible_reason_is_localized():
    result_fr, _ = _normalize_commercial_estimate({}, profit_score=0, language="fr")
    result_en, _ = _normalize_commercial_estimate({}, profit_score=0, language="en")
    assert result_fr["reason_if_not_possible"] != result_en["reason_if_not_possible"]
    assert "insuffisantes" in result_fr["reason_if_not_possible"]
    assert "Insufficient" in result_en["reason_if_not_possible"]


# ---------------------------------------------------------------------------
# _import_decision() : carte "Décision Import" dédiée, calculée côté serveur en agrégeant
# des signaux déjà produits (aucun appel IA supplémentaire).
# ---------------------------------------------------------------------------


def test_import_decision_avoid_badge_forces_avoid():
    assert _import_decision("avoid", "high", 5, []) == "avoid"


def test_import_decision_critical_alerts_force_avoid_even_if_recommended():
    assert _import_decision("recommended", "high", 5, ["contradiction"]) == "avoid"


def test_import_decision_recommended_high_margin_good_rating_is_import():
    assert _import_decision("recommended", "high", 4, []) == "import"


def test_import_decision_recommended_low_margin_is_study():
    assert _import_decision("recommended", "low", 5, []) == "study"


def test_import_decision_verify_high_margin_high_rating_is_import():
    assert _import_decision("verify", "high", 4, []) == "import"


def test_import_decision_verify_medium_margin_is_study():
    assert _import_decision("verify", "medium", 3, []) == "study"


def test_import_decision_caution_is_study():
    assert _import_decision("caution", "high", 5, []) == "study"


# ---------------------------------------------------------------------------
# analyze_product_text() : le badge/risque reflètent l'état FINAL (après le filet de
# sécurité local), pas l'état brut renvoyé par l'IA.
# ---------------------------------------------------------------------------


def _raw_ai_result(**overrides):
    base = {
        "product_name": "Produit test",
        "included": [],
        "not_included": [],
        "warnings": [],
        "quality_score": 80,
        "supplier_score": 80,
        "profit_score": 80,
        "final_score": 85,
        "recommendation": "BUY",
        "detected_data": {},
        "ai_estimations": {},
        "missing_information": [],
        "confidence_score": 90,
        "confidence_reasons": [],
        "confidence_risks": [],
        "critical_alerts": [],
        "commercial_estimate": {"possible": False},
        "ai_recommendation_summary": "Produit fiable, achat recommandé.",
    }
    base.update(overrides)
    return base


def test_badge_reflects_downgrade_from_local_trap_keyword_safety_net():
    """
    L'IA renvoie BUY/85 (ce qui donnerait "recommended" isolément), mais le texte source
    contient un mot-clé piège ("case only") que le filet de sécurité local détecte après
    coup, rétrogradant la recommandation en CAUTION. Le badge final doit refléter CAUTION,
    pas rester "recommended" (bug qu'aurait causé un calcul du badge trop tôt).
    """
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result()
        result = analyze_product_text("Cooltech CP25 protective case only")

    assert result["recommendation"] == "CAUTION"
    assert result["decision_badge"] != "recommended"


def test_fallback_result_does_not_leak_warnings_across_calls():
    """
    Reproduit une régression potentielle : `dict(_fallback_result(...))` serait une copie superficielle,
    donc muter result["warnings"] (ajout d'un mot-clé piège) muterait la constante partagée du
    module, faisant grossir indéfiniment les warnings de TOUS les appels de secours suivants.
    Deux appels successifs en échec IA doivent produire le même nombre de warnings.
    """
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.side_effect = MistralAPIError("boom")
        first = analyze_product_text("Cooltech CP25 protective case only")
        second = analyze_product_text("Cooltech CP25 protective case only")

    assert len(second["warnings"]) == len(first["warnings"])


# ---------------------------------------------------------------------------
# Internationalisation (v1.1) : la langue est transmise de bout en bout, y compris pour
# le filet de sécurité local et le repli en cas d'échec IA (jamais un mélange de langues).
# ---------------------------------------------------------------------------


def test_language_is_echoed_back_in_result():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result()
        result = analyze_product_text("Some clean product description", language="en")

    assert result["language"] == "en"


def test_unsupported_language_falls_back_to_french():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result()
        result = analyze_product_text("Some clean product description", language="de")

    assert result["language"] == "fr"


def test_local_trap_warning_is_localized_in_english():
    """Le warning ajouté par le filet de sécurité local (pas par l'IA) doit être en anglais
    quand language="en" — sinon mélange de langues même si l'IA répond correctement en anglais."""
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result()
        result = analyze_product_text("Protective case only, phone not included", language="en")

    trap_warnings = [w for w in result["warnings"] if "case only" in w]
    assert trap_warnings, "expected a trap-keyword warning to be present"
    assert "Risky keyword detected" in trap_warnings[0]
    assert "Mot-clé à risque" not in trap_warnings[0]


def test_fallback_result_is_localized_in_english():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.side_effect = MistralAPIError("boom")
        result = analyze_product_text("Some product text", language="en")

    assert "temporarily unavailable" in result["warnings"][0]
    assert "momentanément indisponible" not in result["warnings"][0]


def test_import_decision_is_set_on_final_result():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result(
            commercial_potential_rating=5
        )
        result = analyze_product_text("Clean product with no risky keywords")

    assert result["import_decision"] in ("import", "study", "avoid")


# ---------------------------------------------------------------------------
# v1.2 : pipeline financier primaire yuan -> FCFA (taux heuristique 1¥=100 FCFA), avec
# repli sur le pipeline euro -> FCFA (parité fixe réelle) quand aucun prix en yuan n'est fourni.
# ---------------------------------------------------------------------------


def test_commercial_estimate_cny_pipeline_computes_fcfa_breakdown_and_roi():
    raw = {
        "commercial_estimate": {
            "possible": True,
            "purchase_price_cny": 50.0,
            "estimated_transport_cny": 10.0,
            "estimated_customs_cny": 5.0,
            "misc_fees_cny": 2.0,
            "suggested_resale_price_fcfa": 10000.0,
        }
    }
    result, margin_potential = _normalize_commercial_estimate(raw, profit_score=50, language="fr")
    # (50+10+5+2) * 100 (taux heuristique) = 6700
    assert result["landed_cost_fcfa"] == 6700.0
    assert result["estimated_profit_fcfa"] == 3300
    assert result["margin_percentage"] == 33.0
    assert round(result["roi_percentage"], 2) == round(3300 / 6700 * 100, 2)
    assert margin_potential == "high"
    # Le pipeline euro n'a reçu aucune donnée : reste vide, sans planter.
    assert result["landed_cost_eur"] is None


def test_commercial_estimate_falls_back_to_eur_when_no_cny_price():
    """Sans prix en yuan mais avec un prix en euros, le calculateur FCFA reste renseigné via
    la parité fixe réelle EUR/XOF (comportement v1.1 conservé en repli)."""
    raw = {
        "commercial_estimate": {
            "possible": True,
            "purchase_price_eur": 10.0,
            "suggested_resale_price_eur": 20.0,
        }
    }
    result, _ = _normalize_commercial_estimate(raw, profit_score=50, language="fr")
    assert result["landed_cost_fcfa"] is not None
    assert result["estimated_profit_fcfa"] is not None
    assert result["purchase_price_cny"] is None


def test_commercial_estimate_both_currencies_computed_independently():
    """Quand l'IA fournit à la fois yuan et euro, les deux pipelines restent disponibles
    (pas d'écrasement) et le calcul FCFA privilégie le pipeline yuan, plus réaliste."""
    raw = {
        "commercial_estimate": {
            "possible": True,
            "purchase_price_cny": 50.0,
            "suggested_resale_price_fcfa": 10000.0,
            "purchase_price_eur": 8.0,
            "suggested_resale_price_eur": 15.0,
        }
    }
    result, _ = _normalize_commercial_estimate(raw, profit_score=50, language="fr")
    assert result["landed_cost_eur"] == 8.0
    assert result["estimated_profit_eur"] == 7.0
    # Le calcul FCFA vient bien du pipeline yuan (50*100=5000), pas du pipeline euro.
    assert result["landed_cost_fcfa"] == 5000.0


# ---------------------------------------------------------------------------
# v1.2 : winning_product_score, decision_reasons, competition_level, market_positioning,
# data_confidence — normalisation et garde-fous serveur.
# ---------------------------------------------------------------------------


def test_clamp_winning_score_bounds():
    assert _clamp_winning_score(15) == 10
    assert _clamp_winning_score(-3) == 0
    assert _clamp_winning_score("7") == 7
    assert _clamp_winning_score(None) == 5


def test_decision_reasons_truncated_to_five():
    raw = {"decision_reasons": ["a", "b", "c", "d", "e", "f", "g"]}
    assert _normalize_decision_reasons(raw) == ["a", "b", "c", "d", "e"]


def test_decision_reasons_missing_key_is_empty_list():
    assert _normalize_decision_reasons({}) == []


def test_normalize_competition_level_invalid_falls_back_to_medium():
    assert _normalize_competition_level("astronomical") == "medium"
    assert _normalize_competition_level("very_high") == "very_high"


def test_normalize_market_positioning_invalid_falls_back_to_unknown():
    assert _normalize_market_positioning("bargain") == "unknown"
    assert _normalize_market_positioning("premium") == "premium"


def test_normalize_data_confidence_clamps_each_category():
    raw = {"data_confidence": {"price": 150, "specifications": -10, "photos": 60, "ocr": "97"}}
    result = _normalize_data_confidence(raw)
    assert result == {"price": 100, "specifications": 0, "photos": 60, "reviews": 0, "ocr": 97}


def test_winning_product_score_capped_when_critical_alert_present():
    """Garde-fou serveur : une contradiction factuelle avérée plafonne le score produit
    gagnant à 3/10, même si l'IA renvoie un score plus élevé (RÈGLE ABSOLUE non fiable seule)."""
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result(
            critical_alerts=["RTX 5060 annoncé mais HD 7670 détecté"],
            winning_product_score=9,
        )
        result = analyze_product_text("Some product text")

    assert result["winning_product_score"] <= 3


def test_winning_product_score_not_capped_without_critical_alerts():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result(winning_product_score=9)
        result = analyze_product_text("Clean product with no risky keywords")

    assert result["winning_product_score"] == 9


# ---------------------------------------------------------------------------
# v1.3 : coercition de types (helpers génériques réutilisés par tous les nouveaux champs)
# ---------------------------------------------------------------------------


def test_coerce_bool_accepts_real_booleans():
    assert _coerce_bool(True) is True
    assert _coerce_bool(False) is False


def test_coerce_bool_accepts_common_ai_string_variants():
    assert _coerce_bool("true") is True
    assert _coerce_bool("Yes") is True
    assert _coerce_bool("oui") is True
    assert _coerce_bool("1") is True
    assert _coerce_bool("false") is False
    assert _coerce_bool("non") is False
    assert _coerce_bool(None) is False


def test_coerce_str_list_truncates_to_max_items():
    assert _coerce_str_list(["a", "b", "c", "d"], max_items=2) == ["a", "b"]


def test_coerce_str_list_filters_empty_strings_and_non_list():
    assert _coerce_str_list(["a", "", "  ", "b"]) == ["a", "b"]
    assert _coerce_str_list("not a list") == []
    assert _coerce_str_list(None) == []


# ---------------------------------------------------------------------------
# v1.3 : _normalize_enum() — refactor générique remplaçant 3 fonctions dupliquées
# (_normalize_demand_level / _normalize_competition_level / _normalize_market_positioning
# délèguent désormais toutes à ce helper).
# ---------------------------------------------------------------------------


def test_normalize_enum_valid_value_is_lowercased():
    assert _normalize_enum("HIGH", ("low", "high"), "low") == "high"


def test_normalize_enum_invalid_value_falls_back_to_default():
    assert _normalize_enum("astronomical", ("low", "high"), "low") == "low"


def test_normalize_enum_missing_value_falls_back_to_default():
    assert _normalize_enum(None, ("low", "high"), "low") == "low"


# ---------------------------------------------------------------------------
# v1.3 : _normalize_submodel() — sous-objets IA à champs plats (SupplierProfile sans
# overall_trust, ImportStrategy, LogisticsProfile).
# ---------------------------------------------------------------------------


def test_normalize_submodel_missing_key_returns_safe_defaults():
    spec = {"reputation": "str", "dispute_history": "str_or_none", "fragile": "bool"}
    result = _normalize_submodel({}, "supplier_profile", spec)
    assert result == {"reputation": "", "dispute_history": None, "fragile": False}


def test_normalize_submodel_ignores_extra_ai_keys():
    spec = {"reputation": "str"}
    raw = {"supplier_profile": {"reputation": "Bonne", "overall_trust": "high"}}
    result = _normalize_submodel(raw, "supplier_profile", spec)
    # "overall_trust" n'est pas dans la spec -> ignoré ici (toujours recalculé côté serveur
    # séparément dans _normalize_ai_result, jamais lu depuis la réponse IA brute).
    assert result == {"reputation": "Bonne"}


# ---------------------------------------------------------------------------
# v1.3 : _normalize_seasonality() — garde-fou anti-hallucination (pas de mois sans saisonnalité)
# ---------------------------------------------------------------------------


def test_seasonality_not_seasonal_clears_months_even_if_ai_provided_them():
    """Garde-fou serveur : si is_seasonal=false, on ne fait pas confiance à l'IA seule pour
    avoir laissé les listes de mois vides (même esprit que le nettoyage des avis)."""
    raw = {
        "seasonality": {
            "is_seasonal": False,
            "favorable_months": ["Décembre"],
            "unfavorable_months": ["Juillet"],
        }
    }
    result = _normalize_seasonality(raw)
    assert result["favorable_months"] == []
    assert result["unfavorable_months"] == []


def test_seasonality_seasonal_keeps_months():
    raw = {
        "seasonality": {
            "is_seasonal": True,
            "ideal_period": "Novembre-Décembre",
            "favorable_months": ["Novembre", "Décembre"],
            "unfavorable_months": ["Juillet"],
        }
    }
    result = _normalize_seasonality(raw)
    assert result["ideal_period"] == "Novembre-Décembre"
    assert result["favorable_months"] == ["Novembre", "Décembre"]


# ---------------------------------------------------------------------------
# v1.3 : _normalize_target_audiences() — liste fermée, dédoublonnée, ordre préservé
# ---------------------------------------------------------------------------


def test_target_audiences_filters_invalid_values():
    raw = {"target_audiences": ["students", "aliens", "gamers"]}
    assert _normalize_target_audiences(raw) == ["students", "gamers"]


def test_target_audiences_deduplicates_preserving_order():
    raw = {"target_audiences": ["gamers", "students", "gamers"]}
    assert _normalize_target_audiences(raw) == ["gamers", "students"]


def test_target_audiences_missing_key_is_empty_list():
    assert _normalize_target_audiences({}) == []


# ---------------------------------------------------------------------------
# v1.3 : _normalize_marketing_claims() — ne signale que des termes réellement présents
# ---------------------------------------------------------------------------


def test_marketing_claims_ignores_items_without_claim_text():
    raw = {"marketing_claims": [{"claim": "", "justified": True}, {"justified": False}]}
    assert _normalize_marketing_claims(raw) == []


def test_marketing_claims_keeps_well_formed_items():
    raw = {
        "marketing_claims": [
            {"claim": "Premium", "justified": False, "explanation": "Aucune preuve dans le texte."}
        ]
    }
    result = _normalize_marketing_claims(raw)
    assert result == [
        {"claim": "Premium", "justified": False, "explanation": "Aucune preuve dans le texte."}
    ]


def test_marketing_claims_ignores_non_dict_items():
    assert _normalize_marketing_claims({"marketing_claims": ["Premium", 42]}) == []


# ---------------------------------------------------------------------------
# v1.3 : supplier_profile.overall_trust — TOUJOURS recalculé côté serveur à partir de
# supplier_reliability (yes/medium/no), jamais lu depuis la réponse IA brute.
# ---------------------------------------------------------------------------


def test_overall_trust_high_when_supplier_score_high():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result(
            supplier_score=90, supplier_profile={"overall_trust": "low"}
        )
        result = analyze_product_text("Clean product with no risky keywords")

    # supplier_score=90 -> _supplier_reliability="yes" -> overall_trust="high", quel que soit
    # ce que l'IA a renvoyé ("low" ci-dessus est ignoré).
    assert result["supplier_profile"]["overall_trust"] == "high"


def test_overall_trust_low_when_supplier_score_low():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result(supplier_score=10)
        result = analyze_product_text("Clean product with no risky keywords")

    assert result["supplier_profile"]["overall_trust"] == "low"


# ---------------------------------------------------------------------------
# v1.3 : reviews_available=False force le nettoyage serveur des listes d'avis (même garde-fou
# que la saisonnalité — ne fait pas confiance à l'IA seule pour respecter la consigne).
# ---------------------------------------------------------------------------


def test_reviews_not_available_clears_review_lists_even_if_ai_provided_them():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result(
            reviews_available=False,
            review_highlights=["Bonne qualité"],
            review_complaints=["Livraison lente"],
            review_recurring_defects=["Casse fréquente"],
        )
        result = analyze_product_text("Clean product with no risky keywords")

    assert result["review_highlights"] == []
    assert result["review_complaints"] == []
    assert result["review_recurring_defects"] == []


def test_reviews_available_keeps_lists():
    with patch("ai_engine.services.product_analysis_service.mistral_client") as mock_mistral:
        mock_mistral.chat_completion_json.return_value = _raw_ai_result(
            reviews_available=True,
            review_highlights=["Bonne qualité"],
        )
        result = analyze_product_text("Clean product with no risky keywords")

    assert result["review_highlights"] == ["Bonne qualité"]

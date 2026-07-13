"""
Tests unitaires : service d'analyse multi-captures
(`ai_engine/services/multi_capture_service.py`).

Couvre :
- classify_capture_category() : un cas par catégorie canonique + cas de repli "other".
- detect_duplicates() : détection par distance de Hamming sur des hashes construits
  directement (imagehash.hex_to_hash), sans dépendre de vraies images.
- analyze_multi_capture() : comportement du pipeline complet, avec mock des 3
  dépendances externes/coûteuses (OCR, pHash, appel Mistral) pour rester 100%
  déterministe et sans réseau. On ne teste jamais l'égalité stricte du dict
  complet retourné (des clés peuvent être ajoutées par d'autres chantiers),
  uniquement des clés précises.
"""
from unittest.mock import patch

import pytest

from ai_engine.services.mistral_client import MistralAPIError
from ai_engine.services.multi_capture_service import (
    CAPTURE_CATEGORIES,
    DUPLICATE_HAMMING_THRESHOLD,
    analyze_multi_capture,
    classify_capture_category,
    detect_duplicates,
)


def _valid_raw_ai_result(recommendation: str = "BUY") -> dict:
    """Réponse IA brute plausible, respectant le contrat attendu par _normalize_ai_result."""
    return {
        "product_name": "Produit test",
        "included": ["câble USB"],
        "not_included": ["batterie"],
        "warnings": [],
        "quality_score": 80,
        "supplier_score": 75,
        "profit_score": 70,
        "final_score": 78,
        "recommendation": recommendation,
        "detected_data": {},
        "ai_estimations": {},
        "missing_information": [],
        "confidence_score": 85,
        "confidence_level": "high",
        "confidence_reasons": [],
        "confidence_risks": [],
    }


@pytest.fixture
def mocked_pipeline():
    """
    Mocke les 3 dépendances externes/coûteuses de `analyze_multi_capture` :
    - extract_text_from_image_bytes (OCR, dépend de tesseract)
    - compute_phash (dépend de PIL sur de vraies images, inutile pour tester la logique)
    - mistral_client.chat_completion_json (appel réseau vers l'API Mistral)
    Retourne les 3 mocks pour permettre à chaque test de configurer side_effect/return_value.
    """
    with (
        patch("ai_engine.services.multi_capture_service.extract_text_from_image_bytes") as mock_extract,
        patch("ai_engine.services.multi_capture_service.compute_phash") as mock_phash,
        patch("ai_engine.services.multi_capture_service.mistral_client") as mock_mistral,
    ):
        mock_mistral.chat_completion_json.return_value = _valid_raw_ai_result()
        yield mock_extract, mock_phash, mock_mistral


# ---------------------------------------------------------------------------
# classify_capture_category()
# ---------------------------------------------------------------------------


def test_classify_main_page():
    text = "Prix incroyable en promotion, vente flash aujourd'hui"
    assert classify_capture_category(text) == "main_page"


def test_classify_product_info():
    text = "Taille et couleur disponibles, matière coton, poids 200g"
    assert classify_capture_category(text) == "product_info"


def test_classify_shop():
    text = "Vendeur fiable, boutique avec bonne ancienneté"
    assert classify_capture_category(text) == "shop"


def test_classify_reviews():
    text = "Avis clients positifs, commentaire élogieux, note client excellente"
    assert classify_capture_category(text) == "reviews"


def test_classify_shipping():
    text = "Livraison rapide, frais de port réduits, délai de expédition 3 jours"
    assert classify_capture_category(text) == "shipping"


def test_classify_empty_text_returns_other():
    assert classify_capture_category("") == "other"


def test_classify_no_known_keyword_returns_other():
    text = "Lorem ipsum dolor sit amet consectetur adipiscing elit"
    assert classify_capture_category(text) == "other"


def test_classify_categories_are_exactly_the_five_canonical():
    assert CAPTURE_CATEGORIES == ["main_page", "product_info", "shop", "reviews", "shipping"]
    assert len(CAPTURE_CATEGORIES) == 5


# ---------------------------------------------------------------------------
# detect_duplicates()
# ---------------------------------------------------------------------------


def test_detect_duplicates_identical_hashes_are_flagged():
    hashes = ["0000000000000000", "0000000000000000"]
    duplicates = detect_duplicates(hashes)
    assert duplicates == {1: 0}


def test_detect_duplicates_very_different_hashes_not_flagged():
    # Distance de Hamming maximale possible (64 bits) entre ces deux hashes.
    hashes = ["0000000000000000", "ffffffffffffffff"]
    duplicates = detect_duplicates(hashes)
    assert duplicates == {}


def test_detect_duplicates_within_threshold_is_flagged():
    # "0000000000000007" ne diffère de "0000000000000000" que de 3 bits (< seuil de 8).
    hashes = ["0000000000000000", "0000000000000007"]
    duplicates = detect_duplicates(hashes)
    assert duplicates == {1: 0}


def test_detect_duplicates_just_above_threshold_not_flagged():
    # "00000000000001ff" diffère de "0000000000000000" de 9 bits (> seuil de 8).
    hashes = ["0000000000000000", "00000000000001ff"]
    duplicates = detect_duplicates(hashes)
    assert duplicates == {}
    assert DUPLICATE_HAMMING_THRESHOLD == 8


def test_detect_duplicates_empty_list():
    assert detect_duplicates([]) == {}


def test_detect_duplicates_chain_of_three_identical():
    hashes = ["0000000000000000", "0000000000000000", "0000000000000000"]
    duplicates = detect_duplicates(hashes)
    # Toutes les occurrences suivantes pointent vers le premier original (index 0).
    assert duplicates == {1: 0, 2: 0}


# ---------------------------------------------------------------------------
# analyze_multi_capture()
# ---------------------------------------------------------------------------


def test_analyze_multi_capture_auto_classification_without_hints(mocked_pipeline):
    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    mock_extract.side_effect = [
        "Prix incroyable en promotion, vente flash aujourd'hui",
        "Taille et couleur disponibles, matière coton, poids 200g",
        "Vendeur fiable, boutique avec bonne ancienneté",
    ]
    # 3 hashes suffisamment différents entre eux pour ne jamais être détectés comme doublons.
    mock_phash.side_effect = ["0000000000000000", "ffffffffffffffff", "00000000000001ff"]

    captures = [
        ("main.png", b"fake-bytes-1"),
        ("info.png", b"fake-bytes-2"),
        ("shop.png", b"fake-bytes-3"),
    ]

    result = analyze_multi_capture(captures, category_hints=None)

    assert [c["category"] for c in result["captures"]] == ["main_page", "product_info", "shop"]
    assert result["categories_covered"] == ["main_page", "product_info", "shop"]
    assert result["categories_missing"] == ["reviews", "shipping"]
    mock_mistral.chat_completion_json.assert_called_once()


def test_analyze_multi_capture_valid_hints_override_auto_classification(mocked_pipeline):
    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    # Texte volontairement sans aucun mot-clé connu : la classification automatique
    # donnerait "other" pour les deux captures si les hints n'étaient pas utilisés.
    mock_extract.side_effect = ["Lorem ipsum dolor sit amet", "Lorem ipsum dolor sit amet consectetur"]
    mock_phash.side_effect = ["0000000000000000", "ffffffffffffffff"]

    captures = [("a.png", b"fake-bytes-a"), ("b.png", b"fake-bytes-b")]

    result = analyze_multi_capture(captures, category_hints=["shipping", "reviews"])

    assert [c["category"] for c in result["captures"]] == ["shipping", "reviews"]
    assert result["categories_covered"] == ["reviews", "shipping"]


def test_analyze_multi_capture_invalid_individual_hint_falls_back_to_auto(mocked_pipeline):
    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    mock_extract.side_effect = ["Prix incroyable en promotion, vente flash aujourd'hui"]
    mock_phash.side_effect = ["0000000000000000"]

    captures = [("main.png", b"fake-bytes-1")]

    # Hint non-canonique -> repli sur la classification automatique pour cette capture.
    result = analyze_multi_capture(captures, category_hints=["not_a_real_category"])

    assert result["captures"][0]["category"] == "main_page"


def test_analyze_multi_capture_hints_length_mismatch_falls_back_to_auto(mocked_pipeline):
    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    mock_extract.side_effect = [
        "Prix incroyable en promotion, vente flash aujourd'hui",
        "Vendeur fiable, boutique avec bonne ancienneté",
    ]
    mock_phash.side_effect = ["0000000000000000", "ffffffffffffffff"]

    captures = [("main.png", b"fake-bytes-1"), ("shop.png", b"fake-bytes-2")]

    # Un seul hint fourni pour 2 captures : longueur incohérente -> classification
    # automatique appliquée à toutes les captures (hints entièrement ignorés).
    result = analyze_multi_capture(captures, category_hints=["shipping"])

    assert [c["category"] for c in result["captures"]] == ["main_page", "shop"]


def test_analyze_multi_capture_duplicate_excluded_from_categories_covered(mocked_pipeline):
    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    mock_extract.side_effect = [
        "Prix incroyable en promotion, vente flash aujourd'hui",
        "Prix incroyable en promotion, vente flash aujourd'hui",
    ]
    # Hash identique -> la 2e capture est détectée comme doublon de la 1ère.
    mock_phash.side_effect = ["0000000000000000", "0000000000000000"]

    captures = [("main1.png", b"fake-bytes-1"), ("main2.png", b"fake-bytes-2")]

    result = analyze_multi_capture(captures, category_hints=None)

    captures_detail = result["captures"]
    assert captures_detail[0]["is_duplicate"] is False
    assert captures_detail[1]["is_duplicate"] is True
    assert captures_detail[1]["duplicate_of_index"] == 0
    # Une seule catégorie couverte malgré 2 captures classées "main_page", car le
    # doublon est exclu de l'agrégation utilisée pour construire categories_covered.
    assert result["categories_covered"] == ["main_page"]


def test_analyze_multi_capture_mistral_failure_uses_local_fallback(mocked_pipeline):
    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    mock_extract.side_effect = ["Prix incroyable en promotion, vente flash aujourd'hui"]
    mock_phash.side_effect = ["0000000000000000"]
    mock_mistral.chat_completion_json.side_effect = MistralAPIError("API indisponible")

    captures = [("main.png", b"fake-bytes-1")]

    result = analyze_multi_capture(captures, category_hints=None)

    # Le filet de sécurité local (_fallback_result()) prend le relais, sans planter.
    assert result["recommendation"] == "CAUTION"
    assert result["confidence_level"] == "insufficient"
    assert result["captures"][0]["category"] == "main_page"
    assert result["categories_covered"] == ["main_page"]


def test_analyze_multi_capture_ocr_failure_is_tolerant(mocked_pipeline):
    """Une capture dont l'OCR échoue ne doit pas faire échouer tout le lot."""
    from ai_engine.services.ocr_service import OCRError

    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    mock_extract.side_effect = [OCRError("échec OCR"), "Vendeur fiable, boutique avec bonne ancienneté"]
    mock_phash.side_effect = ["0000000000000000", "ffffffffffffffff"]

    captures = [("broken.png", b"fake-bytes-1"), ("shop.png", b"fake-bytes-2")]

    result = analyze_multi_capture(captures, category_hints=None)

    captures_detail = result["captures"]
    assert captures_detail[0]["ocr_failed"] is True
    assert captures_detail[0]["ocr_excerpt"] == ""
    assert captures_detail[1]["ocr_failed"] is False
    assert result["categories_covered"] == ["shop"]


def test_ocr_data_confidence_overrides_ai_estimate_with_real_success_ratio(mocked_pipeline):
    """v1.2 : data_confidence["ocr"] doit refléter le taux RÉEL de captures exploitées avec
    succès par l'OCR (donnée déterministe), pas l'estimation IA (qui ne peut que deviner)."""
    from ai_engine.services.ocr_service import OCRError

    mock_extract, mock_phash, mock_mistral = mocked_pipeline
    mock_mistral.chat_completion_json.return_value = {
        **_valid_raw_ai_result(),
        "data_confidence": {"price": 90, "specifications": 80, "photos": 50, "reviews": 70, "ocr": 20},
    }
    # 1 échec sur 4 captures -> taux réel de succès = 75%
    mock_extract.side_effect = ["texte 1", OCRError("échec"), "texte 3", "texte 4"]
    mock_phash.side_effect = ["0000000000000000", "1111111111111111", "2222222222222222", "3333333333333333"]

    captures = [(f"c{i}.png", b"fake-bytes") for i in range(4)]
    result = analyze_multi_capture(captures, category_hints=None)

    assert result["data_confidence"]["ocr"] == 75
    # Les autres catégories de confiance restent celles renvoyées par l'IA, inchangées.
    assert result["data_confidence"]["price"] == 90

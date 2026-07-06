"""
Tests unitaires : service OCR, en particulier le repli automatique sur l'API
OCR Mistral quand le binaire Tesseract local n'est pas disponible (ex. Vercel).
"""
import io
from unittest.mock import patch

import pytesseract
from PIL import Image

from ai_engine.services.mistral_client import MistralAPIError
from ai_engine.services.ocr_service import OCRError, extract_text_from_image_bytes


def _fake_image_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_tesseract_success_path_does_not_call_mistral_ocr():
    """Quand Tesseract fonctionne, le texte est retourné tel quel et l'API Mistral OCR n'est jamais appelée."""
    with patch("pytesseract.image_to_string", return_value="Prix: 39.9 EUR") as mock_tesseract, \
         patch("ai_engine.services.ocr_service.mistral_client") as mock_client:
        text = extract_text_from_image_bytes(_fake_image_bytes())

    assert text == "Prix: 39.9 EUR"
    mock_tesseract.assert_called_once()
    mock_client.ocr_extract_text.assert_not_called()


def test_tesseract_not_found_falls_back_to_mistral_ocr():
    """Si le binaire Tesseract est absent, le texte vient de l'API OCR Mistral."""
    with patch("pytesseract.image_to_string", side_effect=pytesseract.TesseractNotFoundError()), \
         patch("ai_engine.services.ocr_service.mistral_client") as mock_client:
        mock_client.ocr_extract_text.return_value = "手机壳 保护套 39.9元"
        text = extract_text_from_image_bytes(_fake_image_bytes(), content_type="image/png")

    assert text == "手机壳 保护套 39.9元"
    mock_client.ocr_extract_text.assert_called_once()
    _, kwargs = mock_client.ocr_extract_text.call_args
    assert kwargs.get("content_type") == "image/png"


def test_mistral_ocr_failure_raises_clean_ocr_error():
    """Si Tesseract est absent ET que l'appel Mistral échoue, on lève une OCRError propre (pas un crash)."""
    with patch("pytesseract.image_to_string", side_effect=pytesseract.TesseractNotFoundError()), \
         patch("ai_engine.services.ocr_service.mistral_client") as mock_client:
        mock_client.ocr_extract_text.side_effect = MistralAPIError("réseau indisponible")
        try:
            extract_text_from_image_bytes(_fake_image_bytes())
            assert False, "OCRError attendue"
        except OCRError as exc:
            assert "Mistral" in str(exc)


def test_mistral_ocr_empty_text_raises_ocr_error():
    """Si Tesseract est absent ET que Mistral OCR ne détecte aucun texte, on lève OCRError (pas un texte vide silencieux)."""
    with patch("pytesseract.image_to_string", side_effect=pytesseract.TesseractNotFoundError()), \
         patch("ai_engine.services.ocr_service.mistral_client") as mock_client:
        mock_client.ocr_extract_text.return_value = "   "
        try:
            extract_text_from_image_bytes(_fake_image_bytes())
            assert False, "OCRError attendue"
        except OCRError as exc:
            assert "Aucun texte détecté" in str(exc)


def test_generic_tesseract_error_does_not_trigger_mistral_fallback():
    """
    Une erreur Tesseract QUELCONQUE (pas 'binaire absent') ne doit PAS déclencher le
    repli Mistral : c'est le comportement historique (image illisible = échec net),
    préservé pour ne rien changer en local.
    """
    with patch("pytesseract.image_to_string", side_effect=RuntimeError("erreur de décodage image")), \
         patch("ai_engine.services.ocr_service.mistral_client") as mock_client:
        try:
            extract_text_from_image_bytes(_fake_image_bytes())
            assert False, "OCRError attendue"
        except OCRError:
            pass

    mock_client.ocr_extract_text.assert_not_called()


def test_empty_text_from_tesseract_without_binary_missing_does_not_fallback():
    """Texte vide détecté par Tesseract (binaire présent) : échec normal, pas de repli Mistral."""
    with patch("pytesseract.image_to_string", return_value=""), \
         patch("ai_engine.services.ocr_service.mistral_client") as mock_client:
        try:
            extract_text_from_image_bytes(_fake_image_bytes())
            assert False, "OCRError attendue"
        except OCRError as exc:
            assert "Aucun texte détecté" in str(exc)

    mock_client.ocr_extract_text.assert_not_called()

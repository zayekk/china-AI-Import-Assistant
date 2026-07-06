"""
Service OCR : extrait le texte (chinois / anglais / français) d'une image
(capture d'écran de fiche produit) avant analyse IA.
"""
import io
import logging

import pytesseract
from PIL import Image, ImageFilter, ImageOps

from app.core.config import settings

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class OCRError(Exception):
    """Erreur levée en cas d'échec de l'extraction OCR."""


def _preprocess_image(image: Image.Image) -> Image.Image:
    """
    Améliore la lisibilité de l'image avant OCR :
    conversion en niveaux de gris, augmentation du contraste, débruitage léger.
    """
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Extrait le texte brut d'une image (bytes) via Tesseract OCR.
    Supporte le chinois simplifié, l'anglais et le français (cf. settings.OCR_LANG).
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")
        processed = _preprocess_image(image)

        text = pytesseract.image_to_string(processed, lang=settings.OCR_LANG)
        text = text.strip()

        if not text:
            raise OCRError(
                "Aucun texte détecté dans l'image. "
                "Essayez une capture plus nette ou avec un meilleur cadrage."
            )

        return text

    except OCRError:
        raise
    except Exception as exc:  # pytesseract / PIL peuvent lever divers types d'erreurs
        logger.error("Erreur OCR: %s", exc)
        raise OCRError(f"Échec de l'extraction OCR: {exc}") from exc

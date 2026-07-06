"""
Service OCR : extrait le texte (chinois / anglais / français) d'une image
(capture d'écran de fiche produit) avant analyse IA.

Tesseract (binaire système local) est utilisé en priorité — rapide, gratuit, déjà
éprouvé. S'il est absent (ex. environnement serverless comme Vercel, où aucun
paquet système n'est installable), le module bascule automatiquement sur l'API OCR
dédiée de Mistral (mistral-ocr-latest), qui ne nécessite qu'un accès réseau et
réutilise MISTRAL_API_KEY déjà configurée. Ce repli ne se déclenche que sur
l'absence constatée du binaire (pytesseract.TesseractNotFoundError) — une image
illisible avec Tesseract présent continue d'échouer normalement, comme avant.
"""
import io
import logging

import pytesseract
from PIL import Image, ImageFilter, ImageOps

from ai_engine.services.mistral_client import MistralAPIError, mistral_client
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


def extract_text_from_image_bytes(image_bytes: bytes, content_type: str = "image/png") -> str:
    """
    Extrait le texte brut d'une image (bytes) via Tesseract OCR.
    Supporte le chinois simplifié, l'anglais et le français (cf. settings.OCR_LANG).

    Si le binaire Tesseract n'est pas installé, bascule automatiquement sur l'API
    OCR de Mistral (voir _extract_text_via_mistral_ocr) — `content_type` sert
    uniquement d'indication de format pour ce repli distant (défaut sûr : les
    formats d'image acceptés à l'upload sont tous décodés par leur contenu binaire,
    pas par ce libellé).
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

    except pytesseract.TesseractNotFoundError:
        logger.warning(
            "Binaire Tesseract introuvable (environnement sans OCR local, ex. Vercel) — "
            "repli sur l'API OCR Mistral."
        )
        return _extract_text_via_mistral_ocr(image_bytes, content_type)

    except OCRError:
        raise
    except Exception as exc:  # pytesseract / PIL peuvent lever divers types d'erreurs
        logger.error("Erreur OCR: %s", exc)
        raise OCRError(f"Échec de l'extraction OCR: {exc}") from exc


def _extract_text_via_mistral_ocr(image_bytes: bytes, content_type: str) -> str:
    """Repli OCR via l'API Mistral, utilisé uniquement quand Tesseract est absent."""
    try:
        text = mistral_client.ocr_extract_text(image_bytes, content_type=content_type).strip()
    except MistralAPIError as exc:
        raise OCRError(f"Échec de l'extraction OCR (API Mistral) : {exc}") from exc

    if not text:
        raise OCRError(
            "Aucun texte détecté dans l'image. "
            "Essayez une capture plus nette ou avec un meilleur cadrage."
        )

    return text

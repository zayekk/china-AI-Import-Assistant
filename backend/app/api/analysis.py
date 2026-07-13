"""
Router API : endpoints d'analyse produit.

POST /analyze-text    -> analyse un texte produit brut
POST /analyze-image   -> analyse une capture d'écran (OCR + IA)
POST /analyze-images  -> analyse multi-captures intelligente (5 à 12 images, OCR + doublons + IA)
POST /analyze-url     -> scrape un lien produit puis l'analyse
"""
import logging

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ai_engine.services.multi_capture_service import analyze_multi_capture
from ai_engine.services.ocr_service import OCRError, extract_text_from_image_bytes
from ai_engine.services.product_analysis_service import analyze_product_text
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_optional_user
from app.models.analysis import (
    Analysis,
    AnalysisCapture,
    AnalysisRecommendation,
    AnalysisSourceType,
)
from app.models.product import Product
from app.models.user import User
from app.schemas.analysis import (
    AIAnalysisResult,
    AnalyzeTextRequest,
    AnalyzeUrlRequest,
    AnalysisOut,
    MultiCaptureAnalysisResult,
)
from app.utils.platform_detector import detect_platform
from scraper.spider_registry import scrape_product_url
from scraper.spiders.base_spider import SpiderError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analyse Produit"])

_SUPPORTED_LANGUAGES = ("fr", "en")


def _resolve_language(x_language: str | None) -> str:
    """
    Normalise l'en-tête X-Language (injecté par frontend/src/services/apiClient.js à partir
    du sélecteur FR/EN, voir frontend/src/utils/language.js) : retombe sur "fr" si absent ou
    non supporté, plutôt que de laisser passer une valeur arbitraire jusqu'au prompt IA.
    """
    if x_language and x_language.lower() in _SUPPORTED_LANGUAGES:
        return x_language.lower()
    return "fr"


def _persist_analysis(
    db: Session,
    source_type: AnalysisSourceType,
    raw_input: str | None,
    raw_input_url: str | None,
    result: dict,
    user: User | None,
    product: Product | None = None,
) -> Analysis:
    """Enregistre le résultat d'analyse en base de données."""
    analysis = Analysis(
        user_id=user.id if user else None,
        product_id=product.id if product else None,
        source_type=source_type,
        raw_input=raw_input,
        raw_input_url=raw_input_url,
        product_name=result.get("product_name"),
        included=result.get("included"),
        not_included=result.get("not_included"),
        warnings=result.get("warnings"),
        quality_score=str(result.get("quality_score", 0)),
        supplier_score=str(result.get("supplier_score", 0)),
        profit_score=str(result.get("profit_score", 0)),
        final_score=str(result.get("final_score", 0)),
        recommendation=AnalysisRecommendation(result.get("recommendation", "CAUTION")),
        detected_data=result.get("detected_data"),
        ai_estimations=result.get("ai_estimations"),
        missing_information=result.get("missing_information"),
        confidence_score=str(result.get("confidence_score", 0)),
        confidence_level=result.get("confidence_level"),
        confidence_reasons=result.get("confidence_reasons"),
        confidence_risks=result.get("confidence_risks"),
        mobile_summary=result.get("mobile_summary"),
        critical_alerts=result.get("critical_alerts"),
        ai_recommendation_summary=result.get("ai_recommendation_summary"),
        commercial_estimate=result.get("commercial_estimate"),
        decision_badge=result.get("decision_badge"),
        risk_level=result.get("risk_level"),
        supplier_reliability=result.get("supplier_reliability"),
        margin_potential=result.get("margin_potential"),
        language=result.get("language"),
        commercial_potential_rating=result.get("commercial_potential_rating"),
        commercial_potential_explanation=result.get("commercial_potential_explanation"),
        import_decision=result.get("import_decision"),
        import_decision_explanation=result.get("import_decision_explanation"),
        market_comparisons=result.get("market_comparisons"),
        demand_level=result.get("demand_level"),
        demand_explanation=result.get("demand_explanation"),
        quick_report=result.get("quick_report"),
        decision_reasons=result.get("decision_reasons"),
        winning_product_score=result.get("winning_product_score"),
        winning_product_explanation=result.get("winning_product_explanation"),
        competition_level=result.get("competition_level"),
        competition_explanation=result.get("competition_explanation"),
        data_confidence=result.get("data_confidence"),
        average_market_price=result.get("average_market_price"),
        market_positioning=result.get("market_positioning"),
        market_positioning_explanation=result.get("market_positioning_explanation"),
        resale_ease_rating=result.get("resale_ease_rating"),
        resale_ease_explanation=result.get("resale_ease_explanation"),
        raw_ai_response=result,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Détail par capture (analyses multi-captures uniquement) : une ligne AnalysisCapture
    # par élément de result["captures"], produit par
    # ai_engine/services/multi_capture_service.py::analyze_multi_capture(). Absent/vide
    # pour les analyses texte/image/URL simples -> rien n'est inséré.
    captures = result.get("captures") or []
    if captures:
        capture_rows = [
            AnalysisCapture(
                analysis_id=analysis.id,
                capture_index=c.get("index"),
                filename=c.get("filename"),
                category=c.get("category"),
                is_duplicate=bool(c.get("is_duplicate", False)),
                duplicate_of_index=c.get("duplicate_of_index"),
                ocr_excerpt=c.get("ocr_excerpt"),
                ocr_failed=bool(c.get("ocr_failed", False)),
            )
            for c in captures
        ]
        db.add_all(capture_rows)
        db.commit()

    return analysis


@router.post("/analyze-text", response_model=AIAnalysisResult)
def analyze_text(
    payload: AnalyzeTextRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    x_language: str | None = Header(default=None, alias="X-Language"),
):
    """
    Analyse un texte produit brut (titre/description), dans n'importe quelle langue source.
    Détecte les pièges classiques ("case only", "no battery included", etc.)
    et retourne un résultat structuré avec recommandation BUY/AVOID/CAUTION, rédigé dans la
    langue choisie par l'utilisateur (en-tête X-Language, "fr" par défaut).
    """
    result = analyze_product_text(payload.text, language=_resolve_language(x_language))
    _persist_analysis(
        db,
        source_type=AnalysisSourceType.TEXT,
        raw_input=payload.text,
        raw_input_url=None,
        result=result,
        user=current_user,
    )
    return result


@router.post("/analyze-image", response_model=AIAnalysisResult)
async def analyze_image(
    file: UploadFile = File(..., description="Capture d'écran de la fiche produit"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    x_language: str | None = Header(default=None, alias="X-Language"),
):
    """
    Analyse une capture d'écran de fiche produit :
    1. Extraction du texte via OCR (chinois/anglais/français)
    2. Analyse IA du texte extrait (mêmes règles que /analyze-text)
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format d'image non supporté. Utilisez JPEG, PNG ou WEBP.",
        )

    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo).",
        )

    try:
        extracted_text = extract_text_from_image_bytes(contents, content_type=file.content_type)
    except OCRError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    result = analyze_product_text(extracted_text, language=_resolve_language(x_language))
    _persist_analysis(
        db,
        source_type=AnalysisSourceType.IMAGE,
        raw_input=extracted_text,
        raw_input_url=None,
        result=result,
        user=current_user,
    )
    return result


@router.post("/analyze-images", response_model=MultiCaptureAnalysisResult)
async def analyze_images(
    files: list[UploadFile] = File(..., description="Entre 5 et 12 captures d'écran de la fiche produit"),
    categories: list[str] | None = Form(
        None,
        description="Catégorie connue de chaque capture, alignée par index avec 'files' "
        "(utilisé par le scan guidé ; laisser vide pour une classification automatique).",
    ),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    x_language: str | None = Header(default=None, alias="X-Language"),
):
    """
    Analyse multi-captures intelligente (5 à 12 images, 8 recommandé) :
    1. OCR de chaque capture
    2. Détection des doublons (hash perceptuel)
    3. Classification par catégorie (page principale, infos produit, boutique, avis,
       livraison) — automatique par mots-clés, ou via `categories` si fourni (scan guidé)
    4. Analyse IA consolidée du contenu agrégé (mêmes règles que /analyze-text)
    """
    if not (5 <= len(files) <= 12):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Le scan multi-captures nécessite entre 5 et 12 images (8 recommandé). "
                f"Vous en avez fourni {len(files)}."
            ),
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    captures: list[tuple[str, bytes]] = []
    for f in files:
        if f.content_type not in ("image/jpeg", "image/png", "image/webp", "image/jpg"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format d'image non supporté pour '{f.filename}'. Utilisez JPEG, PNG ou WEBP.",
            )
        contents = await f.read()
        if len(contents) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fichier '{f.filename}' trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB} Mo).",
            )
        captures.append((f.filename or "capture", contents))

    result = analyze_multi_capture(
        captures, category_hints=categories, language=_resolve_language(x_language)
    )

    combined_excerpt = " | ".join(c.get("ocr_excerpt", "") for c in result.get("captures", []))
    _persist_analysis(
        db,
        source_type=AnalysisSourceType.MULTI_IMAGE,
        raw_input=combined_excerpt,
        raw_input_url=None,
        result=result,
        user=current_user,
    )
    return result


@router.post("/analyze-url", response_model=AIAnalysisResult)
def analyze_url(
    payload: AnalyzeUrlRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    x_language: str | None = Header(default=None, alias="X-Language"),
):
    """
    Analyse un lien produit (Taobao / Pinduoduo / Alibaba / 1688) :
    1. Scraping de la fiche produit (nom, description, prix, variantes...)
    2. Analyse IA du contenu extrait
    """
    url = str(payload.url)
    platform = detect_platform(url)
    if platform == "unknown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plateforme non reconnue. URLs supportées : taobao.com, pinduoduo.com, "
            "alibaba.com, 1688.com",
        )

    try:
        scraped = scrape_product_url(url, fetch_reviews=False)
    except SpiderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    combined_text = f"{scraped.name}\n\n{scraped.description or ''}"
    if scraped.variants:
        variant_lines = "; ".join(
            f"{v['name']}: {', '.join(v['options'])}" for v in scraped.variants
        )
        combined_text += f"\n\nVariantes: {variant_lines}"

    result = analyze_product_text(combined_text, language=_resolve_language(x_language))

    # Sauvegarde du produit scrapé
    product = Product(
        name_original=scraped.name,
        description_original=scraped.description,
        source_url=url,
        platform=scraped.platform,
        price_value=scraped.price_value,
        price_currency=scraped.price_currency,
        images=scraped.images,
        variants=scraped.variants,
        stock=scraped.stock,
        sales_count=scraped.sales_count,
        rating=scraped.rating,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    _persist_analysis(
        db,
        source_type=AnalysisSourceType.URL,
        raw_input=combined_text,
        raw_input_url=url,
        result=result,
        user=current_user,
        product=product,
    )
    return result


@router.get("/analyses", response_model=list[AnalysisOut])
def list_my_analyses(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    limit: int = 50,
):
    """Liste les analyses de l'utilisateur courant (ou toutes les analyses anonymes récentes)."""
    query = db.query(Analysis).order_by(Analysis.created_at.desc())
    if current_user:
        query = query.filter(Analysis.user_id == current_user.id)
    return query.limit(limit).all()

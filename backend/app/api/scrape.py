"""
Router API : lancement du scraper et analyse fournisseur associée.

POST /scrape -> scrape une fiche produit + son fournisseur, enregistre tout en base.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ai_engine.services.supplier_analysis_service import analyze_supplier
from app.core.database import get_db
from app.core.deps import get_optional_user
from app.models.product import Product
from app.models.review import Review
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.scrape import ScrapeRequest, ScrapeResult
from scraper.spider_registry import scrape_product_url
from scraper.spiders.base_spider import SpiderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["Scraper"])


def _get_or_create_supplier(db: Session, scraped) -> Supplier | None:
    """Récupère ou crée le fournisseur associé au produit scrapé, avec son score IA."""
    if not scraped.supplier_name:
        return None

    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.name == scraped.supplier_name,
            Supplier.platform == scraped.platform,
        )
        .first()
    )

    if supplier is None:
        supplier = Supplier(
            name=scraped.supplier_name,
            platform=scraped.platform,
            shop_url=scraped.supplier_shop_url,
            years_active=scraped.supplier_years_active,
            rating=scraped.supplier_rating,
            total_reviews=scraped.supplier_total_reviews,
            total_sales=scraped.supplier_total_sales,
        )
        db.add(supplier)
        db.commit()
        db.refresh(supplier)

    # Calcule (ou recalcule) le score IA du fournisseur
    supplier_data = {
        "years_active": supplier.years_active,
        "rating": supplier.rating,
        "total_reviews": supplier.total_reviews,
        "total_sales": supplier.total_sales,
        "response_rate": supplier.response_rate,
        "dispute_rate": supplier.dispute_rate,
        "repeat_buyer_rate": supplier.repeat_buyer_rate,
    }
    analysis = analyze_supplier(supplier_data)
    supplier.supplier_score = analysis["supplier_score"]
    db.commit()
    db.refresh(supplier)

    return supplier


@router.post("", response_model=ScrapeResult)
def launch_scrape(
    payload: ScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Lance le scraper sur l'URL fournie, enregistre le produit, le fournisseur
    et les avis en base de données.
    """
    url = str(payload.url)

    try:
        scraped = scrape_product_url(
            url, fetch_reviews=payload.fetch_reviews, max_reviews=payload.max_reviews
        )
    except SpiderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    supplier = _get_or_create_supplier(db, scraped)

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
        supplier_id=supplier.id if supplier else None,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    for review in scraped.reviews:
        db.add(
            Review(
                product_id=product.id,
                author=review.author,
                rating=review.rating,
                content_original=review.content,
                images=review.images,
                variant_purchased=review.variant_purchased,
            )
        )
    db.commit()

    return ScrapeResult(
        success=True,
        product_id=str(product.id),
        message=f"Produit scrapé avec succès depuis {scraped.platform}.",
        data={
            "name": scraped.name,
            "price": scraped.price_value,
            "supplier_score": supplier.supplier_score if supplier else None,
            "reviews_count": len(scraped.reviews),
        },
    )

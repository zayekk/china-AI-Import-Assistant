"""
Router API : calcul et consultation du score "produit gagnant" IA.

GET /score/{id} -> calcule (ou recalcule) et retourne le score pondéré d'un produit.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ai_engine.services.winning_product_service import score_winning_product
from app.core.database import get_db
from app.models.product import Product
from app.models.score import Score
from app.schemas.product import ScoreOut

router = APIRouter(prefix="/score", tags=["Score Produit Gagnant"])


@router.get("/{product_id}", response_model=ScoreOut)
def get_product_score(
    product_id: uuid.UUID,
    force_recompute: bool = False,
    db: Session = Depends(get_db),
):
    """
    Retourne le score "produit gagnant" d'un produit.
    Si aucun score n'existe encore (ou si force_recompute=True), le calcule via l'IA
    et le persiste en base.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")

    existing_score = (
        db.query(Score)
        .filter(Score.product_id == product_id)
        .order_by(Score.created_at.desc())
        .first()
    )

    if existing_score and not force_recompute:
        return existing_score

    supplier_score_value = (
        product.supplier.supplier_score if product.supplier and product.supplier.supplier_score else 50
    )

    product_data = {
        "name": product.name_translated or product.name_original,
        "sales_count": product.sales_count,
        "price_value": product.price_value,
        "rating": product.rating,
        "supplier_score": supplier_score_value,
        "category": None,
    }

    result = score_winning_product(product_data)

    score = Score(
        product_id=product.id,
        demand_score=result["demand_score"],
        margin_score=result["margin_score"],
        quality_score=result["quality_score"],
        supplier_reliability_score=result["supplier_reliability_score"],
        logistics_score=result["logistics_score"],
        final_score=result["final_score"],
        strengths=result["strengths"],
        risks=result["risks"],
        explanation=result["explanation"],
    )
    db.add(score)
    db.commit()
    db.refresh(score)

    return score

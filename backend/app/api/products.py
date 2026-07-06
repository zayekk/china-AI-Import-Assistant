"""
Router API : gestion et consultation des produits.

GET /products      -> liste paginée avec filtres
GET /products/{id} -> détail complet d'un produit
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.product import Product
from app.schemas.product import ProductListItem, ProductOut

router = APIRouter(prefix="/products", tags=["Produits"])


@router.get("", response_model=list[ProductListItem])
def list_products(
    db: Session = Depends(get_db),
    platform: str | None = Query(default=None, description="Filtrer par plateforme"),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    max_price: float | None = Query(default=None, ge=0),
    search: str | None = Query(default=None, description="Recherche dans le nom du produit"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    """Liste les produits enregistrés, avec filtres optionnels et pagination."""
    query = db.query(Product)

    if platform:
        query = query.filter(Product.platform == platform)
    if min_rating is not None:
        query = query.filter(Product.rating >= min_rating)
    if max_price is not None:
        query = query.filter(Product.price_value <= max_price)
    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            (Product.name_translated.ilike(like_pattern))
            | (Product.name_original.ilike(like_pattern))
        )

    query = query.order_by(Product.created_at.desc())
    offset = (page - 1) * page_size
    return query.offset(offset).limit(page_size).all()


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retourne le détail complet d'un produit, avec son fournisseur."""
    product = (
        db.query(Product)
        .options(joinedload(Product.supplier))
        .filter(Product.id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produit introuvable")
    return product

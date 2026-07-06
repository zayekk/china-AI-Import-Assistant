"""
Schémas Pydantic : Product, Supplier, Review, Score.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---------- Supplier ----------

class SupplierOut(BaseModel):
    id: uuid.UUID
    name: str
    platform: str
    shop_url: str | None
    years_active: float | None
    rating: float | None
    total_reviews: int | None
    total_sales: int | None
    response_rate: float | None
    dispute_rate: float | None
    repeat_buyer_rate: float | None
    supplier_score: float | None

    model_config = {"from_attributes": True}


# ---------- Review ----------

class ReviewOut(BaseModel):
    id: uuid.UUID
    author: str | None
    rating: float | None
    content_translated: str | None
    variant_purchased: str | None
    sentiment: str | None
    is_flagged: str | None

    model_config = {"from_attributes": True}


# ---------- Product ----------

class ProductBase(BaseModel):
    name_original: str
    name_translated: str | None = None
    description_original: str | None = None
    description_translated: str | None = None
    source_url: str | None = None
    platform: str | None = None
    price_value: float | None = None
    price_currency: str = "CNY"
    images: list[str] | None = None
    variants: list[dict] | None = None
    stock: int | None = None
    sales_count: int | None = None
    rating: float | None = None


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: uuid.UUID
    supplier: SupplierOut | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    """Version allégée pour les listes paginées."""
    id: uuid.UUID
    name_translated: str | None
    name_original: str
    price_value: float | None
    price_currency: str
    rating: float | None
    sales_count: int | None
    platform: str | None
    images: list[str] | None

    model_config = {"from_attributes": True}


# ---------- Score ----------

class ScoreBreakdown(BaseModel):
    demand_score: float = Field(ge=0, le=100)
    margin_score: float = Field(ge=0, le=100)
    quality_score: float = Field(ge=0, le=100)
    supplier_reliability_score: float = Field(ge=0, le=100)
    logistics_score: float = Field(ge=0, le=100)


class ScoreOut(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    demand_score: float
    margin_score: float
    quality_score: float
    supplier_reliability_score: float
    logistics_score: float
    final_score: float
    strengths: list[str] | None
    risks: list[str] | None
    explanation: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

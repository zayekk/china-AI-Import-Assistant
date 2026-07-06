"""
Modèle Product : produits récupérés via scraping ou analyse.
"""
import uuid

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name_original = Column(String(1000), nullable=False)     # nom dans la langue source
    name_translated = Column(String(1000), nullable=True)    # nom traduit
    description_original = Column(Text, nullable=True)
    description_translated = Column(Text, nullable=True)

    source_url = Column(String(2000), nullable=True)
    platform = Column(String(50), nullable=True)  # taobao, pinduoduo, alibaba, 1688

    price_value = Column(Float, nullable=True)
    price_currency = Column(String(10), default="CNY")

    images = Column(JSON, nullable=True)        # liste d'URLs d'images
    variants = Column(JSON, nullable=True)       # liste de variantes {name, options[]}
    stock = Column(Integer, nullable=True)
    sales_count = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)

    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    supplier = relationship("Supplier", back_populates="products")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="product", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Product {self.name_translated or self.name_original}>"

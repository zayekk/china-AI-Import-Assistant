"""
Modèle Supplier : vendeurs / boutiques sur les plateformes chinoises.
"""
import uuid

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String(255), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # taobao, pinduoduo, alibaba, 1688...
    shop_url = Column(String(1000), nullable=True)
    external_shop_id = Column(String(255), nullable=True, index=True)

    # Indicateurs bruts récupérés par le scraper
    years_active = Column(Float, nullable=True)          # ancienneté en années
    rating = Column(Float, nullable=True)                # note /5
    total_reviews = Column(Integer, nullable=True)
    total_sales = Column(Integer, nullable=True)
    response_rate = Column(Float, nullable=True)         # % réponse au service client
    dispute_rate = Column(Float, nullable=True)          # % litiges / plaintes
    repeat_buyer_rate = Column(Float, nullable=True)     # % clients qui rachètent

    # Score calculé par l'AI engine (0-100)
    supplier_score = Column(Float, nullable=True)
    score_breakdown = Column(String, nullable=True)  # JSON sérialisé en texte

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    products = relationship("Product", back_populates="supplier")

    def __repr__(self) -> str:
        return f"<Supplier {self.name} ({self.platform}) score={self.supplier_score}>"

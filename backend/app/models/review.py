"""
Modèle Review : avis clients récupérés sur les fiches produits.
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    author = Column(String(255), nullable=True)
    rating = Column(Float, nullable=True)
    content_original = Column(Text, nullable=True)
    content_translated = Column(Text, nullable=True)
    images = Column(JSON, nullable=True)  # photos clients
    variant_purchased = Column(String(500), nullable=True)
    sentiment = Column(String(20), nullable=True)  # positive / neutral / negative
    is_flagged = Column(String(10), default="false")  # plainte détectée par IA

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="reviews")

    def __repr__(self) -> str:
        return f"<Review by {self.author} rating={self.rating}>"

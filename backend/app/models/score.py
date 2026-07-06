"""
Modèle Score : score "produit gagnant" calculé par le moteur IA
(pondération demande / marge / qualité / fiabilité / logistique).
"""
import uuid

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)

    # Sous-scores bruts (0-100 chacun)
    demand_score = Column(Float, nullable=False, default=0)      # 30%
    margin_score = Column(Float, nullable=False, default=0)      # 25%
    quality_score = Column(Float, nullable=False, default=0)     # 20%
    supplier_reliability_score = Column(Float, nullable=False, default=0)  # 15%
    logistics_score = Column(Float, nullable=False, default=0)   # 10%

    final_score = Column(Float, nullable=False, default=0)  # somme pondérée /100

    strengths = Column(JSON, nullable=True)   # liste de points forts
    risks = Column(JSON, nullable=True)        # liste de risques
    explanation = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="scores")

    # Pondérations officielles du moteur (constantes du projet)
    WEIGHTS = {
        "demand": 0.30,
        "margin": 0.25,
        "quality": 0.20,
        "supplier_reliability": 0.15,
        "logistics": 0.10,
    }

    def compute_final_score(self) -> float:
        """Calcule le score final pondéré à partir des sous-scores."""
        self.final_score = round(
            self.demand_score * self.WEIGHTS["demand"]
            + self.margin_score * self.WEIGHTS["margin"]
            + self.quality_score * self.WEIGHTS["quality"]
            + self.supplier_reliability_score * self.WEIGHTS["supplier_reliability"]
            + self.logistics_score * self.WEIGHTS["logistics"],
            2,
        )
        return self.final_score

    def __repr__(self) -> str:
        return f"<Score product={self.product_id} final={self.final_score}>"

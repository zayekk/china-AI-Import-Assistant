"""
Modèle Analysis : résultat d'une analyse IA (texte, image ou URL) demandée par un utilisateur.
"""
import enum
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AnalysisSourceType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    URL = "url"
    MULTI_IMAGE = "multi_image"


class AnalysisRecommendation(str, enum.Enum):
    BUY = "BUY"
    AVOID = "AVOID"
    CAUTION = "CAUTION"


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    source_type = Column(Enum(AnalysisSourceType), nullable=False)
    raw_input = Column(Text, nullable=True)          # texte brut ou OCR extrait
    raw_input_url = Column(String(2000), nullable=True)

    # Résultat IA structuré (correspond au schéma JSON imposé)
    product_name = Column(String(1000), nullable=True)
    included = Column(JSON, nullable=True)            # liste de strings
    not_included = Column(JSON, nullable=True)         # liste de strings
    warnings = Column(JSON, nullable=True)              # liste de strings

    quality_score = Column(String(10), nullable=True)
    supplier_score = Column(String(10), nullable=True)
    profit_score = Column(String(10), nullable=True)
    final_score = Column(String(10), nullable=True)

    recommendation = Column(Enum(AnalysisRecommendation), nullable=True)

    # Séparation explicite données détectées / estimations IA / informations manquantes,
    # et score de confiance justifié (voir schémas AIAnalysisResult / AnalysisOut).
    detected_data = Column(JSON, nullable=True)         # dict clé/valeur
    ai_estimations = Column(JSON, nullable=True)         # dict clé/valeur
    missing_information = Column(JSON, nullable=True)    # liste de strings

    confidence_score = Column(String(10), nullable=True)
    confidence_level = Column(String(20), nullable=True)
    confidence_reasons = Column(JSON, nullable=True)     # liste de strings
    confidence_risks = Column(JSON, nullable=True)       # liste de strings

    # Résumé compact sur une ligne, calculé côté serveur (jamais par l'IA), destiné au
    # futur affichage dans une bulle flottante mobile (voir docs/mobile_architecture.md).
    mobile_summary = Column(String(500), nullable=True)

    # Rapport de décision enrichi (voir schémas AIAnalysisResult / CommercialEstimate) :
    # alertes IA + synthèse IA + estimation commerciale, et badge/risque/fiabilité/marge
    # toujours calculés côté serveur à partir des scores ci-dessus.
    critical_alerts = Column(JSON, nullable=True)          # liste de strings
    ai_recommendation_summary = Column(Text, nullable=True)
    commercial_estimate = Column(JSON, nullable=True)      # dict CommercialEstimate
    decision_badge = Column(String(20), nullable=True)
    risk_level = Column(String(10), nullable=True)
    supplier_reliability = Column(String(10), nullable=True)
    margin_potential = Column(String(10), nullable=True)

    raw_ai_response = Column(JSON, nullable=True)  # réponse brute pour debug / audit

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="analyses")
    product = relationship("Product", back_populates="analyses")
    captures = relationship(
        "AnalysisCapture", back_populates="analysis", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Analysis {self.product_name} -> {self.recommendation}>"


class AnalysisCapture(Base):
    """
    Détail par capture d'une analyse multi-captures (`POST /analyze-images`) : une ligne
    par image envoyée, liée à l'analyse parente. Rend interrogeable/filtrable en base ce
    qui n'existait auparavant que noyé dans la colonne JSON `raw_ai_response` (ex: "combien
    d'analyses ont une capture catégorisée 'shop' dupliquée"). Format produit par
    `ai_engine/services/multi_capture_service.py::analyze_multi_capture()`.
    """
    __tablename__ = "analysis_captures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        UUID(as_uuid=True), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )

    capture_index = Column(Integer, nullable=False)
    filename = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of_index = Column(Integer, nullable=True)
    ocr_excerpt = Column(Text, nullable=True)
    ocr_failed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis = relationship("Analysis", back_populates="captures")

    def __repr__(self) -> str:
        return f"<AnalysisCapture {self.capture_index} ({self.category}) -> {self.analysis_id}>"

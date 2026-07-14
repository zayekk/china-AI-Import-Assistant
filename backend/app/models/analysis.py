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

    # v1.1 : langue de génération du rapport, potentiel commercial (étoiles), décision
    # d'import dédiée, comparaisons marché, demande — voir schémas AIAnalysisResult /
    # MarketComparison et ai_engine/services/product_analysis_service.py.
    language = Column(String(2), nullable=True)
    commercial_potential_rating = Column(Integer, nullable=True)
    commercial_potential_explanation = Column(Text, nullable=True)
    import_decision = Column(String(10), nullable=True)
    import_decision_explanation = Column(Text, nullable=True)
    market_comparisons = Column(JSON, nullable=True)      # liste de dicts MarketComparison
    demand_level = Column(String(12), nullable=True)
    demand_explanation = Column(Text, nullable=True)
    quick_report = Column(JSON, nullable=True)            # liste de strings

    # v1.2 : raisons de la décision, winning product, concurrence, confiance par catégorie,
    # positionnement marché, facilité de revente — voir schémas AIAnalysisResult / DataConfidence
    # et ai_engine/services/product_analysis_service.py.
    decision_reasons = Column(JSON, nullable=True)         # liste de strings (5 max)
    winning_product_score = Column(Integer, nullable=True)
    winning_product_explanation = Column(Text, nullable=True)
    competition_level = Column(String(10), nullable=True)
    competition_explanation = Column(Text, nullable=True)
    data_confidence = Column(JSON, nullable=True)           # dict DataConfidence
    average_market_price = Column(String(200), nullable=True)
    market_positioning = Column(String(12), nullable=True)
    market_positioning_explanation = Column(Text, nullable=True)
    resale_ease_rating = Column(Integer, nullable=True)
    resale_ease_explanation = Column(Text, nullable=True)

    # v1.3 : avis clients, profil vendeur, public cible, stratégie d'import, saisonnalité,
    # saturation, produits complémentaires, logistique, difficulté d'import, marketing
    # trompeur, résumé importateur — voir schémas AIAnalysisResult / SupplierProfile /
    # ImportStrategy / Seasonality / LogisticsProfile / MarketingClaim et
    # ai_engine/services/product_analysis_service.py.
    reviews_available = Column(Boolean, nullable=True)
    review_highlights = Column(JSON, nullable=True)          # liste de strings (4 max)
    review_complaints = Column(JSON, nullable=True)          # liste de strings (4 max)
    review_recurring_defects = Column(JSON, nullable=True)   # liste de strings (4 max)
    review_satisfaction = Column(String(12), nullable=True)
    supplier_profile = Column(JSON, nullable=True)           # dict SupplierProfile
    target_audiences = Column(JSON, nullable=True)           # liste de strings (liste fermée)
    target_audience_explanation = Column(Text, nullable=True)
    import_strategy = Column(JSON, nullable=True)            # dict ImportStrategy
    seasonality = Column(JSON, nullable=True)                # dict Seasonality
    saturation_level = Column(String(24), nullable=True)
    saturation_explanation = Column(Text, nullable=True)
    complementary_products = Column(JSON, nullable=True)     # liste de strings (6 max)
    logistics_profile = Column(JSON, nullable=True)          # dict LogisticsProfile
    recommended_transport = Column(String(10), nullable=True)
    transport_explanation = Column(Text, nullable=True)
    import_difficulty = Column(String(12), nullable=True)
    import_difficulty_explanation = Column(Text, nullable=True)
    marketing_claims = Column(JSON, nullable=True)           # liste de dicts MarketingClaim
    importer_summary = Column(JSON, nullable=True)           # liste de strings (8 max)

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

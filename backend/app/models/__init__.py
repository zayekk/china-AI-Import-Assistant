"""
Centralise l'import de tous les modèles SQLAlchemy.
Important : Base.metadata.create_all() a besoin que tous les modèles
soient importés au moins une fois pour détecter les relations.
"""
from app.models.user import User, UserRole  # noqa: F401
from app.models.supplier import Supplier  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.review import Review  # noqa: F401
from app.models.analysis import (  # noqa: F401
    Analysis,
    AnalysisCapture,
    AnalysisSourceType,
    AnalysisRecommendation,
)
from app.models.score import Score  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "Supplier",
    "Product",
    "Review",
    "Analysis",
    "AnalysisCapture",
    "AnalysisSourceType",
    "AnalysisRecommendation",
    "Score",
]

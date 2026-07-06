"""
Schémas Pydantic : requêtes et réponses d'analyse produit (texte / image / URL).
Le format de sortie JSON respecte strictement le contrat imposé par le projet :

{
  "product_name": "",
  "included": [],
  "not_included": [],
  "warnings": [],
  "quality_score": 0,
  "supplier_score": 0,
  "profit_score": 0,
  "final_score": 0,
  "recommendation": "BUY/AVOID"
}
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=2, max_length=5000, description="Texte produit (toute langue)")


class AnalyzeUrlRequest(BaseModel):
    url: HttpUrl = Field(..., description="Lien produit Taobao / Pinduoduo / Alibaba / 1688")


class AnalyzeImageRequest(BaseModel):
    """
    Utilisé uniquement pour la doc OpenAPI : la véritable requête image
    se fait en multipart/form-data (UploadFile) au niveau du endpoint.
    """
    note: str | None = None


class AIAnalysisResult(BaseModel):
    """Contrat de sortie STRICT renvoyé par le moteur IA (Mistral)."""

    product_name: str = ""
    included: list[str] = Field(default_factory=list)
    not_included: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    quality_score: int = Field(default=0, ge=0, le=100)
    supplier_score: int = Field(default=0, ge=0, le=100)
    profit_score: int = Field(default=0, ge=0, le=100)
    final_score: int = Field(default=0, ge=0, le=100)
    recommendation: Literal["BUY", "AVOID", "CAUTION"] = "CAUTION"

    # --- Séparation explicite données détectées / estimations IA / manques ---
    detected_data: dict[str, str] = Field(default_factory=dict)       # A) données détectées telles quelles dans le texte
    ai_estimations: dict[str, str] = Field(default_factory=dict)      # B) estimations/déductions IA (jamais présentées comme faits)
    missing_information: list[str] = Field(default_factory=list)      # C) informations manquantes pour trancher
    confidence_score: int = Field(default=0, ge=0, le=100)
    confidence_level: Literal["insufficient", "approximate", "reliable", "high"] = "insufficient"
    confidence_reasons: list[str] = Field(default_factory=list)       # pourquoi ce score (2-4 items)
    confidence_risks: list[str] = Field(default_factory=list)         # quels risques existent à cause du manque d'info

    # Résumé compact sur une ligne, calculé côté serveur (jamais par l'IA) à partir des
    # champs ci-dessus. Destiné à un futur affichage dans une bulle flottante mobile
    # (voir docs/mobile_architecture.md, section 5).
    mobile_summary: str = ""


class AnalysisOut(BaseModel):
    id: uuid.UUID
    source_type: str
    product_name: str | None
    included: list[str] | None
    not_included: list[str] | None
    warnings: list[str] | None
    quality_score: str | None
    supplier_score: str | None
    profit_score: str | None
    final_score: str | None
    recommendation: str | None
    created_at: datetime

    detected_data: dict[str, str] | None = None
    ai_estimations: dict[str, str] | None = None
    missing_information: list[str] | None = None
    confidence_score: str | None = None
    confidence_level: str | None = None
    confidence_reasons: list[str] | None = None
    confidence_risks: list[str] | None = None
    mobile_summary: str | None = None

    model_config = {"from_attributes": True}


CaptureCategory = Literal["main_page", "product_info", "shop", "reviews", "shipping", "other"]


class CaptureClassification(BaseModel):
    index: int
    filename: str
    category: CaptureCategory
    is_duplicate: bool = False
    duplicate_of_index: int | None = None
    ocr_excerpt: str = ""


class MultiCaptureAnalysisResult(AIAnalysisResult):
    """Résultat d'une analyse multi-captures (5 à 12 images) : hérite du contrat IA standard
    et ajoute le détail de classification par capture."""
    captures: list[CaptureClassification] = Field(default_factory=list)
    categories_covered: list[str] = Field(default_factory=list)
    categories_missing: list[str] = Field(default_factory=list)

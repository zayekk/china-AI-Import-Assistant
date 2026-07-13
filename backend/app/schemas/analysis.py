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


class CommercialEstimate(BaseModel):
    """
    Analyse financière (coût d'achat/transport/douane -> coût rendu -> revente -> bénéfice/marge),
    ou marquée impossible si le texte source ne contient aucune donnée de prix exploitable.

    L'IA ne fournit que les 4 montants "input" (purchase_price_eur, estimated_transport_eur,
    estimated_customs_eur, suggested_resale_price_eur) : tous les montants dérivés
    (landed_cost_eur, estimated_profit_eur, margin_percentage, estimated_profit_fcfa,
    commercial_potential) sont calculés STRICTEMENT côté serveur (voir
    ai_engine/services/product_analysis_service.py::_normalize_commercial_estimate) pour
    garantir une arithmétique cohérente, jamais sujette aux approximations de calcul de l'IA.
    """

    possible: bool = False
    reason_if_not_possible: str | None = None

    # --- Fournis par l'IA (estimations, jamais des faits confirmés) ---
    purchase_price_eur: float | None = None
    estimated_transport_eur: float | None = None
    estimated_customs_eur: float | None = None
    suggested_resale_price_eur: float | None = None

    # --- Calculés côté serveur ---
    landed_cost_eur: float | None = None
    estimated_profit_eur: float | None = None
    margin_percentage: float | None = None
    # Conversion au taux FIXE réel EUR/XOF (settings.IMPORT_EUR_XOF_RATE), pas une estimation.
    estimated_profit_fcfa: int | None = None
    # Calculé à partir de margin_percentage si disponible, sinon de profit_score (repli) —
    # toujours cohérent avec "margin_potential" du résumé rapide (même valeur).
    commercial_potential: Literal["low", "medium", "high"] | None = None


class MarketComparison(BaseModel):
    """Comparaison d'un composant technique détecté (GPU, CPU, RAM, SSD...) à des références
    connues du marché actuel (ex: component="GPU", detected_value="HD 7670",
    comparison="≈ GTX 750 Ti, très inférieur à une RTX 3060 actuelle")."""

    component: str
    detected_value: str
    comparison: str


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

    # --- Rapport de décision (voir docs sur le rapport enrichi) ---
    # Contradictions factuelles détectées par l'IA entre différentes parties du texte source
    # (titre vs specs, description vs avis, capture vs capture...).
    critical_alerts: list[str] = Field(default_factory=list)
    # Synthèse en langage simple générée par l'IA (2-4 phrases).
    ai_recommendation_summary: str = ""
    commercial_estimate: CommercialEstimate = Field(default_factory=CommercialEstimate)

    # Les 4 champs suivants sont TOUJOURS calculés côté serveur (jamais par l'IA), à partir des
    # scores et alertes ci-dessus, pour garantir cohérence et déterminisme (même principe que
    # "confidence_level"). Voir ai_engine/services/product_analysis_service.py.
    decision_badge: Literal["recommended", "verify", "caution", "avoid"] = "caution"
    risk_level: Literal["low", "medium", "high"] = "medium"
    supplier_reliability: Literal["yes", "medium", "no"] = "medium"
    margin_potential: Literal["low", "medium", "high"] = "medium"

    # --- v1.1 : langue, potentiel commercial, décision import, comparaisons marché, demande ---
    # Langue effectivement utilisée pour générer ce rapport (transmise par le frontend via
    # l'en-tête X-Language, jamais choisie par l'IA) — voir ai_engine/prompts/product_prompts.py.
    language: Literal["fr", "en"] = "fr"

    commercial_potential_rating: int = Field(default=3, ge=1, le=5)
    commercial_potential_explanation: str = ""

    # import_decision est TOUJOURS calculé côté serveur (jamais par l'IA), à partir de
    # decision_badge/margin_potential/commercial_potential_rating/critical_alerts déjà produits —
    # aucun appel IA supplémentaire. Voir _import_decision() dans product_analysis_service.py.
    import_decision: Literal["import", "study", "avoid"] = "study"
    import_decision_explanation: str = ""

    market_comparisons: list[MarketComparison] = Field(default_factory=list)

    demand_level: Literal["very_high", "high", "medium", "low", "very_low"] = "medium"
    demand_explanation: str = ""

    # Résumé de lecture ultra-rapide (<10s), généré par l'IA à partir des champs ci-dessus,
    # sans information nouvelle (voir règle prompt correspondante).
    quick_report: list[str] = Field(default_factory=list)


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

    critical_alerts: list[str] | None = None
    ai_recommendation_summary: str | None = None
    commercial_estimate: dict | None = None
    decision_badge: str | None = None
    risk_level: str | None = None
    supplier_reliability: str | None = None
    margin_potential: str | None = None

    language: str | None = None
    commercial_potential_rating: int | None = None
    commercial_potential_explanation: str | None = None
    import_decision: str | None = None
    import_decision_explanation: str | None = None
    market_comparisons: list[dict] | None = None
    demand_level: str | None = None
    demand_explanation: str | None = None
    quick_report: list[str] | None = None

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

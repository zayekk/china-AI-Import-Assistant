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

    Pipeline PRIMAIRE (v1.2) : yuan (¥, devise réelle des plateformes chinoises) côté achat ->
    FCFA (devise de revente locale en Afrique de l'Ouest/Centrale) côté résultat, via le taux
    HEURISTIQUE settings.IMPORT_CNY_XOF_RATE (1¥ = 100 FCFA par défaut — voir sa docstring).
    Pipeline SECONDAIRE (v1.1, conservé pour compatibilité) : euro, utilisé en repli si l'IA n'a
    trouvé aucun prix en yuan.

    L'IA ne fournit que les montants "input" (purchase_price_cny/eur, estimated_transport_cny/eur,
    estimated_customs_cny/eur, misc_fees_cny, suggested_resale_price_fcfa/eur) : tous les montants
    dérivés (landed_cost, estimated_profit, margin_percentage, roi_percentage,
    estimated_profit_fcfa, commercial_potential) sont calculés STRICTEMENT côté serveur (voir
    ai_engine/services/product_analysis_service.py::_normalize_commercial_estimate) pour
    garantir une arithmétique cohérente, jamais sujette aux approximations de calcul de l'IA.
    """

    possible: bool = False
    reason_if_not_possible: str | None = None

    # --- Fournis par l'IA : pipeline primaire (yuan -> FCFA), estimations jamais des faits ---
    purchase_price_cny: float | None = None
    estimated_transport_cny: float | None = None
    estimated_customs_cny: float | None = None
    misc_fees_cny: float | None = None
    suggested_resale_price_fcfa: float | None = None

    # --- Calculés côté serveur, pipeline primaire (FCFA) ---
    landed_cost_fcfa: float | None = None
    estimated_profit_fcfa: int | None = None
    margin_percentage: float | None = None
    # Retour sur investissement = bénéfice / coût rendu * 100.
    roi_percentage: float | None = None
    # Calculé à partir de margin_percentage si disponible, sinon de profit_score (repli) —
    # toujours cohérent avec "margin_potential" du résumé rapide (même valeur).
    commercial_potential: Literal["low", "medium", "high"] | None = None

    # --- Fournis par l'IA : pipeline secondaire (euro), repli si aucun prix en yuan disponible ---
    purchase_price_eur: float | None = None
    estimated_transport_eur: float | None = None
    estimated_customs_eur: float | None = None
    suggested_resale_price_eur: float | None = None

    # --- Calculés côté serveur, pipeline secondaire (euro) ---
    landed_cost_eur: float | None = None
    estimated_profit_eur: float | None = None


class DataConfidence(BaseModel):
    """
    Confiance de l'IA par catégorie de donnée (distincte de "confidence_score" qui reflète la
    confiance GLOBALE) : permet à l'utilisateur de savoir quelles informations sont les plus
    fiables. "photos" reste structurellement prudent : le pipeline actuel n'envoie que du texte
    OCR à l'IA, jamais l'image elle-même — voir la règle prompt correspondante.
    """

    price: int = Field(default=0, ge=0, le=100)
    specifications: int = Field(default=0, ge=0, le=100)
    photos: int = Field(default=0, ge=0, le=100)
    reviews: int = Field(default=0, ge=0, le=100)
    # Pour une analyse multi-captures, écrasé côté serveur par le taux réel de captures
    # exploitées avec succès par l'OCR (voir multi_capture_service.py) plutôt que l'estimation IA.
    ocr: int = Field(default=0, ge=0, le=100)


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

    # --- v1.2 : raisons de la décision, winning product, concurrence, confiance par catégorie,
    # positionnement marché, facilité de revente ---

    # Jusqu'à 5 raisons courtes ("vendeur fiable", "faible marge"...), générées par l'IA à partir
    # de constats déjà présents ailleurs dans la réponse.
    decision_reasons: list[str] = Field(default_factory=list)

    winning_product_score: int = Field(default=5, ge=0, le=10)
    winning_product_explanation: str = ""

    competition_level: Literal["low", "medium", "high", "very_high"] = "medium"
    competition_explanation: str = ""

    data_confidence: DataConfidence = Field(default_factory=DataConfidence)

    average_market_price: str | None = None
    market_positioning: Literal["premium", "mid_range", "entry_level", "saturated", "unknown"] = (
        "unknown"
    )
    market_positioning_explanation: str = ""

    resale_ease_rating: int = Field(default=3, ge=1, le=5)
    resale_ease_explanation: str = ""


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

    decision_reasons: list[str] | None = None
    winning_product_score: int | None = None
    winning_product_explanation: str | None = None
    competition_level: str | None = None
    competition_explanation: str | None = None
    data_confidence: dict | None = None
    average_market_price: str | None = None
    market_positioning: str | None = None
    market_positioning_explanation: str | None = None
    resale_ease_rating: int | None = None
    resale_ease_explanation: str | None = None

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

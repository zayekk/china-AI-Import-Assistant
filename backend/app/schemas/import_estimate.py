"""
Schémas Pydantic : estimation du coût d'importation (prix Chine + transport → coût
total, marge, recommandation d'achat).
"""
from typing import Literal

from pydantic import BaseModel, Field


class ImportEstimateRequest(BaseModel):
    product_price_cny: float = Field(..., gt=0, description="Prix unitaire du produit en Chine (CNY)")
    quantity: int = Field(default=1, ge=1)
    weight_kg: float = Field(..., gt=0, description="Poids estimé total (kg)")
    transport_method: Literal["air", "sea"]
    user_shipping_cost_cny: float | None = Field(
        default=None, ge=0, description="Coût transport réel connu de l'utilisateur, prioritaire sur l'estimation"
    )
    target_selling_price_eur: float | None = Field(
        default=None, ge=0, description="Prix de revente cible (EUR), optionnel, pour calcul de marge"
    )
    customs_duty_rate_pct: float = Field(default=0, ge=0, le=100)


class ImportEstimateResponse(BaseModel):
    product_cost_cny: float
    transport_cost_cny: float
    customs_cost_cny: float
    total_cost_cny: float
    total_cost_eur_estimated: float
    cost_per_unit_cny: float
    cost_per_unit_eur_estimated: float
    margin_amount_eur: float | None
    margin_percentage: float | None
    recommendation: Literal["ACHETER", "NE_PAS_ACHETER", "A_ETUDIER"]
    recommendation_reasons: list[str]
    assumptions: list[str]

"""
Tests unitaires : moteur de scoring "produit gagnant" (pondération officielle).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from ai_engine.services.winning_product_service import compute_final_score


def test_compute_final_score_weights():
    """Vérifie que la pondération officielle (30/25/20/15/10) est bien appliquée."""
    sub_scores = {
        "demand_score": 100,
        "margin_score": 100,
        "quality_score": 100,
        "supplier_reliability_score": 100,
        "logistics_score": 100,
    }
    assert compute_final_score(sub_scores) == 100.0


def test_compute_final_score_zero():
    sub_scores = {
        "demand_score": 0,
        "margin_score": 0,
        "quality_score": 0,
        "supplier_reliability_score": 0,
        "logistics_score": 0,
    }
    assert compute_final_score(sub_scores) == 0.0


def test_compute_final_score_example():
    """
    Exemple du cahier des charges : score 88/100 pour un produit avec
    beaucoup de ventes, léger, marge intéressante, concurrence élevée (logistique moyenne).
    """
    sub_scores = {
        "demand_score": 95,
        "margin_score": 90,
        "quality_score": 85,
        "supplier_reliability_score": 80,
        "logistics_score": 90,
    }
    score = compute_final_score(sub_scores)
    # 95*0.3 + 90*0.25 + 85*0.2 + 80*0.15 + 90*0.10 = 28.5+22.5+17+12+9 = 89.0
    assert score == 89.0

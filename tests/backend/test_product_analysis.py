"""
Tests unitaires : service d'analyse produit, en particulier la détection
locale de mots-clés pièges (filet de sécurité indépendant de l'IA).
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from ai_engine.services.product_analysis_service import detect_trap_keywords


def test_detect_case_only():
    text = "Cooltech CP25 protective case only"
    found = detect_trap_keywords(text)
    assert "case only" in found
    assert "only" in found


def test_detect_no_battery():
    text = "Replacement battery pack, no battery included"
    found = detect_trap_keywords(text)
    assert "no battery included" in found


def test_detect_without_charger():
    text = "USB-C fast charging cable without charger"
    found = detect_trap_keywords(text)
    assert "without charger" in found


def test_no_false_positive_on_clean_text():
    text = "Complete wireless earbuds set with charging case and cable included"
    found = detect_trap_keywords(text)
    # "case" seul ne doit pas matcher "case only"
    assert "case only" not in found


def test_detect_replacement_part():
    text = "iPhone 13 screen replacement part, DIY repair kit"
    found = detect_trap_keywords(text)
    assert "replacement part" in found


def test_detect_accessory_only():
    text = "Car phone holder accessory only, phone not included"
    found = detect_trap_keywords(text)
    assert "accessory only" in found

"""
Tests : étapes du scan guidé (`backend/app/api/scan_guide.py`).

- Tests directs sur `SCAN_GUIDE_STEPS` (rapides, sans passer par le serveur HTTP).
- Un test d'intégration légère de l'endpoint via TestClient sur l'app complète.
"""
from fastapi.testclient import TestClient

from app.api.scan_guide import SCAN_GUIDE_STEPS
from app.main import app

CANONICAL_CATEGORIES = {"main_page", "product_info", "shop", "reviews", "shipping"}


def test_exactly_twelve_steps():
    assert len(SCAN_GUIDE_STEPS) == 12


def test_exactly_five_required_steps():
    required_steps = [step for step in SCAN_GUIDE_STEPS if step.required]
    assert len(required_steps) == 5


def test_required_steps_cover_all_five_canonical_categories():
    required_categories = {step.category for step in SCAN_GUIDE_STEPS if step.required}
    assert required_categories == CANONICAL_CATEGORIES


def test_step_numbers_are_unique_and_within_range():
    step_numbers = [step.step for step in SCAN_GUIDE_STEPS]
    assert len(step_numbers) == len(set(step_numbers)), "les numéros d'étape doivent être uniques"
    assert all(1 <= n <= 12 for n in step_numbers)


def test_all_step_categories_are_canonical():
    for step in SCAN_GUIDE_STEPS:
        assert step.category in CANONICAL_CATEGORIES


def test_all_steps_have_non_empty_instruction():
    for step in SCAN_GUIDE_STEPS:
        assert isinstance(step.instruction, str)
        assert step.instruction.strip() != ""


def test_endpoint_returns_200_and_twelve_steps_with_expected_keys():
    client = TestClient(app)
    response = client.get("/api/v1/scan-guide/steps")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 12

    for item in payload:
        assert set(["step", "instruction", "category", "required"]).issubset(item.keys())

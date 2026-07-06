"""
Tests unitaires : service de calcul du coût d'importation
(`backend/app/services/import_estimate_service.py`).

Calcul 100% déterministe (aucun appel réseau/IA), donc pas de mock nécessaire ici.

NB robustesse : on n'importe PAS de valeurs numériques codées en dur pour les
recopier dans nos assertions. Les tarifs de transport et le taux de change ont
justement déjà été rendus configurables via `Settings` par un chantier parallèle
(`app.core.config.settings.IMPORT_AIR_RATE_CNY_PER_KG` / `IMPORT_SEA_RATE_CNY_PER_KG`
/ `IMPORT_EUR_CNY_RATE`, cf. `app/core/config.py`) : ce ne sont donc plus des
constantes de module dans `import_estimate_service.py`. On lit ces valeurs
directement depuis `settings` (la même source de vérité utilisée par le service
au moment de l'exécution) et on calcule nos valeurs attendues à partir de là,
pour rester robuste même si les valeurs par défaut changent. Les seuils de
recommandation (`MARGIN_THRESHOLD_BUY_PCT`, `MARGIN_THRESHOLD_AVOID_PCT`), eux,
sont toujours des constantes de module et sont importés tels quels.
"""
from app.core.config import settings
from app.schemas.import_estimate import ImportEstimateRequest
from app.services.import_estimate_service import (
    MARGIN_THRESHOLD_AVOID_PCT,
    MARGIN_THRESHOLD_BUY_PCT,
    compute_import_estimate,
)

AIR_RATE_CNY_PER_KG = settings.IMPORT_AIR_RATE_CNY_PER_KG
SEA_RATE_CNY_PER_KG = settings.IMPORT_SEA_RATE_CNY_PER_KG
EUR_CNY_RATE = settings.IMPORT_EUR_CNY_RATE


def test_simple_case_air_transport_manual_calculation():
    """
    Cas simple, valeurs rondes, vérifiées à la main à partir des constantes du module :
    - product_cost = 100 CNY * 2 = 200 CNY
    - transport = 2 kg * AIR_RATE_CNY_PER_KG
    - customs = 0 (taux à 0%)
    - total = product_cost + transport
    """
    payload = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=2,
        weight_kg=2.0,
        transport_method="air",
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    expected_product_cost = 200.0
    expected_transport_cost = round(2.0 * AIR_RATE_CNY_PER_KG, 2)
    expected_total_cost = round(expected_product_cost + expected_transport_cost, 2)

    assert result.product_cost_cny == expected_product_cost
    assert result.transport_cost_cny == expected_transport_cost
    assert result.customs_cost_cny == 0.0
    assert result.total_cost_cny == expected_total_cost
    assert result.total_cost_eur_estimated == round(expected_total_cost * EUR_CNY_RATE, 2)
    assert result.cost_per_unit_cny == round(expected_total_cost / 2, 2)


def test_air_vs_sea_transport_costs_differ():
    base_kwargs = dict(product_price_cny=100.0, quantity=1, weight_kg=10.0, customs_duty_rate_pct=0)

    air_result = compute_import_estimate(ImportEstimateRequest(transport_method="air", **base_kwargs))
    sea_result = compute_import_estimate(ImportEstimateRequest(transport_method="sea", **base_kwargs))

    assert air_result.transport_cost_cny == round(10.0 * AIR_RATE_CNY_PER_KG, 2)
    assert sea_result.transport_cost_cny == round(10.0 * SEA_RATE_CNY_PER_KG, 2)
    # Le fret aérien indicatif est toujours plus cher que le maritime dans ce modèle.
    assert air_result.transport_cost_cny > sea_result.transport_cost_cny
    assert air_result.total_cost_cny != sea_result.total_cost_cny


def test_user_shipping_cost_takes_priority_over_estimation():
    payload = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=1,
        weight_kg=50.0,  # poids élevé : l'estimation automatique serait très différente
        transport_method="air",
        user_shipping_cost_cny=42.0,
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert result.transport_cost_cny == 42.0
    # Le coût réel utilisateur ne doit pas correspondre à l'estimation au poids/tarif.
    assert result.transport_cost_cny != round(50.0 * AIR_RATE_CNY_PER_KG, 2)
    assert any("utilisateur" in a.lower() for a in result.assumptions)


def test_recommendation_acheter_when_margin_at_or_above_buy_threshold():
    # cost_per_unit_eur choisi très bas pour garantir une marge >= seuil ACHETER.
    payload = ImportEstimateRequest(
        product_price_cny=10.0,
        quantity=1,
        weight_kg=0.1,
        transport_method="sea",
        target_selling_price_eur=100.0,
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert result.margin_percentage is not None
    assert result.margin_percentage >= MARGIN_THRESHOLD_BUY_PCT
    assert result.recommendation == "ACHETER"


def test_recommendation_ne_pas_acheter_when_margin_below_avoid_threshold():
    # Prix de revente cible très bas par rapport au coût -> marge négative, sous le seuil.
    payload = ImportEstimateRequest(
        product_price_cny=500.0,
        quantity=1,
        weight_kg=20.0,
        transport_method="air",
        target_selling_price_eur=5.0,
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert result.margin_percentage is not None
    assert result.margin_percentage < MARGIN_THRESHOLD_AVOID_PCT
    assert result.recommendation == "NE_PAS_ACHETER"


def test_recommendation_a_etudier_when_margin_between_thresholds():
    # On calcule un prix de revente cible qui place la marge exactement au milieu
    # de l'intervalle [MARGIN_THRESHOLD_AVOID_PCT, MARGIN_THRESHOLD_BUY_PCT).
    payload_no_target = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=1,
        weight_kg=1.0,
        transport_method="sea",
        customs_duty_rate_pct=0,
    )
    baseline = compute_import_estimate(payload_no_target)
    cost_per_unit_eur = baseline.cost_per_unit_eur_estimated

    mid_margin_pct = (MARGIN_THRESHOLD_AVOID_PCT + MARGIN_THRESHOLD_BUY_PCT) / 2
    # margin_pct = (target - cost) / target * 100  =>  target = cost / (1 - margin_pct/100)
    target_price = cost_per_unit_eur / (1 - mid_margin_pct / 100)

    payload = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=1,
        weight_kg=1.0,
        transport_method="sea",
        target_selling_price_eur=round(target_price, 2),
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert result.margin_percentage is not None
    assert MARGIN_THRESHOLD_AVOID_PCT <= result.margin_percentage < MARGIN_THRESHOLD_BUY_PCT
    assert result.recommendation == "A_ETUDIER"


def test_recommendation_a_etudier_when_no_target_price():
    payload = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=1,
        weight_kg=1.0,
        transport_method="air",
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert result.recommendation == "A_ETUDIER"
    assert result.margin_percentage is None
    assert result.margin_amount_eur is None


def test_recommendation_a_etudier_when_target_price_is_zero():
    """Cas limite explicitement géré : prix de revente à 0 -> pas de division par zéro."""
    payload = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=1,
        weight_kg=1.0,
        transport_method="air",
        target_selling_price_eur=0,
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert result.recommendation == "A_ETUDIER"
    assert result.margin_percentage is None


def test_assumptions_never_empty():
    payload = ImportEstimateRequest(
        product_price_cny=50.0,
        quantity=1,
        weight_kg=1.0,
        transport_method="sea",
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert isinstance(result.assumptions, list)
    assert len(result.assumptions) > 0


def test_assumptions_never_empty_even_with_all_optional_fields_set():
    payload = ImportEstimateRequest(
        product_price_cny=50.0,
        quantity=3,
        weight_kg=5.0,
        transport_method="air",
        user_shipping_cost_cny=30.0,
        target_selling_price_eur=25.0,
        customs_duty_rate_pct=15,
    )
    result = compute_import_estimate(payload)

    assert len(result.assumptions) > 0


def test_customs_duty_rate_increases_customs_and_total_cost():
    base_kwargs = dict(product_price_cny=100.0, quantity=1, weight_kg=1.0, transport_method="sea")

    no_duty = compute_import_estimate(ImportEstimateRequest(customs_duty_rate_pct=0, **base_kwargs))
    with_duty = compute_import_estimate(ImportEstimateRequest(customs_duty_rate_pct=20, **base_kwargs))

    assert no_duty.customs_cost_cny == 0.0
    assert with_duty.customs_cost_cny > 0.0
    assert with_duty.total_cost_cny > no_duty.total_cost_cny

    expected_customs = round(
        (with_duty.product_cost_cny + with_duty.transport_cost_cny) * 20 / 100, 2
    )
    assert with_duty.customs_cost_cny == expected_customs


def test_customs_duty_zero_adds_explicit_assumption_warning():
    payload = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=1,
        weight_kg=1.0,
        transport_method="sea",
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert any("douane" in a.lower() and "0%" in a for a in result.assumptions)


def test_recommendation_reasons_never_empty():
    payload = ImportEstimateRequest(
        product_price_cny=100.0,
        quantity=1,
        weight_kg=1.0,
        transport_method="air",
        target_selling_price_eur=200.0,
        customs_duty_rate_pct=0,
    )
    result = compute_import_estimate(payload)

    assert isinstance(result.recommendation_reasons, list)
    assert len(result.recommendation_reasons) > 0

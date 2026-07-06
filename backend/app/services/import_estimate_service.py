"""
Service de calcul du coût d'importation (prix Chine + transport → coût total,
marge, recommandation d'achat).

Calcul PUREMENT déterministe : aucune donnée n'est inventée, aucun appel réseau
ni IA n'est effectué. Toutes les constantes ci-dessous sont indicatives et ne
reflètent pas des tarifs en temps réel — elles sont explicitement signalées
comme telles dans les "assumptions" retournées à l'utilisateur.
"""
from app.core.config import settings
from app.schemas.import_estimate import ImportEstimateRequest, ImportEstimateResponse

# ---------- Constantes indicatives (NON temps réel, à ajuster manuellement) ----------
#
# Les tarifs de transport et le taux de change sont configurables via les variables
# d'environnement IMPORT_AIR_RATE_CNY_PER_KG, IMPORT_SEA_RATE_CNY_PER_KG et
# IMPORT_EUR_CNY_RATE (voir app.core.config.Settings). Les valeurs par défaut restent
# indicatives et ne reflètent pas des tarifs en temps réel.

# Seuils de décision pour la recommandation d'achat (en % de marge).
MARGIN_THRESHOLD_BUY_PCT = 30
MARGIN_THRESHOLD_AVOID_PCT = 10


def compute_import_estimate(payload: ImportEstimateRequest) -> ImportEstimateResponse:
    """
    Calcule le détail du coût d'importation et une recommandation d'achat
    déterministe à partir des seules données fournies par l'utilisateur et des
    constantes indicatives ci-dessus.
    """
    assumptions: list[str] = []

    # ----- Coût produit -----
    product_cost_cny = payload.product_price_cny * payload.quantity

    # ----- Coût transport (donnée utilisateur prioritaire sur l'estimation) -----
    if payload.user_shipping_cost_cny is not None:
        transport_cost_cny = payload.user_shipping_cost_cny
        assumptions.append(
            "Coût de transport réel renseigné par l'utilisateur "
            f"({transport_cost_cny:.2f} CNY) utilisé à la place de l'estimation au kg."
        )
    else:
        transport_rate = (
            settings.IMPORT_AIR_RATE_CNY_PER_KG
            if payload.transport_method == "air"
            else settings.IMPORT_SEA_RATE_CNY_PER_KG
        )
        transport_cost_cny = payload.weight_kg * transport_rate
        method_label = "aérien" if payload.transport_method == "air" else "maritime"
        assumptions.append(
            f"Tarif de transport {method_label} indicatif (non temps réel) utilisé : "
            f"{transport_rate:.2f} CNY/kg, soit {transport_cost_cny:.2f} CNY pour "
            f"{payload.weight_kg} kg."
        )

    # Le taux de change est toujours une hypothèse de calcul, quelle que soit la
    # méthode de transport retenue.
    assumptions.append(
        f"Taux de change indicatif (non temps réel) utilisé : 1 CNY = {settings.IMPORT_EUR_CNY_RATE} EUR."
    )

    # ----- Douane -----
    customs_cost_cny = (product_cost_cny + transport_cost_cny) * payload.customs_duty_rate_pct / 100

    if payload.customs_duty_rate_pct == 0:
        assumptions.append(
            "Droits de douane non pris en compte (taux à 0%), vérifiez le seuil de "
            "franchise et les taxes réelles à l'importation."
        )

    # ----- Totaux -----
    total_cost_cny = product_cost_cny + transport_cost_cny + customs_cost_cny
    total_cost_eur_estimated = total_cost_cny * settings.IMPORT_EUR_CNY_RATE
    cost_per_unit_cny = total_cost_cny / payload.quantity
    cost_per_unit_eur_estimated = total_cost_eur_estimated / payload.quantity

    # ----- Marge et recommandation -----
    margin_amount_eur: float | None = None
    margin_percentage: float | None = None
    recommendation_reasons: list[str] = []

    if payload.target_selling_price_eur is None:
        recommendation = "A_ETUDIER"
        recommendation_reasons.append(
            "Prix de revente cible non fourni : impossible d'estimer la marge."
        )
    elif payload.target_selling_price_eur == 0:
        # Cas limite : un prix de revente cible de 0 ne permet pas de calculer un
        # pourcentage de marge (division par zéro). On ne fabrique pas de valeur.
        recommendation = "A_ETUDIER"
        recommendation_reasons.append(
            "Prix de revente cible à 0 EUR : marge non calculable, renseignez un "
            "prix de revente strictement positif."
        )
    else:
        margin_amount_eur = payload.target_selling_price_eur - cost_per_unit_eur_estimated
        margin_percentage = margin_amount_eur / payload.target_selling_price_eur * 100

        if margin_percentage >= MARGIN_THRESHOLD_BUY_PCT:
            recommendation = "ACHETER"
            recommendation_reasons.append(
                f"Marge estimée de {margin_percentage:.2f}% (≥ {MARGIN_THRESHOLD_BUY_PCT}%) : "
                "opération rentable."
            )
        elif margin_percentage < MARGIN_THRESHOLD_AVOID_PCT:
            recommendation = "NE_PAS_ACHETER"
            recommendation_reasons.append(
                f"Marge estimée de {margin_percentage:.2f}% (< {MARGIN_THRESHOLD_AVOID_PCT}%) : "
                "marge insuffisante, risque financier élevé."
            )
        else:
            recommendation = "A_ETUDIER"
            recommendation_reasons.append(
                f"Marge estimée de {margin_percentage:.2f}% (entre {MARGIN_THRESHOLD_AVOID_PCT}% "
                f"et {MARGIN_THRESHOLD_BUY_PCT}%) : rentabilité incertaine, à étudier plus en détail."
            )

    return ImportEstimateResponse(
        product_cost_cny=round(product_cost_cny, 2),
        transport_cost_cny=round(transport_cost_cny, 2),
        customs_cost_cny=round(customs_cost_cny, 2),
        total_cost_cny=round(total_cost_cny, 2),
        total_cost_eur_estimated=round(total_cost_eur_estimated, 2),
        cost_per_unit_cny=round(cost_per_unit_cny, 2),
        cost_per_unit_eur_estimated=round(cost_per_unit_eur_estimated, 2),
        margin_amount_eur=round(margin_amount_eur, 2) if margin_amount_eur is not None else None,
        margin_percentage=round(margin_percentage, 2) if margin_percentage is not None else None,
        recommendation=recommendation,
        recommendation_reasons=recommendation_reasons,
        assumptions=assumptions,
    )

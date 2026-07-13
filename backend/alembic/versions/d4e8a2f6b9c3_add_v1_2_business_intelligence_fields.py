"""add v1.2 business intelligence fields (decision reasons, winning product, competition, data confidence, market positioning, resale ease)

Revision ID: d4e8a2f6b9c3
Revises: c7d2f9a1e5b6
Create Date: 2026-07-13

Ajoute à la table `analyses` les colonnes de la version 1.2 (Business Intelligence &
Import Decision) :
- decision_reasons ("Pourquoi cette décision ?", 5 raisons max)
- winning_product_score / winning_product_explanation (score "produit gagnant" /10)
- competition_level / competition_explanation (indice de concurrence)
- data_confidence (confiance par catégorie : prix/specs/photos/avis/OCR)
- average_market_price / market_positioning / market_positioning_explanation
- resale_ease_rating / resale_ease_explanation (facilité de revente)

NB : le pivot CNY -> FCFA (prix fournisseur, calculateur d'import, ROI) n'ajoute AUCUNE
colonne : ces montants vivent dans la colonne JSON `commercial_estimate` déjà créée par
b1a4e6f2c8d1, dont la forme interne évolue sans migration nécessaire.

Utilise "ADD COLUMN IF NOT EXISTS" (idempotent), comme toutes les migrations précédentes
depuis 5c45dddb51e0 — voir cette migration pour le contexte (Base.metadata.create_all() en
développement peut déjà avoir créé ces colonnes avant que cette migration ne soit appliquée
en production).
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "d4e8a2f6b9c3"
down_revision = "c7d2f9a1e5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS decision_reasons JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS winning_product_score INTEGER')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS winning_product_explanation TEXT'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS competition_level VARCHAR(10)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS competition_explanation TEXT')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS data_confidence JSON')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS average_market_price VARCHAR(200)'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS market_positioning VARCHAR(12)')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS market_positioning_explanation TEXT'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS resale_ease_rating INTEGER')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS resale_ease_explanation TEXT')


def downgrade() -> None:
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS resale_ease_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS resale_ease_rating')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS market_positioning_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS market_positioning')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS average_market_price')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS data_confidence')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS competition_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS competition_level')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS winning_product_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS winning_product_score')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS decision_reasons')

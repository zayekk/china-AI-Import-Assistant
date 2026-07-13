"""add v1.1 report fields (language, commercial potential, import decision, market comparisons, demand, quick report)

Revision ID: c7d2f9a1e5b6
Revises: b1a4e6f2c8d1
Create Date: 2026-07-13

Ajoute à la table `analyses` les colonnes de la version 1.1 du rapport d'analyse :
- language (langue de génération du rapport, choisie par l'utilisateur)
- commercial_potential_rating / commercial_potential_explanation (potentiel commercial 1-5,
  généré par l'IA)
- import_decision / import_decision_explanation ("Décision Import" dédiée ; import_decision
  est calculé côté serveur, jamais par l'IA)
- market_comparisons (comparaisons de composants techniques détectés au marché actuel)
- demand_level / demand_explanation (demande de marché estimée)
- quick_report (résumé de lecture ultra-rapide)

NB : utilise "ADD COLUMN IF NOT EXISTS" (idempotent), comme toutes les migrations
précédentes depuis 5c45dddb51e0 — voir cette migration pour le contexte (Base.metadata.
create_all() en développement peut déjà avoir créé ces colonnes avant que cette migration
ne soit appliquée en production).
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "c7d2f9a1e5b6"
down_revision = "b1a4e6f2c8d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS language VARCHAR(2)')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS commercial_potential_rating INTEGER'
    )
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS commercial_potential_explanation TEXT'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS import_decision VARCHAR(10)')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS import_decision_explanation TEXT'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS market_comparisons JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS demand_level VARCHAR(12)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS demand_explanation TEXT')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS quick_report JSON')


def downgrade() -> None:
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS quick_report')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS demand_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS demand_level')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS market_comparisons')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS import_decision_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS import_decision')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS commercial_potential_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS commercial_potential_rating')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS language')

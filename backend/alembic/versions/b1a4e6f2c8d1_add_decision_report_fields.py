"""add decision report fields (alerts, commercial estimate, badge, risk, reliability, margin)

Revision ID: b1a4e6f2c8d1
Revises: 8f249ab434bd
Create Date: 2026-07-06

Ajoute à la table `analyses` les colonnes du rapport de décision enrichi :
- critical_alerts (générées par l'IA : contradictions détectées entre titre/specs/OCR)
- ai_recommendation_summary (synthèse en langage simple générée par l'IA)
- commercial_estimate (coût/revente/marge estimés, ou raison si impossible)
- decision_badge, risk_level, supplier_reliability, margin_potential (toujours calculés
  côté serveur à partir des scores existants, jamais par l'IA)

NB : utilise "ADD COLUMN IF NOT EXISTS" (idempotent) plutôt que op.add_column — voir la
note équivalente dans 5c45dddb51e0 (Base.metadata.create_all() en développement peut déjà
avoir créé ces colonnes avant même que cette migration ne soit appliquée).
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "b1a4e6f2c8d1"
down_revision = "8f249ab434bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS critical_alerts JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS ai_recommendation_summary TEXT')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS commercial_estimate JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS decision_badge VARCHAR(20)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS risk_level VARCHAR(10)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS supplier_reliability VARCHAR(10)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS margin_potential VARCHAR(10)')


def downgrade() -> None:
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS margin_potential')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS supplier_reliability')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS risk_level')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS decision_badge')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS commercial_estimate')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS ai_recommendation_summary')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS critical_alerts')

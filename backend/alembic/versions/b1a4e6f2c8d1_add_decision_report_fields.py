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
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b1a4e6f2c8d1"
down_revision = "8f249ab434bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("critical_alerts", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("ai_recommendation_summary", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("commercial_estimate", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("decision_badge", sa.String(length=20), nullable=True))
    op.add_column("analyses", sa.Column("risk_level", sa.String(length=10), nullable=True))
    op.add_column("analyses", sa.Column("supplier_reliability", sa.String(length=10), nullable=True))
    op.add_column("analyses", sa.Column("margin_potential", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "margin_potential")
    op.drop_column("analyses", "supplier_reliability")
    op.drop_column("analyses", "risk_level")
    op.drop_column("analyses", "decision_badge")
    op.drop_column("analyses", "commercial_estimate")
    op.drop_column("analyses", "ai_recommendation_summary")
    op.drop_column("analyses", "critical_alerts")

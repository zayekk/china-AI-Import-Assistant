"""add analysis confidence and detected/estimated data fields

Revision ID: 5c45dddb51e0
Revises:
Create Date: 2026-07-01

Ajoute à la table `analyses` les colonnes permettant de séparer explicitement :
- les données détectées telles quelles dans le texte source (detected_data)
- les estimations/déductions de l'IA, jamais présentées comme des faits (ai_estimations)
- les informations manquantes pour trancher (missing_information)
- un score de confiance et sa justification (confidence_score, confidence_level,
  confidence_reasons, confidence_risks)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5c45dddb51e0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("detected_data", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("ai_estimations", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("missing_information", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("confidence_score", sa.String(length=10), nullable=True))
    op.add_column("analyses", sa.Column("confidence_level", sa.String(length=20), nullable=True))
    op.add_column("analyses", sa.Column("confidence_reasons", sa.JSON(), nullable=True))
    op.add_column("analyses", sa.Column("confidence_risks", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("analyses", "confidence_risks")
    op.drop_column("analyses", "confidence_reasons")
    op.drop_column("analyses", "confidence_level")
    op.drop_column("analyses", "confidence_score")
    op.drop_column("analyses", "missing_information")
    op.drop_column("analyses", "ai_estimations")
    op.drop_column("analyses", "detected_data")

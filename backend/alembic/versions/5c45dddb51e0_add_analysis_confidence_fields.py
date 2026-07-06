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

NB : utilise "ADD COLUMN IF NOT EXISTS" (idempotent) plutôt que op.add_column, car
`backend/app/main.py` crée automatiquement les tables via `Base.metadata.create_all()`
en environnement de développement (`APP_ENV=development`) — si l'app a un jour tourné
en pointant vers une base neuve avec ce réglage, ces colonnes existent déjà et un
op.add_column classique échouerait avec "DuplicateColumn".
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "5c45dddb51e0"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS detected_data JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS ai_estimations JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS missing_information JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS confidence_score VARCHAR(10)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(20)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS confidence_reasons JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS confidence_risks JSON')


def downgrade() -> None:
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS confidence_risks')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS confidence_reasons')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS confidence_level')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS confidence_score')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS missing_information')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS ai_estimations')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS detected_data')

"""add v1.3 advanced analysis fields (customer reviews, supplier profile, target audience, import strategy, seasonality, saturation, complementary products, logistics, import difficulty, marketing claims, importer summary)

Revision ID: e5f9c3a7d2b1
Revises: d4e8a2f6b9c3
Create Date: 2026-07-14

Ajoute à la table `analyses` les colonnes de la version 1.3 (analyse produit avancée) :
- reviews_available / review_highlights / review_complaints / review_recurring_defects /
  review_satisfaction (ce que disent réellement les clients)
- supplier_profile (profil du vendeur ; overall_trust calculé côté serveur)
- target_audiences / target_audience_explanation (public cible)
- import_strategy (stratégie commerciale d'import)
- seasonality (analyse saisonnière)
- saturation_level / saturation_explanation (saturation du marché, distincte de la concurrence)
- complementary_products (accessoires pertinents suggérés)
- logistics_profile / recommended_transport / transport_explanation (analyse logistique)
- import_difficulty / import_difficulty_explanation (difficulté d'importation)
- marketing_claims (détection de termes marketing trompeurs réellement présents)
- importer_summary (résumé structuré final)

Utilise "ADD COLUMN IF NOT EXISTS" (idempotent), comme toutes les migrations précédentes
depuis 5c45dddb51e0 — voir cette migration pour le contexte (Base.metadata.create_all() en
développement peut déjà avoir créé ces colonnes à partir des modèles avant que cette migration
ne soit appliquée en production ; un op.add_column() classique planterait alors avec
DuplicateColumn).
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "e5f9c3a7d2b1"
down_revision = "d4e8a2f6b9c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS reviews_available BOOLEAN')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS review_highlights JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS review_complaints JSON')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS review_recurring_defects JSON'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS review_satisfaction VARCHAR(12)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS supplier_profile JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS target_audiences JSON')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS target_audience_explanation TEXT'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS import_strategy JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS seasonality JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS saturation_level VARCHAR(24)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS saturation_explanation TEXT')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS complementary_products JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS logistics_profile JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS recommended_transport VARCHAR(10)')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS transport_explanation TEXT')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS import_difficulty VARCHAR(12)')
    op.execute(
        'ALTER TABLE analyses ADD COLUMN IF NOT EXISTS import_difficulty_explanation TEXT'
    )
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS marketing_claims JSON')
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS importer_summary JSON')


def downgrade() -> None:
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS importer_summary')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS marketing_claims')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS import_difficulty_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS import_difficulty')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS transport_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS recommended_transport')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS logistics_profile')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS complementary_products')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS saturation_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS saturation_level')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS seasonality')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS import_strategy')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS target_audience_explanation')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS target_audiences')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS supplier_profile')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS review_satisfaction')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS review_recurring_defects')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS review_complaints')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS review_highlights')
    op.execute('ALTER TABLE analyses DROP COLUMN IF EXISTS reviews_available')

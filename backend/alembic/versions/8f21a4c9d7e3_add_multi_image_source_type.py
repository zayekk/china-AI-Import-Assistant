"""add multi_image value to analysissourcetype enum

Revision ID: 8f21a4c9d7e3
Revises: 5c45dddb51e0
Create Date: 2026-07-02

Le module "analyse multi-captures" (POST /analyze-images) et le "scan guidé"
persistent leurs résultats avec `AnalysisSourceType.MULTI_IMAGE`. Le type enum
PostgreSQL `analysissourcetype` créé lors de la première migration ne contenait
que TEXT/IMAGE/URL : sans cette migration, toute tentative de persistance d'une
analyse multi-captures échoue en base ("invalid input value for enum").
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "8f21a4c9d7e3"
down_revision = "5c45dddb51e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE ne peut pas s'exécuter dans le même bloc de
    # transaction qu'une utilisation de cette valeur, mais l'ajout seul est
    # supporté en transaction depuis PostgreSQL 12 (projet sur PostgreSQL 16).
    op.execute("ALTER TYPE analysissourcetype ADD VALUE IF NOT EXISTS 'MULTI_IMAGE'")


def downgrade() -> None:
    # PostgreSQL ne permet pas de retirer une valeur d'un type enum sans
    # recréer le type et migrer toutes les colonnes qui l'utilisent : ce
    # downgrade est volontairement un no-op, comme c'est l'usage standard
    # pour les ajouts de valeurs enum sous PostgreSQL.
    pass

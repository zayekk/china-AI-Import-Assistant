"""add mobile summary and analysis captures table

Revision ID: 8f249ab434bd
Revises: 8f21a4c9d7e3
Create Date: 2026-07-03 21:48:01.792933

Deux ajouts liés à la persistance des analyses :

1. Colonne `mobile_summary` sur `analyses` : résumé compact sur une ligne, calculé
   côté serveur (jamais par l'IA) via `_normalize_ai_result()`, destiné au futur
   affichage dans une bulle flottante mobile (voir docs/mobile_architecture.md,
   section 5).

2. Table `analysis_captures` : une ligne par capture d'une analyse multi-captures
   (`POST /analyze-images`), liée à l'analyse parente (`ON DELETE CASCADE`). Avant
   cette migration, ce détail (catégorie, doublon, extrait OCR) n'existait que noyé
   dans la colonne JSON `raw_ai_response` de `analyses`, donc impossible à
   interroger/filtrer efficacement en base.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '8f249ab434bd'
down_revision = '8f21a4c9d7e3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("analyses", sa.Column("mobile_summary", sa.String(length=500), nullable=True))

    op.create_table(
        "analysis_captures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capture_index", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duplicate_of_index", sa.Integer(), nullable=True),
        sa.Column("ocr_excerpt", sa.Text(), nullable=True),
        sa.Column("ocr_failed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["analysis_id"], ["analyses.id"], ondelete="CASCADE", name="fk_analysis_captures_analysis_id"
        ),
    )
    # Les requêtes par analyse (récupérer toutes les captures d'une analyse donnée)
    # seront fréquentes -> index dédié sur la clé étrangère.
    op.create_index(
        "ix_analysis_captures_analysis_id", "analysis_captures", ["analysis_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_captures_analysis_id", table_name="analysis_captures")
    op.drop_table("analysis_captures")
    op.drop_column("analyses", "mobile_summary")

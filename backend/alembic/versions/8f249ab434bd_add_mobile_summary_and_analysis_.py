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


# revision identifiers, used by Alembic.
revision = '8f249ab434bd'
down_revision = '8f21a4c9d7e3'
branch_labels = None
depends_on = None

# NB : toutes les opérations utilisent des variantes "IF NOT EXISTS"/raw SQL (idempotent)
# plutôt que op.add_column/op.create_table/op.create_index, car `backend/app/main.py`
# crée automatiquement les tables via `Base.metadata.create_all()` en développement
# (APP_ENV=development) — voir la note équivalente dans 5c45dddb51e0.


def upgrade() -> None:
    op.execute('ALTER TABLE analyses ADD COLUMN IF NOT EXISTS mobile_summary VARCHAR(500)')

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_captures (
            id UUID NOT NULL PRIMARY KEY,
            analysis_id UUID NOT NULL,
            capture_index INTEGER NOT NULL,
            filename VARCHAR(500),
            category VARCHAR(50),
            is_duplicate BOOLEAN NOT NULL DEFAULT false,
            duplicate_of_index INTEGER,
            ocr_excerpt TEXT,
            ocr_failed BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            CONSTRAINT fk_analysis_captures_analysis_id
                FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
        )
        """
    )
    # Les requêtes par analyse (récupérer toutes les captures d'une analyse donnée)
    # seront fréquentes -> index dédié sur la clé étrangère.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_analysis_captures_analysis_id "
        "ON analysis_captures (analysis_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_analysis_captures_analysis_id")
    op.execute("DROP TABLE IF EXISTS analysis_captures")
    op.execute("ALTER TABLE analyses DROP COLUMN IF EXISTS mobile_summary")

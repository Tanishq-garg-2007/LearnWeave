"""Round 3 constraints: one quiz per lesson, one roadmap version number per roadmap.

Revision ID: e4a7c1f9b203
Revises: 7c2e9b1d4f10
Create Date: 2026-10-17

Existing duplicates are merged before the constraints are added:
- Duplicate quizzes for a lesson are merged into the earliest one. Attempts are re-pointed to the
  survivor, so no graded history is deleted. (The attempts keep the scores they were given.)
- Duplicate roadmap version numbers keep the earliest snapshot.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e4a7c1f9b203"
down_revision: Union[str, Sequence[str], None] = "7c2e9b1d4f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- assessments: one quiz per lesson ---
    op.execute(
        """
        WITH ranked AS (
            SELECT id, lesson_id,
                   ROW_NUMBER() OVER (PARTITION BY lesson_id ORDER BY created_at, id) AS rn,
                   FIRST_VALUE(id) OVER (PARTITION BY lesson_id ORDER BY created_at, id) AS keep_id
            FROM assessments
        )
        UPDATE assessment_attempts AS aa
        SET assessment_id = ranked.keep_id
        FROM ranked
        WHERE aa.assessment_id = ranked.id AND ranked.rn > 1
        """
    )
    op.execute(
        """
        DELETE FROM assessments WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY lesson_id ORDER BY created_at, id
                ) AS rn
                FROM assessments
            ) ranked
            WHERE ranked.rn > 1
        )
        """
    )
    op.create_unique_constraint("uq_assessment_lesson", "assessments", ["lesson_id"])

    # --- roadmap_versions: one row per (roadmap, version number) ---
    op.execute(
        """
        DELETE FROM roadmap_versions WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY roadmap_id, version_number ORDER BY created_at, id
                ) AS rn
                FROM roadmap_versions
            ) ranked
            WHERE ranked.rn > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_roadmap_version_number", "roadmap_versions", ["roadmap_id", "version_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_roadmap_version_number", "roadmap_versions", type_="unique")
    op.drop_constraint("uq_assessment_lesson", "assessments", type_="unique")

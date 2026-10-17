"""Round 1 integrity constraints: per-user idempotency keys, single active cycle per lesson,
one report per reporter per note.

Revision ID: 7c2e9b1d4f10
Revises: 1adf92ff4c6e
Create Date: 2026-10-16

Existing rows are de-duplicated before the constraints are added, so the migration can run
against a populated database. Superseded duplicate cycles are marked 'skipped'; duplicate
reports keep the earliest row.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c2e9b1d4f10"
down_revision: Union[str, Sequence[str], None] = "1adf92ff4c6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- note_reports: one report per (reporter, note) ---
    op.execute(
        """
        DELETE FROM note_reports WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY reporter_id, note_id ORDER BY created_at, id
                ) AS rn
                FROM note_reports
            ) ranked
            WHERE ranked.rn > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_note_report_reporter_note", "note_reports", ["reporter_id", "note_id"]
    )

    # --- cycle_runs: at most one active cycle per (user, lesson) ---
    op.execute(
        """
        UPDATE cycle_runs SET status = 'skipped', error_message = 'superseded by duplicate-cycle cleanup'
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY user_id, lesson_id ORDER BY created_at DESC, id DESC
                ) AS rn
                FROM cycle_runs
                WHERE status IN ('pending', 'running', 'paused')
            ) ranked
            WHERE ranked.rn > 1
        )
        """
    )
    op.create_index(
        "uq_cycle_active_user_lesson",
        "cycle_runs",
        ["user_id", "lesson_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'running', 'paused')"),
    )

    # --- cycle_runs: idempotency keys are unique per user, not globally ---
    op.drop_index("ix_cycle_runs_idempotency_key", table_name="cycle_runs")
    op.create_index("ix_cycle_runs_idempotency_key", "cycle_runs", ["idempotency_key"], unique=False)
    op.create_unique_constraint(
        "uq_cycle_user_idempotency", "cycle_runs", ["user_id", "idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_cycle_user_idempotency", "cycle_runs", type_="unique")
    op.drop_index("ix_cycle_runs_idempotency_key", table_name="cycle_runs")
    op.create_index("ix_cycle_runs_idempotency_key", "cycle_runs", ["idempotency_key"], unique=True)

    op.drop_index("uq_cycle_active_user_lesson", table_name="cycle_runs")

    op.drop_constraint("uq_note_report_reporter_note", "note_reports", type_="unique")

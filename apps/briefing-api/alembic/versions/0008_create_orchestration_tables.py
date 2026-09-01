"""create orchestration tables

Revision ID: 0008_orchestration_tables
Revises: 0007_email_delivery_logs
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_orchestration_tables"
down_revision: str | None = "0007_email_delivery_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("pending", "running", "success", "partial_success", "failed", "skipped", "cancelled")
RUN_TYPES = ("daily", "window", "manual")
STEP_NAMES = (
    "ingestion",
    "normalization",
    "clustering",
    "event_analysis",
    "digest_build",
    "email_preview",
    "email_send",
)


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "orchestration_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("digest_date", sa.Date(), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lock_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("triggered_by", sa.String(length=100), server_default="manual", nullable=False),
        sa.Column("dry_run", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("email_send_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("continue_on_ai_failure", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("recipient_emails", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("digest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_check_values(STATUSES)})",
            name="ck_orchestration_runs_status",
        ),
        sa.CheckConstraint(
            f"run_type IN ({_check_values(RUN_TYPES)})",
            name="ck_orchestration_runs_run_type",
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_orchestration_runs_duration_non_negative",
        ),
        sa.CheckConstraint(
            "window_start IS NULL OR window_end IS NULL OR window_start < window_end",
            name="ck_orchestration_runs_valid_window",
        ),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orchestration_runs_lock_key", "orchestration_runs", ["lock_key"])
    op.create_index(
        "ix_orchestration_runs_idempotency_key",
        "orchestration_runs",
        ["idempotency_key"],
    )
    op.create_index("ix_orchestration_runs_status", "orchestration_runs", ["status"])
    op.create_index("ix_orchestration_runs_run_type", "orchestration_runs", ["run_type"])
    op.create_index("ix_orchestration_runs_digest_date", "orchestration_runs", ["digest_date"])
    op.create_index("ix_orchestration_runs_window_start", "orchestration_runs", ["window_start"])
    op.create_index("ix_orchestration_runs_window_end", "orchestration_runs", ["window_end"])
    op.create_index("ix_orchestration_runs_digest_id", "orchestration_runs", ["digest_id"])
    op.create_index("ix_orchestration_runs_started_at", "orchestration_runs", ["started_at"])
    op.create_index("ix_orchestration_runs_finished_at", "orchestration_runs", ["finished_at"])
    op.create_index("ix_orchestration_runs_created_at", "orchestration_runs", ["created_at"])

    op.create_table(
        "orchestration_run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("items_processed", sa.Integer(), nullable=True),
        sa.Column("items_created", sa.Integer(), nullable=True),
        sa.Column("items_failed", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_check_values(STATUSES)})",
            name="ck_orchestration_run_steps_status",
        ),
        sa.CheckConstraint(
            f"step_name IN ({_check_values(STEP_NAMES)})",
            name="ck_orchestration_run_steps_step_name",
        ),
        sa.CheckConstraint(
            "step_order > 0",
            name="ck_orchestration_run_steps_order_positive",
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_orchestration_run_steps_duration_non_negative",
        ),
        sa.CheckConstraint(
            "items_processed IS NULL OR items_processed >= 0",
            name="ck_orchestration_run_steps_processed_non_negative",
        ),
        sa.CheckConstraint(
            "items_created IS NULL OR items_created >= 0",
            name="ck_orchestration_run_steps_created_non_negative",
        ),
        sa.CheckConstraint(
            "items_failed IS NULL OR items_failed >= 0",
            name="ck_orchestration_run_steps_failed_non_negative",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["orchestration_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_orchestration_run_steps_run_step_unique",
        "orchestration_run_steps",
        ["run_id", "step_name"],
        unique=True,
    )
    op.create_index(
        "ix_orchestration_run_steps_run_order_unique",
        "orchestration_run_steps",
        ["run_id", "step_order"],
        unique=True,
    )
    op.create_index("ix_orchestration_run_steps_run_id", "orchestration_run_steps", ["run_id"])
    op.create_index(
        "ix_orchestration_run_steps_step_name",
        "orchestration_run_steps",
        ["step_name"],
    )
    op.create_index("ix_orchestration_run_steps_status", "orchestration_run_steps", ["status"])
    op.create_index(
        "ix_orchestration_run_steps_step_order",
        "orchestration_run_steps",
        ["step_order"],
    )
    op.create_index(
        "ix_orchestration_run_steps_started_at",
        "orchestration_run_steps",
        ["started_at"],
    )
    op.create_index(
        "ix_orchestration_run_steps_finished_at",
        "orchestration_run_steps",
        ["finished_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_orchestration_run_steps_finished_at", table_name="orchestration_run_steps")
    op.drop_index("ix_orchestration_run_steps_started_at", table_name="orchestration_run_steps")
    op.drop_index("ix_orchestration_run_steps_step_order", table_name="orchestration_run_steps")
    op.drop_index("ix_orchestration_run_steps_status", table_name="orchestration_run_steps")
    op.drop_index("ix_orchestration_run_steps_step_name", table_name="orchestration_run_steps")
    op.drop_index("ix_orchestration_run_steps_run_id", table_name="orchestration_run_steps")
    op.drop_index(
        "ix_orchestration_run_steps_run_order_unique",
        table_name="orchestration_run_steps",
    )
    op.drop_index(
        "ix_orchestration_run_steps_run_step_unique",
        table_name="orchestration_run_steps",
    )
    op.drop_table("orchestration_run_steps")
    op.drop_index("ix_orchestration_runs_created_at", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_finished_at", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_started_at", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_digest_id", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_window_end", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_window_start", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_digest_date", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_run_type", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_status", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_idempotency_key", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_lock_key", table_name="orchestration_runs")
    op.drop_table("orchestration_runs")

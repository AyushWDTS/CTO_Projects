"""create data quality tables

Revision ID: 0010_data_quality_tables
Revises: 0008_orchestration_tables
Create Date: 2026-06-02 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_data_quality_tables"
down_revision: str | None = "0008_orchestration_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HEALTH_STATUSES = ("healthy", "degraded", "failing", "skipped")
RUN_STATUSES = ("running", "success", "failed")
SEVERITIES = ("info", "warning", "error", "critical")
SCOPE_TYPES = (
    "source",
    "raw_document",
    "article",
    "event",
    "analysis",
    "digest",
    "orchestration_run",
    "system",
)


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "source_health_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=True),
        sa.Column("content_size_bytes", sa.Integer(), nullable=True),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_check_values(HEALTH_STATUSES)})",
            name="ck_source_health_checks_status",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_source_health_checks_latency_non_negative",
        ),
        sa.CheckConstraint(
            "http_status IS NULL OR (http_status >= 100 AND http_status <= 599)",
            name="ck_source_health_checks_http_status_range",
        ),
        sa.CheckConstraint(
            "item_count IS NULL OR item_count >= 0",
            name="ck_source_health_checks_item_count_non_negative",
        ),
        sa.CheckConstraint(
            "content_size_bytes IS NULL OR content_size_bytes >= 0",
            name="ck_source_health_checks_content_size_non_negative",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= checked_at",
            name="ck_source_health_checks_finished_after_checked",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_health_checks_source_id", "source_health_checks", ["source_id"])
    op.create_index("ix_source_health_checks_status", "source_health_checks", ["status"])
    op.create_index("ix_source_health_checks_checked_at", "source_health_checks", ["checked_at"])
    op.create_index("ix_source_health_checks_created_at", "source_health_checks", ["created_at"])
    op.create_index(
        "ix_source_health_checks_source_checked_at",
        "source_health_checks",
        ["source_id", "checked_at"],
    )

    op.create_table(
        "data_quality_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="running", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("scope_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("min_severity", sa.String(length=50), nullable=True),
        sa.Column("total_findings", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"status IN ({_check_values(RUN_STATUSES)})",
            name="ck_data_quality_runs_status",
        ),
        sa.CheckConstraint(
            f"min_severity IS NULL OR min_severity IN ({_check_values(SEVERITIES)})",
            name="ck_data_quality_runs_min_severity",
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_data_quality_runs_duration_non_negative",
        ),
        sa.CheckConstraint(
            "total_findings >= 0",
            name="ck_data_quality_runs_total_non_negative",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_data_quality_runs_finished_after_started",
        ),
        sa.ForeignKeyConstraint(["scope_source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_quality_runs_status", "data_quality_runs", ["status"])
    op.create_index(
        "ix_data_quality_runs_scope_source_id",
        "data_quality_runs",
        ["scope_source_id"],
    )
    op.create_index("ix_data_quality_runs_min_severity", "data_quality_runs", ["min_severity"])
    op.create_index("ix_data_quality_runs_started_at", "data_quality_runs", ["started_at"])
    op.create_index("ix_data_quality_runs_created_at", "data_quality_runs", ["created_at"])

    op.create_table(
        "data_quality_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_name", sa.String(length=100), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"severity IN ({_check_values(SEVERITIES)})",
            name="ck_data_quality_findings_severity",
        ),
        sa.CheckConstraint(
            f"scope_type IN ({_check_values(SCOPE_TYPES)})",
            name="ck_data_quality_findings_scope_type",
        ),
        sa.CheckConstraint(
            "check_name <> ''",
            name="ck_data_quality_findings_check_name_non_empty",
        ),
        sa.CheckConstraint("message <> ''", name="ck_data_quality_findings_message_non_empty"),
        sa.ForeignKeyConstraint(["run_id"], ["data_quality_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_quality_findings_run_id", "data_quality_findings", ["run_id"])
    op.create_index("ix_data_quality_findings_severity", "data_quality_findings", ["severity"])
    op.create_index("ix_data_quality_findings_check_name", "data_quality_findings", ["check_name"])
    op.create_index("ix_data_quality_findings_scope_type", "data_quality_findings", ["scope_type"])
    op.create_index("ix_data_quality_findings_scope_id", "data_quality_findings", ["scope_id"])
    op.create_index("ix_data_quality_findings_source_id", "data_quality_findings", ["source_id"])
    op.create_index("ix_data_quality_findings_created_at", "data_quality_findings", ["created_at"])
    op.create_index(
        "ix_data_quality_findings_run_severity",
        "data_quality_findings",
        ["run_id", "severity"],
    )
    op.create_index(
        "ix_data_quality_findings_source_severity",
        "data_quality_findings",
        ["source_id", "severity"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_quality_findings_source_severity", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_run_severity", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_created_at", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_source_id", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_scope_id", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_scope_type", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_check_name", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_severity", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_run_id", table_name="data_quality_findings")
    op.drop_table("data_quality_findings")

    op.drop_index("ix_data_quality_runs_created_at", table_name="data_quality_runs")
    op.drop_index("ix_data_quality_runs_started_at", table_name="data_quality_runs")
    op.drop_index("ix_data_quality_runs_min_severity", table_name="data_quality_runs")
    op.drop_index("ix_data_quality_runs_scope_source_id", table_name="data_quality_runs")
    op.drop_index("ix_data_quality_runs_status", table_name="data_quality_runs")
    op.drop_table("data_quality_runs")

    op.drop_index("ix_source_health_checks_source_checked_at", table_name="source_health_checks")
    op.drop_index("ix_source_health_checks_created_at", table_name="source_health_checks")
    op.drop_index("ix_source_health_checks_checked_at", table_name="source_health_checks")
    op.drop_index("ix_source_health_checks_status", table_name="source_health_checks")
    op.drop_index("ix_source_health_checks_source_id", table_name="source_health_checks")
    op.drop_table("source_health_checks")

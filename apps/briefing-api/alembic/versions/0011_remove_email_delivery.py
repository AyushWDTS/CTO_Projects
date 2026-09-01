"""remove email delivery infrastructure

Revision ID: 0011_remove_email_delivery
Revises: 0010_data_quality_tables
Create Date: 2026-08-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011_remove_email_delivery"
down_revision: str | None = "0010_data_quality_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STEP_NAMES = ("ingestion", "normalization", "clustering", "event_analysis", "digest_build")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "email_delivery_logs" in inspector.get_table_names():
        op.drop_table("email_delivery_logs")

    if "orchestration_runs" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("orchestration_runs")}
        if "email_send_enabled" in columns:
            op.drop_column("orchestration_runs", "email_send_enabled")
        if "recipient_emails" in columns:
            op.drop_column("orchestration_runs", "recipient_emails")

    if "orchestration_run_steps" in inspector.get_table_names():
        op.execute(
            "DELETE FROM orchestration_run_steps "
            "WHERE step_name IN ('email_preview', 'email_send')"
        )
        constraints = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("orchestration_run_steps")
        }
        if "ck_orchestration_run_steps_step_name" in constraints:
            op.drop_constraint(
                "ck_orchestration_run_steps_step_name",
                "orchestration_run_steps",
                type_="check",
            )
        allowed_steps = ", ".join(f"'{step}'" for step in STEP_NAMES)
        op.create_check_constraint(
            "ck_orchestration_run_steps_step_name",
            "orchestration_run_steps",
            f"step_name IN ({allowed_steps})",
        )


def downgrade() -> None:
    raise NotImplementedError("Email delivery removal cannot be safely downgraded.")

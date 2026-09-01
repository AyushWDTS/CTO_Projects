"""create email delivery logs

Revision ID: 0007_email_delivery_logs
Revises: 0006_create_digest_tables
Create Date: 2026-06-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_email_delivery_logs"
down_revision: str | None = "0006_create_digest_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("pending", "rendered", "sent", "failed", "skipped")


def _check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "email_delivery_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("html_size_bytes", sa.Integer(), nullable=True),
        sa.Column("text_size_bytes", sa.Integer(), nullable=True),
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
            name="ck_email_delivery_logs_status",
        ),
        sa.CheckConstraint(
            "html_size_bytes IS NULL OR html_size_bytes >= 0",
            name="ck_email_delivery_logs_html_size_non_negative",
        ),
        sa.CheckConstraint(
            "text_size_bytes IS NULL OR text_size_bytes >= 0",
            name="ck_email_delivery_logs_text_size_non_negative",
        ),
        sa.ForeignKeyConstraint(["digest_id"], ["digests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_delivery_logs_digest_id", "email_delivery_logs", ["digest_id"])
    op.create_index(
        "ix_email_delivery_logs_recipient_email",
        "email_delivery_logs",
        ["recipient_email"],
    )
    op.create_index("ix_email_delivery_logs_status", "email_delivery_logs", ["status"])
    op.create_index(
        "ix_email_delivery_logs_provider_message_id",
        "email_delivery_logs",
        ["provider_message_id"],
    )
    op.create_index("ix_email_delivery_logs_created_at", "email_delivery_logs", ["created_at"])
    op.create_index("ix_email_delivery_logs_sent_at", "email_delivery_logs", ["sent_at"])


def downgrade() -> None:
    op.drop_index("ix_email_delivery_logs_sent_at", table_name="email_delivery_logs")
    op.drop_index("ix_email_delivery_logs_created_at", table_name="email_delivery_logs")
    op.drop_index("ix_email_delivery_logs_provider_message_id", table_name="email_delivery_logs")
    op.drop_index("ix_email_delivery_logs_status", table_name="email_delivery_logs")
    op.drop_index("ix_email_delivery_logs_recipient_email", table_name="email_delivery_logs")
    op.drop_index("ix_email_delivery_logs_digest_id", table_name="email_delivery_logs")
    op.drop_table("email_delivery_logs")

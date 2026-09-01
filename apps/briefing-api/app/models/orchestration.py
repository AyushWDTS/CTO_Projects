from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrchestrationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class OrchestrationRunType(StrEnum):
    DAILY = "daily"
    WINDOW = "window"
    MANUAL = "manual"


class OrchestrationStepName(StrEnum):
    INGESTION = "ingestion"
    NORMALIZATION = "normalization"
    CLUSTERING = "clustering"
    EVENT_ANALYSIS = "event_analysis"
    DIGEST_BUILD = "digest_build"


def enum_check_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{value.value}'" for value in enum_type)


class OrchestrationRun(Base):
    __tablename__ = "orchestration_runs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_check_values(OrchestrationStatus)})",
            name="ck_orchestration_runs_status",
        ),
        CheckConstraint(
            f"run_type IN ({enum_check_values(OrchestrationRunType)})",
            name="ck_orchestration_runs_run_type",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_orchestration_runs_duration_non_negative",
        ),
        CheckConstraint(
            "window_start IS NULL OR window_end IS NULL OR window_start < window_end",
            name="ck_orchestration_runs_valid_window",
        ),
        Index("ix_orchestration_runs_lock_key", "lock_key"),
        Index("ix_orchestration_runs_idempotency_key", "idempotency_key"),
        Index("ix_orchestration_runs_status", "status"),
        Index("ix_orchestration_runs_run_type", "run_type"),
        Index("ix_orchestration_runs_digest_date", "digest_date"),
        Index("ix_orchestration_runs_window_start", "window_start"),
        Index("ix_orchestration_runs_window_end", "window_end"),
        Index("ix_orchestration_runs_digest_id", "digest_id"),
        Index("ix_orchestration_runs_started_at", "started_at"),
        Index("ix_orchestration_runs_finished_at", "finished_at"),
        Index("ix_orchestration_runs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OrchestrationStatus.PENDING.value,
        server_default=OrchestrationStatus.PENDING.value,
    )
    digest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(100), nullable=False, default="manual")
    dry_run: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    continue_on_ai_failure: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
    )
    digest_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("digests.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    digest = relationship("Digest")
    steps = relationship(
        "OrchestrationRunStep",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="OrchestrationRunStep.step_order",
    )


class OrchestrationRunStep(Base):
    __tablename__ = "orchestration_run_steps"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_check_values(OrchestrationStatus)})",
            name="ck_orchestration_run_steps_status",
        ),
        CheckConstraint(
            f"step_name IN ({enum_check_values(OrchestrationStepName)})",
            name="ck_orchestration_run_steps_step_name",
        ),
        CheckConstraint("step_order > 0", name="ck_orchestration_run_steps_order_positive"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_orchestration_run_steps_duration_non_negative",
        ),
        CheckConstraint(
            "items_processed IS NULL OR items_processed >= 0",
            name="ck_orchestration_run_steps_processed_non_negative",
        ),
        CheckConstraint(
            "items_created IS NULL OR items_created >= 0",
            name="ck_orchestration_run_steps_created_non_negative",
        ),
        CheckConstraint(
            "items_failed IS NULL OR items_failed >= 0",
            name="ck_orchestration_run_steps_failed_non_negative",
        ),
        Index("ix_orchestration_run_steps_run_step_unique", "run_id", "step_name", unique=True),
        Index("ix_orchestration_run_steps_run_order_unique", "run_id", "step_order", unique=True),
        Index("ix_orchestration_run_steps_run_id", "run_id"),
        Index("ix_orchestration_run_steps_step_name", "step_name"),
        Index("ix_orchestration_run_steps_status", "status"),
        Index("ix_orchestration_run_steps_step_order", "step_order"),
        Index("ix_orchestration_run_steps_started_at", "started_at"),
        Index("ix_orchestration_run_steps_finished_at", "finished_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("orchestration_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step_order: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OrchestrationStatus.PENDING.value,
        server_default=OrchestrationStatus.PENDING.value,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    items_processed: Mapped[int | None] = mapped_column(nullable=True)
    items_created: Mapped[int | None] = mapped_column(nullable=True)
    items_failed: Mapped[int | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    run = relationship("OrchestrationRun", back_populates="steps")

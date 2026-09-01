from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SourceHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    SKIPPED = "skipped"


class DataQualityRunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DataQualitySeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DataQualityScopeType(StrEnum):
    SOURCE = "source"
    RAW_DOCUMENT = "raw_document"
    ARTICLE = "article"
    EVENT = "event"
    ANALYSIS = "analysis"
    DIGEST = "digest"
    ORCHESTRATION_RUN = "orchestration_run"
    SYSTEM = "system"


def enum_check_values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{value.value}'" for value in enum_type)


class SourceHealthCheck(Base):
    __tablename__ = "source_health_checks"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_check_values(SourceHealthStatus)})",
            name="ck_source_health_checks_status",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_source_health_checks_latency_non_negative",
        ),
        CheckConstraint(
            "http_status IS NULL OR (http_status >= 100 AND http_status <= 599)",
            name="ck_source_health_checks_http_status_range",
        ),
        CheckConstraint(
            "item_count IS NULL OR item_count >= 0",
            name="ck_source_health_checks_item_count_non_negative",
        ),
        CheckConstraint(
            "content_size_bytes IS NULL OR content_size_bytes >= 0",
            name="ck_source_health_checks_content_size_non_negative",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= checked_at",
            name="ck_source_health_checks_finished_after_checked",
        ),
        Index("ix_source_health_checks_source_id", "source_id"),
        Index("ix_source_health_checks_status", "status"),
        Index("ix_source_health_checks_checked_at", "checked_at"),
        Index("ix_source_health_checks_created_at", "created_at"),
        Index("ix_source_health_checks_source_checked_at", "source_id", "checked_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    health_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    source = relationship("Source")


class DataQualityRun(Base):
    __tablename__ = "data_quality_runs"
    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_check_values(DataQualityRunStatus)})",
            name="ck_data_quality_runs_status",
        ),
        CheckConstraint(
            f"min_severity IS NULL OR min_severity IN ({enum_check_values(DataQualitySeverity)})",
            name="ck_data_quality_runs_min_severity",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_data_quality_runs_duration_non_negative",
        ),
        CheckConstraint("total_findings >= 0", name="ck_data_quality_runs_total_non_negative"),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_data_quality_runs_finished_after_started",
        ),
        Index("ix_data_quality_runs_status", "status"),
        Index("ix_data_quality_runs_scope_source_id", "scope_source_id"),
        Index("ix_data_quality_runs_min_severity", "min_severity"),
        Index("ix_data_quality_runs_started_at", "started_at"),
        Index("ix_data_quality_runs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=DataQualityRunStatus.RUNNING.value,
        server_default=DataQualityRunStatus.RUNNING.value,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope_source_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    min_severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    total_findings: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    run_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scope_source = relationship("Source")
    findings = relationship(
        "DataQualityFinding",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class DataQualityFinding(Base):
    __tablename__ = "data_quality_findings"
    __table_args__ = (
        CheckConstraint(
            f"severity IN ({enum_check_values(DataQualitySeverity)})",
            name="ck_data_quality_findings_severity",
        ),
        CheckConstraint(
            f"scope_type IN ({enum_check_values(DataQualityScopeType)})",
            name="ck_data_quality_findings_scope_type",
        ),
        CheckConstraint("check_name <> ''", name="ck_data_quality_findings_check_name_non_empty"),
        CheckConstraint("message <> ''", name="ck_data_quality_findings_message_non_empty"),
        Index("ix_data_quality_findings_run_id", "run_id"),
        Index("ix_data_quality_findings_severity", "severity"),
        Index("ix_data_quality_findings_check_name", "check_name"),
        Index("ix_data_quality_findings_scope_type", "scope_type"),
        Index("ix_data_quality_findings_scope_id", "scope_id"),
        Index("ix_data_quality_findings_source_id", "source_id"),
        Index("ix_data_quality_findings_created_at", "created_at"),
        Index("ix_data_quality_findings_run_severity", "run_id", "severity"),
        Index("ix_data_quality_findings_source_severity", "source_id", "severity"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("data_quality_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    source_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    finding_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run = relationship("DataQualityRun", back_populates="findings")
    source = relationship("Source")

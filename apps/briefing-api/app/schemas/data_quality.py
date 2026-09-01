from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.data_quality import (
    DataQualityRunStatus,
    DataQualityScopeType,
    DataQualitySeverity,
    SourceHealthStatus,
)


class SourceHealthCheckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    status: SourceHealthStatus
    checked_at: datetime
    finished_at: datetime | None = None
    latency_ms: int | None = None
    http_status: int | None = None
    item_count: int | None = None
    content_size_bytes: int | None = None
    error_reason: str | None = None
    recommendation: str | None = None
    metadata: dict | None = Field(
        default=None,
        validation_alias="health_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime


class SourceHealthCheckList(BaseModel):
    items: list[SourceHealthCheckRead]
    total: int
    limit: int
    offset: int


class DataQualityRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DataQualityRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: int | None = None
    scope_source_id: UUID | None = None
    min_severity: DataQualitySeverity | None = None
    total_findings: int
    metadata: dict | None = Field(
        default=None,
        validation_alias="run_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime


class DataQualityFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    check_name: str
    scope_type: DataQualityScopeType
    scope_id: UUID | None = None
    source_id: UUID | None = None
    severity: DataQualitySeverity
    message: str
    recommendation: str | None = None
    metadata: dict | None = Field(
        default=None,
        validation_alias="finding_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime


class DataQualityFindingList(BaseModel):
    items: list[DataQualityFindingRead]
    total: int
    limit: int
    offset: int


class DataQualityRunResult(BaseModel):
    run: DataQualityRunRead
    severity_counts: dict[str, int]
    findings: list[DataQualityFindingRead]


class SourceHealthRunResult(BaseModel):
    total_sources: int
    status_counts: dict[str, int]
    results: list[SourceHealthCheckRead]


class DataQualitySummary(BaseModel):
    latest_run: DataQualityRunRead | None = None
    severity_counts: dict[str, int]
    source_health_counts: dict[str, int]
    latest_findings: list[DataQualityFindingRead]

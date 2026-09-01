from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.orchestration import (
    OrchestrationRunType,
    OrchestrationStatus,
    OrchestrationStepName,
)


class OrchestrationRunRequest(BaseModel):
    digest_date: date | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    dry_run: bool = True
    skip_ingestion: bool = False
    skip_normalization: bool = False
    skip_clustering: bool = False
    skip_ai: bool = False
    continue_on_ai_failure: bool = False
    refresh_digest: bool = False
    demo_mode: bool = False
    limit: int = Field(default=100, ge=1, le=500)
    digest_limit: int = Field(default=15, ge=1, le=50)
    triggered_by: str = Field(default="manual", max_length=100)

    @model_validator(mode="after")
    def validate_window(self) -> "OrchestrationRunRequest":
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError("window_start and window_end must be provided together")
        if self.window_start is not None and self.window_end is not None:
            if self.window_start >= self.window_end:
                raise ValueError("window_start must be before window_end")
        return self


class OrchestrationRunStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_id: UUID
    step_name: OrchestrationStepName
    step_order: int
    status: OrchestrationStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: int | None = None
    items_processed: int | None = None
    items_created: int | None = None
    items_failed: int | None = None
    error_message: str | None = None
    metadata: dict | None = Field(
        default=None,
        validation_alias="step_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class OrchestrationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    run_type: OrchestrationRunType
    status: OrchestrationStatus
    digest_date: date | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    lock_key: str
    idempotency_key: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: int | None = None
    triggered_by: str
    dry_run: bool
    continue_on_ai_failure: bool
    digest_id: UUID | None = None
    error_message: str | None = None
    metadata: dict | None = Field(
        default=None,
        validation_alias="run_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime
    updated_at: datetime


class OrchestrationRunDetail(OrchestrationRunRead):
    steps: list[OrchestrationRunStepRead] = Field(default_factory=list)


class OrchestrationRunList(BaseModel):
    items: list[OrchestrationRunRead]
    total: int
    limit: int
    offset: int


class OrchestrationRunStepList(BaseModel):
    items: list[OrchestrationRunStepRead]
    total: int
    limit: int
    offset: int


class OrchestrationRunResult(BaseModel):
    run: OrchestrationRunDetail

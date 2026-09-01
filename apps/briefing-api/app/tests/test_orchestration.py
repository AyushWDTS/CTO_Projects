from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import engine
from app.db.session import get_db
from app.main import app
from app.models.digest import Digest
from app.models.orchestration import (
    OrchestrationRun,
    OrchestrationRunStep,
    OrchestrationStatus,
    OrchestrationStepName,
)
from app.schemas.clustering import ClusteringBatchResult
from app.schemas.event_analysis import EventAIAnalysisBatchResult
from app.schemas.ingestion import IngestionBatchResult
from app.schemas.normalization import NormalizationBatchResult
from app.services import orchestration_service
from app.services.orchestration_service import (
    OrchestrationInvalidRequestError,
    OrchestrationRunAlreadyActiveError,
    run_daily_pipeline,
)
from app.workers.celery_app import celery_app

BASE_DATE = date(2026, 6, 1)
WINDOW_START = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
WINDOW_END = WINDOW_START + timedelta(days=1)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def api_client(db: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def clean_orchestration_data(db: Session) -> None:
    db.execute(delete(OrchestrationRunStep))
    db.execute(delete(OrchestrationRun))
    db.execute(delete(Digest))
    db.commit()


def install_successful_step_mocks(monkeypatch: pytest.MonkeyPatch) -> dict:

    monkeypatch.setattr(
        orchestration_service,
        "ingest_all_sources",
        lambda db: IngestionBatchResult(total_sources=1, results=[]),
    )
    monkeypatch.setattr(
        orchestration_service,
        "normalize_pending_raw_documents",
        lambda db, limit: NormalizationBatchResult(total_raw_documents=1, results=[]),
    )
    monkeypatch.setattr(
        orchestration_service,
        "normalize_priority_sources",
        lambda db, limit_per_source: {
            "stage": "normalization",
            "limit_per_source": limit_per_source,
            "sources_processed": 0,
            "results": [],
        },
    )
    monkeypatch.setattr(
        orchestration_service,
        "cluster_pending_articles",
        lambda db, limit: ClusteringBatchResult(total_articles=1, linked_articles=1),
    )
    monkeypatch.setattr(
        orchestration_service,
        "cluster_priority_sources",
        lambda db, limit_per_source: {
            "stage": "clustering",
            "limit_per_source": limit_per_source,
            "sources_processed": 0,
            "results": [],
        },
    )
    monkeypatch.setattr(
        orchestration_service,
        "analyze_pending_events",
        lambda db, limit: EventAIAnalysisBatchResult(total_events=1, analyzed=1),
    )
    monkeypatch.setattr(
        orchestration_service,
        "analyze_clustered_priority_sources",
        lambda db, limit_per_source: {
            "stage": "event_analysis",
            "limit_per_source": limit_per_source,
            "sources_processed": 0,
            "total_failed": 0,
            "results": [],
        },
    )
    monkeypatch.setattr(
        orchestration_service,
        "analyze_priority_sources",
        lambda db, limit_per_source, **kwargs: {
            "stage": "event_analysis",
            "limit_per_source": limit_per_source,
            "sources_processed": 0,
            "total_failed": 0,
            "results": [],
        },
    )
    def fake_build_digest(db, *args, **kwargs):
        digest = Digest(
            digest_date=BASE_DATE,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
            title=f"Orchestration Test Digest {uuid4()}",
            status="draft",
            total_candidates=3,
            total_selected=2,
        )
        db.add(digest)
        db.flush()
        return digest

    monkeypatch.setattr(orchestration_service, "build_digest", fake_build_digest)
    return {}


def test_full_dry_run_records_ordered_steps_without_real_send(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clean_orchestration_data(db)
    install_successful_step_mocks(monkeypatch)

    run = run_daily_pipeline(
        db,
        digest_date=BASE_DATE,
        settings=Settings(ORCHESTRATION_DEFAULT_DRY_RUN=True),
    )

    assert run.status == OrchestrationStatus.SUCCESS.value
    assert run.lock_key
    assert run.idempotency_key
    assert run.digest_id is not None
    assert [step.step_name for step in run.steps] == [
        step.value for step in orchestration_service.STEP_SEQUENCE
    ]
    assert len(run.steps) == 5
    assert run.steps[-1].step_name == OrchestrationStepName.DIGEST_BUILD.value
    assert run.steps[-1].status == OrchestrationStatus.SUCCESS.value


def test_ai_failure_stops_by_default(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    clean_orchestration_data(db)
    install_successful_step_mocks(monkeypatch)
    monkeypatch.setattr(
        orchestration_service,
        "analyze_pending_events",
        lambda db, limit: EventAIAnalysisBatchResult(total_events=1, failed=1),
    )

    run = run_daily_pipeline(db, digest_date=BASE_DATE, settings=Settings())
    steps = {step.step_name: step for step in run.steps}

    assert run.status == OrchestrationStatus.FAILED.value
    assert steps[OrchestrationStepName.EVENT_ANALYSIS.value].status == OrchestrationStatus.FAILED
    assert steps[OrchestrationStepName.DIGEST_BUILD.value].status == OrchestrationStatus.SKIPPED
    for step_name in [OrchestrationStepName.DIGEST_BUILD.value]:
        assert steps[step_name].step_metadata["reason"] == "upstream_failed"
        assert steps[step_name].step_metadata["failed_step"] == "event_analysis"
        assert steps[step_name].finished_at is not None


def test_earlier_failure_marks_downstream_pending_steps_skipped(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clean_orchestration_data(db)
    install_successful_step_mocks(monkeypatch)

    def fail_normalization(db, limit):
        raise RuntimeError("normalization_failed")

    monkeypatch.setattr(
        orchestration_service,
        "normalize_pending_raw_documents",
        fail_normalization,
    )

    run = run_daily_pipeline(db, digest_date=BASE_DATE, settings=Settings())
    steps = {step.step_name: step for step in run.steps}

    assert run.status == OrchestrationStatus.FAILED.value
    assert steps[OrchestrationStepName.INGESTION.value].status == OrchestrationStatus.SUCCESS
    assert steps[OrchestrationStepName.NORMALIZATION.value].status == OrchestrationStatus.FAILED
    for step_name in [
        OrchestrationStepName.CLUSTERING.value,
        OrchestrationStepName.EVENT_ANALYSIS.value,
        OrchestrationStepName.DIGEST_BUILD.value,
    ]:
        assert steps[step_name].status == OrchestrationStatus.SKIPPED
        assert steps[step_name].step_metadata == {
            "reason": "upstream_failed",
            "failed_step": "normalization",
        }


def test_continue_on_ai_failure_records_partial_success(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clean_orchestration_data(db)
    install_successful_step_mocks(monkeypatch)
    monkeypatch.setattr(
        orchestration_service,
        "analyze_pending_events",
        lambda db, limit: EventAIAnalysisBatchResult(total_events=1, failed=1),
    )

    run = run_daily_pipeline(
        db,
        digest_date=BASE_DATE,
        continue_on_ai_failure=True,
        settings=Settings(),
    )

    assert run.status == OrchestrationStatus.PARTIAL_SUCCESS.value
    assert run.digest_id is not None


def test_same_window_lock_prevents_overlap(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clean_orchestration_data(db)
    install_successful_step_mocks(monkeypatch)
    monkeypatch.setattr(orchestration_service, "_try_advisory_lock", lambda db, lock_key: False)

    with pytest.raises(OrchestrationRunAlreadyActiveError):
        run_daily_pipeline(db, digest_date=BASE_DATE, settings=Settings())


def test_api_run_list_read_and_steps(
    db: Session,
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clean_orchestration_data(db)
    install_successful_step_mocks(monkeypatch)

    response = api_client.post(
        "/api/v1/orchestration/daily/run",
        json={"digest_date": BASE_DATE.isoformat()},
    )

    assert response.status_code == 200
    run_id = response.json()["run"]["id"]
    assert api_client.get("/api/v1/orchestration/runs").status_code == 200
    assert api_client.get(f"/api/v1/orchestration/runs/{run_id}").status_code == 200
    assert api_client.get(f"/api/v1/orchestration/runs/{run_id}/steps").status_code == 200


def test_cli_path_and_celery_task_discovery(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    clean_orchestration_data(db)
    install_successful_step_mocks(monkeypatch)

    from app.scripts import run_daily_pipeline as script

    class SessionProxy:
        def __getattr__(self, name: str):
            return getattr(db, name)

        def close(self) -> None:
            return None

    monkeypatch.setattr(script, "SessionLocal", lambda: SessionProxy())
    monkeypatch.setattr(
        "sys.argv",
        ["run_daily_pipeline", "--date", BASE_DATE.isoformat()],
    )
    script.main()

    output = capsys.readouterr().out
    assert '"lock_key"' in output
    assert "app.workers.orchestration_tasks.run_daily_pipeline" in celery_app.tasks
    assert "app.workers.orchestration_tasks.run_pipeline_for_window" in celery_app.tasks
    assert "app.workers.orchestration_tasks.run_pipeline_step" in celery_app.tasks

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.db.session import get_db
from app.main import app
from app.models.article import Article
from app.models.ingestion import RawDocument
from app.models.orchestration import (
    OrchestrationRun,
    OrchestrationRunType,
    OrchestrationStatus,
)
from app.models.source import FetchMethod, Source, SourceType
from app.services.demo_pipeline_service import resolve_demo_fetched_after
from app.services.normalization_service import normalize_pending_raw_documents


@pytest.fixture
def db() -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


def _source(db: Session) -> Source:
    source = Source(
        name=f"Demo Source {uuid4()}",
        url="https://example.com/demo",
        source_type=SourceType.RSS,
        fetch_method=FetchMethod.RSS,
        category="gaming",
        region="US",
        is_active=True,
    )
    db.add(source)
    db.flush()
    return source


def _pending_raw(db: Session, source: Source, fetched_at: datetime) -> RawDocument:
    raw = RawDocument(
        source_id=source.id,
        url=f"https://example.com/demo/{uuid4()}",
        canonical_url=f"https://example.com/demo/{uuid4()}",
        raw_hash=str(uuid4()),
        fetched_at=fetched_at,
        content_type="text/html",
        raw_content="<html><body><h1>Demo story</h1><p>Casino smart table update.</p></body></html>",
        raw_size_bytes=64,
    )
    db.add(raw)
    db.flush()
    return raw


def test_resolve_demo_fetched_after_uses_last_successful_run(db: Session) -> None:
    finished = datetime(2099, 1, 1, 12, 0, tzinfo=UTC)
    db.add(
        OrchestrationRun(
            run_type=OrchestrationRunType.MANUAL.value,
            status=OrchestrationStatus.SUCCESS.value,
            digest_date=finished.date(),
            window_start=finished - timedelta(days=1),
            window_end=finished,
            lock_key="demo-test-lock",
            idempotency_key="demo-test-idem",
            started_at=finished - timedelta(hours=1),
            finished_at=finished,
        )
    )
    db.flush()
    watermark, source, inclusive = resolve_demo_fetched_after(
        db,
        run_started_at=datetime(2026, 6, 24, 8, 0, tzinfo=UTC),
    )
    assert source == "last_successful_run_finished_at"
    assert inclusive is False
    assert watermark == finished


def test_resolve_demo_fetched_after_falls_back_to_run_start() -> None:
    started = datetime(2026, 6, 24, 8, 0, tzinfo=UTC)
    db = MagicMock()
    db.scalar.return_value = None
    watermark, source, inclusive = resolve_demo_fetched_after(db, run_started_at=started)
    assert source == "current_run_started_at"
    assert inclusive is True
    assert watermark == started


def test_normalize_pending_raw_documents_respects_fetched_after(db: Session) -> None:
    source = _source(db)
    watermark = datetime(2026, 6, 24, 8, 0, tzinfo=UTC)
    old_raw = _pending_raw(db, source, watermark - timedelta(hours=2))
    new_raw = _pending_raw(db, source, watermark + timedelta(minutes=5))

    result = normalize_pending_raw_documents(
        db,
        limit=10,
        fetched_after=watermark,
        fetched_after_inclusive=False,
    )

    processed_ids = {item.raw_document_id for item in result.results}
    assert new_raw.id in processed_ids
    assert old_raw.id not in processed_ids
    assert not db.scalar(
        __import__("sqlalchemy").select(Article.id).where(Article.raw_document_id == old_raw.id)
    )

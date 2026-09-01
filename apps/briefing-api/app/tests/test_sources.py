from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import engine
from app.db.session import get_db
from app.main import app
from app.models.source import FetchMethod, Source, SourceType
from app.schemas.source import SourceCreate, SourceUpdate
from app.scripts import seed_sources as seed_sources_script
from app.scripts.seed_sources import seed_sources
from app.services.source_service import (
    DuplicateSourceError,
    activate_source,
    create_source,
    deactivate_source,
    list_sources,
    update_source,
)


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


def source_payload(**overrides: object) -> dict[str, object]:
    suffix = uuid4()
    payload: dict[str, object] = {
        "name": f"Test Source {suffix}",
        "url": f"https://example.com/{suffix}",
        "rss_url": f"https://example.com/{suffix}/feed.xml",
        "source_type": SourceType.RSS.value,
        "category": f"test-category-{suffix}",
        "region": "Test Region",
        "priority": 3,
        "fetch_method": FetchMethod.RSS.value,
        "fetch_frequency_minutes": 60,
        "reliability_score": 0.75,
        "notes": "Created by tests.",
    }
    payload.update(overrides)
    return payload


def test_source_model_defaults(db: Session) -> None:
    source = Source(
        name="Model Default Source",
        url=f"https://example.com/model-{uuid4()}",
        source_type=SourceType.NEWS_SITE,
    )

    db.add(source)
    db.commit()
    db.refresh(source)

    assert source.priority == 3
    assert source.fetch_method == FetchMethod.MANUAL
    assert source.fetch_frequency_minutes == 1440
    assert source.reliability_score == 0.50
    assert source.is_active is True
    assert source.failure_count == 0
    assert source.created_at is not None
    assert source.updated_at is not None


def test_source_schema_validation_errors() -> None:
    with pytest.raises(ValidationError):
        SourceCreate(**source_payload(priority=0))

    with pytest.raises(ValidationError):
        SourceCreate(**source_payload(reliability_score=1.5))

    with pytest.raises(ValidationError):
        SourceCreate(**source_payload(fetch_frequency_minutes=0))


def test_source_service_create_list_filter_update_and_duplicate(db: Session) -> None:
    marker = f"service-category-{uuid4()}"
    created = create_source(db, SourceCreate(**source_payload(category=marker, priority=4)))

    sources, total = list_sources(db, limit=10, offset=0, category=marker, priority=4)

    assert total == 1
    assert sources[0].id == created.id

    updated = update_source(
        db,
        created.id,
        SourceUpdate(name="Updated Service Source", reliability_score=0.85),
    )

    assert updated.name == "Updated Service Source"
    assert float(updated.reliability_score) == 0.85

    with pytest.raises(DuplicateSourceError):
        create_source(db, SourceCreate(**source_payload(url=created.url)))


def test_create_and_retrieve_source_api(api_client: TestClient) -> None:
    create_response = api_client.post("/api/v1/sources", json=source_payload())

    assert create_response.status_code == 201
    created = create_response.json()

    get_response = api_client.get(f"/api/v1/sources/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


def test_list_sources_filters_and_pagination_api(api_client: TestClient) -> None:
    marker = f"api-category-{uuid4()}"

    for index in range(3):
        response = api_client.post(
            "/api/v1/sources",
            json=source_payload(
                name=f"Pagination Source {index}",
                category=marker,
                region="Pagination Region",
                priority=2,
                source_type=SourceType.NEWS_SITE.value,
                fetch_method=FetchMethod.STATIC_HTML.value,
            ),
        )
        assert response.status_code == 201

    list_response = api_client.get(
        "/api/v1/sources",
        params={
            "limit": 2,
            "offset": 1,
            "category": marker,
            "region": "Pagination Region",
            "priority": 2,
            "source_type": SourceType.NEWS_SITE.value,
            "fetch_method": FetchMethod.STATIC_HTML.value,
            "is_active": True,
        },
    )

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2


def test_update_deactivate_activate_and_soft_delete_api(api_client: TestClient) -> None:
    create_response = api_client.post("/api/v1/sources", json=source_payload())
    source_id = create_response.json()["id"]

    update_response = api_client.patch(
        f"/api/v1/sources/{source_id}",
        json={"name": "Updated API Source", "priority": 1},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated API Source"
    assert update_response.json()["priority"] == 1

    delete_response = api_client.delete(f"/api/v1/sources/{source_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["is_active"] is False

    activate_response = api_client.post(f"/api/v1/sources/{source_id}/activate")
    assert activate_response.status_code == 200
    assert activate_response.json()["is_active"] is True

    deactivate_response = api_client.post(f"/api/v1/sources/{source_id}/deactivate")
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False


def test_duplicate_url_and_api_validation_errors(api_client: TestClient) -> None:
    payload = source_payload()
    first_response = api_client.post("/api/v1/sources", json=payload)
    second_response = api_client.post("/api/v1/sources", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    invalid_response = api_client.post("/api/v1/sources", json=source_payload(priority=6))
    assert invalid_response.status_code == 422


def test_service_activate_deactivate(db: Session) -> None:
    source = create_source(db, SourceCreate(**source_payload()))

    deactivated = deactivate_source(db, source.id)
    assert deactivated.is_active is False

    activated = activate_source(db, source.id)
    assert activated.is_active is True


def test_seed_sources_is_idempotent(db: Session) -> None:
    seed_source = SourceCreate(
        name="Seed Idempotency Source",
        url=f"https://example.com/seed-{uuid4()}",
        source_type=SourceType.OTHER,
        category="seed-test",
        region="Test",
        fetch_method=FetchMethod.MANUAL,
    )

    first_result = seed_sources(db, [seed_source])
    second_result = seed_sources(db, [seed_source])

    assert first_result == {"created": 1, "updated": 0}
    assert second_result == {"created": 0, "updated": 1}


def test_seed_sources_migrates_known_catalog_urls(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suffix = uuid4()
    legacy_url = f"https://legacy.example.com/{suffix}"
    new_url = f"https://current.example.com/{suffix}"
    monkeypatch.setattr(
        seed_sources_script,
        "SOURCE_URL_MIGRATIONS",
        {new_url: [legacy_url]},
    )

    legacy = Source(
        name="Legacy Source",
        url=legacy_url,
        source_type=SourceType.REGULATOR,
        category="aml",
        region="US",
        fetch_method=FetchMethod.MANUAL,
    )
    db.add(legacy)
    db.commit()

    seed_source = SourceCreate(
        name="Current Source",
        url=new_url,
        source_type=SourceType.REGULATOR,
        category="aml",
        region="US",
        fetch_method=FetchMethod.STATIC_HTML,
        notes="Verified public press release page for automated static HTML ingestion.",
    )

    result = seed_sources(db, [seed_source])
    db.refresh(legacy)

    assert result == {"created": 0, "updated": 1}
    assert legacy.name == "Current Source"
    assert legacy.url == new_url
    assert legacy.fetch_method == FetchMethod.STATIC_HTML

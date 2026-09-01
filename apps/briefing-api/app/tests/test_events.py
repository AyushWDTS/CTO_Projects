from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import engine
from app.db.session import get_db
from app.main import app


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


def test_event_not_found_responses(api_client: TestClient) -> None:
    missing_id = uuid4()

    event_response = api_client.get(f"/api/v1/events/{missing_id}")
    articles_response = api_client.get(f"/api/v1/events/{missing_id}/articles")

    assert event_response.status_code == 404
    assert articles_response.status_code == 404

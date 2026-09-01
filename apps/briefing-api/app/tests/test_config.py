from app.core.config import Settings


def test_cors_origins_accepts_comma_separated_string() -> None:
    settings = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:3001")

    assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:3001"]


def test_cors_origins_accepts_json_list_string() -> None:
    settings = Settings(CORS_ORIGINS='["http://localhost:3000"]')

    assert settings.CORS_ORIGINS == ["http://localhost:3000"]

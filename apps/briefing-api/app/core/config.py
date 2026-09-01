import json
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


def parse_cors_origins_value(value: str | list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(origin).strip() for origin in value if str(origin).strip()]

    value = value.strip()
    if not value:
        return []

    if value.startswith("["):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise ValueError("CORS_ORIGINS JSON value must be a list")
        return [str(origin).strip() for origin in parsed if str(origin).strip()]

    return [origin.strip() for origin in value.split(",") if origin.strip()]


class CorsEnvSettingsSource(EnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        if field_name == "CORS_ORIGINS" and isinstance(value, str):
            return parse_cors_origins_value(value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class CorsDotEnvSettingsSource(DotEnvSettingsSource):
    def prepare_field_value(
        self, field_name: str, field: Any, value: Any, value_is_complex: bool
    ) -> Any:
        if field_name == "CORS_ORIGINS" and isinstance(value, str):
            return parse_cors_origins_value(value)
        return super().prepare_field_value(field_name, field, value, value_is_complex)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "WDTS News Dashboard"
    APP_ENV: str = "local"
    API_VERSION: str = "v1"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/news_intelligence"
    REDIS_URL: str = "redis://localhost:6379/0"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    LOG_LEVEL: str = "INFO"
    # AI: openai_compatible | gemini | bedrock
    AI_PROVIDER: str = "bedrock"
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = ""
    AI_STRONG_MODEL: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AWS_REGION: str = "ap-south-1"
    AWS_PROFILE: str = "AI-Automation-team"
    # Model ID or application inference profile ARN for Converse
    BEDROCK_MODEL_ID: str = ""
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 2
    AI_MAX_INPUT_CHARS_PER_EVENT: int = 24000
    AI_ESTIMATED_INPUT_COST_PER_1K_TOKENS: float = 0
    AI_ESTIMATED_OUTPUT_COST_PER_1K_TOKENS: float = 0
    APP_PUBLIC_BASE_URL: str = "http://localhost:3000"
    ORCHESTRATION_ENABLED: bool = False
    ORCHESTRATION_DAILY_SCHEDULE_CRON: str = "0 6 * * *"
    ORCHESTRATION_TIMEZONE: str = "UTC"
    ORCHESTRATION_DEFAULT_DRY_RUN: bool = True
    ORCHESTRATION_MAX_RUNTIME_SECONDS: int = 1800
    ORCHESTRATION_LOCK_TIMEOUT_SECONDS: int = 60

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        return parse_cors_origins_value(value)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            CorsEnvSettingsSource(settings_cls),
            CorsDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def import_all_models() -> None:
    """Import models so SQLAlchemy metadata is populated for Alembic."""
    from app.models import (  # noqa: F401
        Article,
        DataQualityFinding,
        DataQualityRun,
        Digest,
        DigestItem,
        EventAIAnalysis,
        EventArticle,
        NewsEvent,
        OrchestrationRun,
        OrchestrationRunStep,
        RawDocument,
        Source,
        SourceFetchLog,
        SourceHealthCheck,
    )

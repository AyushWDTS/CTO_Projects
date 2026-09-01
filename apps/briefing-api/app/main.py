import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.articles import router as articles_router
from app.api.routes.bookmarks import router as bookmarks_router
from app.api.routes.clustering import router as clustering_router
from app.api.routes.data_quality import router as data_quality_router
from app.api.routes.digests import router as digests_router
from app.api.routes.event_analysis import router as event_analysis_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.normalization import router as normalization_router
from app.api.routes.orchestration import router as orchestration_router
from app.api.routes.sources import router as sources_router
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger = logging.getLogger(__name__)
    logger.info("Starting %s", app.title)
    yield


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.API_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(sources_router)
    app.include_router(ingestion_router)
    app.include_router(articles_router)
    app.include_router(normalization_router)
    app.include_router(events_router)
    app.include_router(clustering_router)
    app.include_router(event_analysis_router)
    app.include_router(digests_router)
    app.include_router(bookmarks_router)
    app.include_router(orchestration_router)
    app.include_router(data_quality_router)
    return app


app = create_app()

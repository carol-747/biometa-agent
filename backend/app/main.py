"""
BiometaAgent FastAPI application entry point.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import get_settings
from app.db.database import init_db
from app.api import articles, search, chat, ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting BiometaAgent...")
    init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down BiometaAgent.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="BiometaAgent API",
        description=(
            "Microbe-Metabolite Relationship Retrieval Agent. "
            "Fetches PubMed articles, extracts biomedical entities, "
            "detects relationships, and enables conversational search "
            "powered by Claude AI."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS - allow frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(articles.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(ingestion.router, prefix="/api/v1")

    @app.get("/")
    def root():
        return {
            "name": "BiometaAgent",
            "version": "1.0.0",
            "docs": "/docs",
            "status": "running",
        }

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    return app


app = create_app()

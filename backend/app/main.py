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


def _check_ner_backend() -> str:
    """Return which NER model is active and log a clear status line."""
    try:
        import spacy
        for model_name in ("en_core_sci_sm", "en_core_web_sm"):
            try:
                spacy.load(model_name)
                return model_name
            except OSError:
                continue
    except ImportError:
        pass
    return "none (dictionary + regex only)"


def _check_claude_api() -> bool:
    """Return True if an API key is configured."""
    from app.core.config import get_settings
    key = get_settings().anthropic_api_key
    return bool(key and key != "your_anthropic_api_key_here")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting BiometaAgent...")
    init_db()
    logger.info("Database initialized.")

    ner_model = _check_ner_backend()
    logger.info(f"NER backend : {ner_model}")

    claude_ok = _check_claude_api()
    if claude_ok:
        logger.info("Claude API  : configured")
    else:
        logger.warning(
            "Claude API  : NOT configured — set ANTHROPIC_API_KEY in .env. "
            "The app will run in database-only mode (no conversational AI)."
        )

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

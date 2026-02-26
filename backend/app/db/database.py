"""Database engine, session factory, and initialization."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator
import logging

from app.core.config import get_settings
from app.db.models import Base

logger = logging.getLogger(__name__)


def get_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    return create_engine(url, pool_pre_ping=True, echo=False)


def get_session_factory(engine=None):
    eng = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


_engine = None
_SessionLocal = None


def init_db():
    """Create all tables if they don't exist."""
    global _engine, _SessionLocal
    _engine = get_engine()
    _SessionLocal = get_session_factory(_engine)
    Base.metadata.create_all(bind=_engine)
    logger.info("Database tables created/verified.")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a database session."""
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""Shared pytest fixtures."""
import os
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLITE_URL = "sqlite:///./test_biometa.db"


@pytest.fixture(scope="session")
def sqlite_engine():
    from app.db.models import Base

    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_biometa.db"):
        os.remove("./test_biometa.db")


@pytest.fixture
def db_session(sqlite_engine):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def client(sqlite_engine):
    from app.main import app
    from app.db.database import get_db
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

    def override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    with patch("app.main.init_db", lambda: None):
        app.dependency_overrides[get_db] = override_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

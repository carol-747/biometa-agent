"""Integration tests for FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def client():
    """Create a test client with a mocked database."""
    from app.main import app
    from app.db.database import get_db

    def override_db():
        db = MagicMock()
        db.query.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.offset.return_value.limit.return_value.all.return_value = []
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.query.return_value.all.return_value = []
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "BiometaAgent"


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_articles_list_empty(client):
    res = client.get("/api/v1/articles/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_articles_count(client):
    res = client.get("/api/v1/articles/count")
    assert res.status_code == 200
    assert "count" in res.json()


def test_search_requires_query(client):
    res = client.get("/api/v1/search/")
    assert res.status_code == 422  # Missing required param


def test_search_with_query(client):
    res = client.get("/api/v1/search/", params={"q": "butyrate"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_search_relationships(client):
    res = client.get("/api/v1/search/relationships")
    assert res.status_code == 200


def test_search_network(client):
    res = client.get("/api/v1/search/network")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data


def test_ingest_stats(client):
    res = client.get("/api/v1/ingest/stats")
    assert res.status_code == 200


def test_article_not_found(client):
    res = client.get("/api/v1/articles/99999999")
    assert res.status_code == 404


def test_docs_available(client):
    res = client.get("/docs")
    assert res.status_code == 200

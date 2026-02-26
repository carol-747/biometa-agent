"""Integration tests for FastAPI endpoints using an in-memory SQLite DB."""
# Fixtures (client, sqlite_engine, db_session) are provided by conftest.py


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["name"] == "BiometaAgent"


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
    data = res.json()
    assert "articles" in data
    assert "microbes" in data
    assert "metabolites" in data
    assert "relationships" in data
    assert "relationship_types" in data


def test_article_not_found(client):
    res = client.get("/api/v1/articles/99999999")
    assert res.status_code == 404


def test_docs_available(client):
    res = client.get("/docs")
    assert res.status_code == 200

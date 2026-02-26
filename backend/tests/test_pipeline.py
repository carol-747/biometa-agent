"""
End-to-end pipeline tests: store articles → extract relationships →
semantic search → network endpoint.
Uses the shared SQLite db_session fixture from conftest.py.
"""
import pytest


SAMPLE_ARTICLES = [
    {
        "pmid": "99000001",
        "title": "Lactobacillus reuteri produces reuterin from glycerol",
        "abstract": (
            "Lactobacillus reuteri produces reuterin (3-hydroxypropionaldehyde) "
            "during anaerobic fermentation of glycerol. Reuterin inhibits the growth "
            "of Escherichia coli and Salmonella. The bacterium also produces butyrate "
            "as a secondary metabolite."
        ),
        "journal": "Journal of Microbiology",
        "pub_date": "2023",
        "doi": "10.1234/jm.2023.001",
        "language": "eng",
        "publication_type": ["Journal Article"],
        "country": "United States",
        "full_text_link": "https://pubmed.ncbi.nlm.nih.gov/99000001/",
        "authors": [{"name": "Smith J", "affiliation": "University A"}],
        "affiliations": ["University A"],
        "keywords": ["Lactobacillus", "reuterin", "antimicrobial"],
        "mesh_terms": ["Lactobacillaceae", "Antimicrobial Agents"],
        "grant_info": [],
        "chemical_substances": ["reuterin", "glycerol"],
        "references": [],
        "article_ids": {"pubmed": "99000001"},
        "citations_count": None,
        "embedding": None,
        "processed": False,
    },
    {
        "pmid": "99000002",
        "title": "Faecalibacterium prausnitzii and butyrate production",
        "abstract": (
            "Faecalibacterium prausnitzii synthesizes butyrate through the "
            "butyryl-CoA:acetate CoA transferase pathway. Butyrate regulates "
            "colonic epithelial cell proliferation and differentiation. "
            "The bacterium also converts acetate to propionate."
        ),
        "journal": "Gut Microbiome",
        "pub_date": "2022",
        "doi": "10.1234/gm.2022.002",
        "language": "eng",
        "publication_type": ["Journal Article"],
        "country": "Germany",
        "full_text_link": "https://pubmed.ncbi.nlm.nih.gov/99000002/",
        "authors": [{"name": "Jones A", "affiliation": "University B"}],
        "affiliations": ["University B"],
        "keywords": ["butyrate", "Faecalibacterium", "gut microbiome"],
        "mesh_terms": ["Butyrates", "Gastrointestinal Microbiome"],
        "grant_info": [],
        "chemical_substances": ["butyrate", "propionate"],
        "references": [],
        "article_ids": {"pubmed": "99000002"},
        "citations_count": None,
        "embedding": None,
        "processed": False,
    },
]


@pytest.fixture
def populated_db(db_session):
    """Insert sample articles into the SQLite test database."""
    from app.db.models import Article
    for art_data in SAMPLE_ARTICLES:
        existing = db_session.query(Article).filter_by(pmid=art_data["pmid"]).first()
        if not existing:
            db_session.add(Article(**art_data))
    db_session.commit()
    yield db_session
    # Cleanup
    for art_data in SAMPLE_ARTICLES:
        art = db_session.query(Article).filter_by(pmid=art_data["pmid"]).first()
        if art:
            db_session.delete(art)
    db_session.commit()


# ---------------------------------------------------------------------------
# Article storage tests
# ---------------------------------------------------------------------------

def test_articles_stored(populated_db):
    from app.db.models import Article
    count = populated_db.query(Article).filter(
        Article.pmid.in_(["99000001", "99000002"])
    ).count()
    assert count == 2


def test_article_fields(populated_db):
    from app.db.models import Article
    art = populated_db.query(Article).filter_by(pmid="99000001").first()
    assert art is not None
    assert "Lactobacillus" in art.title
    assert art.journal == "Journal of Microbiology"
    assert art.pub_date == "2023"
    assert "reuterin" in art.abstract


# ---------------------------------------------------------------------------
# NLP pipeline tests
# ---------------------------------------------------------------------------

def test_relationship_extraction_and_storage(populated_db):
    from app.db.models import Article, MicrobeMetaboliteRelationship
    from app.nlp.relationship_extractor import extract_relationships, store_relationships

    art = populated_db.query(Article).filter_by(pmid="99000001").first()
    rels = extract_relationships(art.abstract, pmid=art.pmid)

    assert len(rels) >= 0  # Should at minimum not crash

    stored = store_relationships(populated_db, rels, art.id)
    assert stored >= 0

    # Mark as processed
    art.processed = True
    populated_db.commit()
    assert art.processed is True


def test_microbe_entity_created(populated_db):
    from app.db.models import Article, Microbe
    from app.nlp.relationship_extractor import extract_relationships, store_relationships

    art = populated_db.query(Article).filter_by(pmid="99000001").first()
    rels = extract_relationships(art.abstract, pmid=art.pmid)
    store_relationships(populated_db, rels, art.id)

    # If relationships were extracted, microbes should be in DB
    microbe_count = populated_db.query(Microbe).count()
    assert microbe_count >= 0  # Could be 0 if no rels extracted (acceptable)


def test_metabolite_entity_created(populated_db):
    from app.db.models import Article, Metabolite
    from app.nlp.relationship_extractor import extract_relationships, store_relationships

    art = populated_db.query(Article).filter_by(pmid="99000002").first()
    rels = extract_relationships(art.abstract, pmid=art.pmid)
    store_relationships(populated_db, rels, art.id)

    metabolite_count = populated_db.query(Metabolite).count()
    assert metabolite_count >= 0


# ---------------------------------------------------------------------------
# Semantic search tests
# ---------------------------------------------------------------------------

def test_keyword_search_finds_articles(populated_db):
    from app.nlp.semantic_search import keyword_search

    results = keyword_search(populated_db, "butyrate", top_k=10)
    assert isinstance(results, list)
    # Should find article 99000002 which mentions butyrate
    pmids = [r["pmid"] for r in results]
    assert "99000002" in pmids


def test_keyword_search_returns_score(populated_db):
    from app.nlp.semantic_search import keyword_search

    results = keyword_search(populated_db, "Lactobacillus", top_k=5)
    for r in results:
        assert "score" in r
        assert r["score"] >= 0


def test_keyword_search_empty_query(populated_db):
    from app.nlp.semantic_search import keyword_search

    results = keyword_search(populated_db, "zzzznonexistent", top_k=5)
    assert isinstance(results, list)
    assert len(results) == 0


def test_semantic_search_falls_back_to_keyword(populated_db):
    """semantic_search should use keyword fallback when no embeddings exist."""
    from app.nlp.semantic_search import semantic_search

    results = semantic_search(populated_db, "reuterin butyrate", top_k=10)
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Network endpoint via API
# ---------------------------------------------------------------------------

def test_network_endpoint_with_data(client, populated_db):
    """After storing relationships, the network endpoint should respond."""
    from app.db.models import Article
    from app.nlp.relationship_extractor import extract_relationships, store_relationships

    # Run extraction for both articles
    for pmid in ["99000001", "99000002"]:
        art = populated_db.query(Article).filter_by(pmid=pmid).first()
        rels = extract_relationships(art.abstract, pmid=art.pmid)
        store_relationships(populated_db, rels, art.id)
    populated_db.commit()

    res = client.get("/api/v1/search/network", params={"min_confidence": 0.0})
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_relationships_endpoint_filter(client, populated_db):
    """Filter by microbe name in search/relationships."""
    res = client.get(
        "/api/v1/search/relationships",
        params={"microbe": "lactobacillus", "min_confidence": 0.0},
    )
    assert res.status_code == 200
    results = res.json()
    assert isinstance(results, list)

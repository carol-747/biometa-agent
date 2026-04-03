"""
Semantic search over articles using sentence-transformers embeddings.

Storage strategy (auto-detected at runtime):
  1. pgvector  — native VECTOR column with cosine ANN index (PostgreSQL + pgvector)
  2. JSON      — embeddings stored as JSON float arrays, cosine similarity in Python
  3. keyword   — ILIKE fallback when no embeddings exist at all
"""
import logging
import numpy as np
from typing import Any

logger = logging.getLogger(__name__)

_model = None
MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_DIM = 384


def get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Loaded sentence-transformers model: {MODEL_NAME}")
    except Exception as e:
        logger.warning(f"sentence-transformers unavailable: {e}")
        _model = None
    return _model


def embed_text(text: str) -> list[float] | None:
    model = get_model()
    if model is None or not text:
        return None
    try:
        return model.encode(text, show_progress_bar=False).tolist()
    except Exception as e:
        logger.warning(f"Embedding error: {e}")
        return None


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    model = get_model()
    if model is None:
        return [None] * len(texts)
    try:
        vecs = model.encode(texts, show_progress_bar=False, batch_size=32)
        return [v.tolist() for v in vecs]
    except Exception as e:
        logger.warning(f"Batch embedding error: {e}")
        return [None] * len(texts)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom else 0.0


# ---------------------------------------------------------------------------
# pgvector helpers
# ---------------------------------------------------------------------------

def _pgvector_available(db) -> bool:
    """True when the DB is PostgreSQL and pgvector extension is present."""
    try:
        from sqlalchemy import text
        dialect = db.bind.dialect.name if hasattr(db, "bind") else \
            db.get_bind().dialect.name
        if dialect != "postgresql":
            return False
        result = db.execute(
            text("SELECT 1 FROM pg_extension WHERE extname='vector'")
        ).first()
        return result is not None
    except Exception:
        return False


def _pgvector_search(
    db, query_vec: list[float], top_k: int, min_score: float
) -> list[dict[str, Any]]:
    """Nearest-neighbour search using pgvector cosine distance."""
    from sqlalchemy import text

    vec_str = "[" + ",".join(str(v) for v in query_vec) + "]"
    sql = text("""
        SELECT pmid, title, abstract, journal, pub_date, doi, full_text_link,
               1 - (embedding_vector <=> :vec ::vector) AS score
        FROM articles
        WHERE embedding_vector IS NOT NULL
        ORDER BY embedding_vector <=> :vec ::vector
        LIMIT :top_k
    """)
    rows = db.execute(sql, {"vec": vec_str, "top_k": top_k}).fetchall()
    return [
        {
            "pmid": r.pmid, "title": r.title, "abstract": r.abstract,
            "journal": r.journal, "pub_date": r.pub_date, "doi": r.doi,
            "full_text_link": r.full_text_link,
            "score": round(float(r.score), 4),
        }
        for r in rows
        if float(r.score) >= min_score
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def semantic_search(
    db,
    query: str,
    top_k: int = 20,
    min_score: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Search articles by semantic similarity.
    Auto-detects the best available backend: pgvector → JSON cosine → keyword.
    """
    query_vec = embed_text(query)

    if query_vec is None:
        return keyword_search(db, query, top_k)

    # Try pgvector first
    if _pgvector_available(db):
        try:
            results = _pgvector_search(db, query_vec, top_k, min_score)
            if results:
                return results
        except Exception as e:
            logger.warning(f"pgvector search failed, falling back: {e}")

    # JSON cosine fallback
    return _json_cosine_search(db, query_vec, top_k, min_score)


def _json_cosine_search(
    db, query_vec: list[float], top_k: int, min_score: float
) -> list[dict[str, Any]]:
    """Load JSON embeddings and rank by cosine similarity in Python."""
    from app.db.models import Article

    articles = (
        db.query(Article)
        .filter(Article.embedding.isnot(None))
        .all()
    )

    scored = []
    for art in articles:
        if art.embedding:
            try:
                score = cosine_similarity(query_vec, art.embedding)
                if score >= min_score:
                    scored.append((score, art))
            except Exception:
                pass

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "pmid": art.pmid, "title": art.title, "abstract": art.abstract,
            "journal": art.journal, "pub_date": art.pub_date, "doi": art.doi,
            "full_text_link": art.full_text_link,
            "score": round(score, 4),
        }
        for score, art in scored[:top_k]
    ]


def keyword_search(db, query: str, top_k: int = 20) -> list[dict[str, Any]]:
    """ILIKE keyword search over title and abstract."""
    from app.db.models import Article
    from sqlalchemy import or_

    terms = query.split()
    filters = []
    for term in terms[:5]:
        filters.append(Article.title.ilike(f"%{term}%"))
        filters.append(Article.abstract.ilike(f"%{term}%"))

    articles = (
        db.query(Article)
        .filter(or_(*filters))
        .limit(top_k)
        .all()
    ) if filters else []

    return [
        {
            "pmid": art.pmid, "title": art.title, "abstract": art.abstract,
            "journal": art.journal, "pub_date": art.pub_date, "doi": art.doi,
            "full_text_link": art.full_text_link,
            "score": 0.5,
        }
        for art in articles
    ]


def compute_and_store_embeddings(db, batch_size: int = 64) -> int:
    """
    Compute embeddings for all articles that are missing them.
    Stores in both Article.embedding (JSON) and Article.embedding_vector
    (pgvector, if available) so both backends stay in sync.
    """
    from app.db.models import Article

    use_pgvector = _pgvector_available(db)

    articles = (
        db.query(Article)
        .filter(Article.embedding.is_(None))
        .filter(Article.abstract.isnot(None))
        .all()
    )
    logger.info(
        f"Computing embeddings for {len(articles)} articles "
        f"(pgvector={'on' if use_pgvector else 'off'})"
    )

    updated = 0
    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        texts = [f"{a.title} {a.abstract}" for a in batch]
        vecs = embed_texts(texts)
        for art, vec in zip(batch, vecs):
            if vec:
                art.embedding = vec
                if use_pgvector and hasattr(art, "embedding_vector"):
                    art.embedding_vector = vec
                updated += 1
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Embedding commit error: {e}")
            db.rollback()

    return updated

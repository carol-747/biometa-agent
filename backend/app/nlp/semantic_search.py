"""
Semantic search over articles using sentence-transformers embeddings.
Embeddings are stored as JSON arrays in the database.
"""
import logging
import numpy as np
from typing import Any

logger = logging.getLogger(__name__)

_model = None
MODEL_NAME = "all-MiniLM-L6-v2"  # Small, fast, good for biomedical text


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
    """Embed a text string, return as list of floats (or None if unavailable)."""
    model = get_model()
    if model is None or not text:
        return None
    try:
        vec = model.encode(text, show_progress_bar=False)
        return vec.tolist()
    except Exception as e:
        logger.warning(f"Embedding error: {e}")
        return None


def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """Batch embed multiple texts."""
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
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def semantic_search(
    db_session,
    query: str,
    top_k: int = 20,
    min_score: float = 0.3,
) -> list[dict[str, Any]]:
    """
    Search articles by semantic similarity to query.
    Falls back to keyword search if embeddings unavailable.
    """
    from app.db.models import Article

    query_vec = embed_text(query)

    if query_vec is None:
        # Fallback: basic keyword search
        return keyword_search(db_session, query, top_k)

    # Load articles with embeddings
    articles = (
        db_session.query(Article)
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
    results = []
    for score, art in scored[:top_k]:
        results.append({
            "pmid": art.pmid,
            "title": art.title,
            "abstract": art.abstract,
            "journal": art.journal,
            "pub_date": art.pub_date,
            "doi": art.doi,
            "full_text_link": art.full_text_link,
            "score": round(score, 4),
        })
    return results


def keyword_search(
    db_session,
    query: str,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """Simple ILIKE keyword search over title and abstract."""
    from app.db.models import Article
    from sqlalchemy import or_

    terms = query.split()
    filters = []
    for term in terms[:5]:  # Limit to first 5 terms
        filters.append(Article.title.ilike(f"%{term}%"))
        filters.append(Article.abstract.ilike(f"%{term}%"))

    articles = (
        db_session.query(Article)
        .filter(or_(*filters))
        .limit(top_k)
        .all()
    )

    return [
        {
            "pmid": art.pmid,
            "title": art.title,
            "abstract": art.abstract,
            "journal": art.journal,
            "pub_date": art.pub_date,
            "doi": art.doi,
            "full_text_link": art.full_text_link,
            "score": 0.5,  # arbitrary score for keyword matches
        }
        for art in articles
    ]


def compute_and_store_embeddings(db_session, batch_size: int = 64) -> int:
    """Compute embeddings for all articles missing them."""
    from app.db.models import Article

    articles = (
        db_session.query(Article)
        .filter(Article.embedding.is_(None))
        .filter(Article.abstract.isnot(None))
        .all()
    )
    logger.info(f"Computing embeddings for {len(articles)} articles")

    updated = 0
    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        texts = [f"{a.title} {a.abstract}" for a in batch]
        vecs = embed_texts(texts)
        for art, vec in zip(batch, vecs):
            if vec:
                art.embedding = vec
                updated += 1
        try:
            db_session.commit()
        except Exception as e:
            logger.error(f"Embedding commit error: {e}")
            db_session.rollback()

    return updated

"""
Data ingestion endpoints: fetch PubMed articles and run NLP pipeline.
"""
import logging
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.core.config import get_settings

router = APIRouter(prefix="/ingest", tags=["ingestion"])
logger = logging.getLogger(__name__)

# Track background job status
_job_status: dict[str, dict] = {}


class IngestRequest(BaseModel):
    query: str = "microbe metabolite"
    max_results: int = 1000
    run_nlp: bool = True


class ProcessRequest(BaseModel):
    batch_size: int = 50
    compute_embeddings: bool = True


def _run_ingestion(job_id: str, query: str, max_results: int, run_nlp: bool, db_url: str):
    """Background task: fetch articles and optionally run NLP."""
    from app.db.database import get_engine, get_session_factory
    from app.db.models import Article
    from app.services.pubmed_fetcher import fetch_and_store
    from app.nlp.relationship_extractor import extract_relationships, store_relationships
    from app.nlp.semantic_search import compute_and_store_embeddings

    settings = get_settings()
    engine = get_engine(db_url)
    SessionLocal = get_session_factory(engine)
    db = SessionLocal()

    try:
        _job_status[job_id]["status"] = "fetching"
        stored = fetch_and_store(
            db, query, max_results=max_results, email=settings.entrez_email
        )
        _job_status[job_id]["articles_fetched"] = stored

        if run_nlp:
            _job_status[job_id]["status"] = "extracting_entities"
            articles = (
                db.query(Article)
                .filter(Article.processed == False)
                .filter(Article.abstract.isnot(None))
                .all()
            )
            rel_count = 0
            for art in articles:
                rels = extract_relationships(art.abstract or "", pmid=art.pmid)
                stored_rels = store_relationships(db, rels, art.id)
                rel_count += stored_rels
                art.processed = True
            db.commit()
            _job_status[job_id]["relationships_extracted"] = rel_count

            _job_status[job_id]["status"] = "computing_embeddings"
            emb_count = compute_and_store_embeddings(db)
            _job_status[job_id]["embeddings_computed"] = emb_count

        _job_status[job_id]["status"] = "completed"

    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {e}")
        _job_status[job_id]["status"] = "failed"
        _job_status[job_id]["error"] = str(e)
    finally:
        db.close()


@router.post("/pubmed")
def ingest_pubmed(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Fetch articles from PubMed and store them.
    Runs as a background task, returns job_id to poll status.
    """
    import uuid
    job_id = str(uuid.uuid4())
    _job_status[job_id] = {
        "status": "queued",
        "query": req.query,
        "max_results": req.max_results,
    }

    settings = get_settings()
    background_tasks.add_task(
        _run_ingestion,
        job_id=job_id,
        query=req.query,
        max_results=req.max_results,
        run_nlp=req.run_nlp,
        db_url=settings.database_url,
    )

    return {"job_id": job_id, "status": "queued"}


@router.get("/status/{job_id}")
def ingestion_status(job_id: str):
    """Poll background ingestion job status."""
    if job_id not in _job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_status[job_id]


@router.post("/process")
def process_articles(
    req: ProcessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Run NLP pipeline on already-fetched articles that haven't been processed.
    """
    import uuid
    job_id = str(uuid.uuid4())
    _job_status[job_id] = {"status": "queued"}
    settings = get_settings()

    def _run_processing(job_id: str, db_url: str):
        from app.db.database import get_engine, get_session_factory
        from app.db.models import Article
        from app.nlp.relationship_extractor import extract_relationships, store_relationships
        from app.nlp.semantic_search import compute_and_store_embeddings

        engine = get_engine(db_url)
        SessionLocal = get_session_factory(engine)
        db = SessionLocal()
        try:
            _job_status[job_id]["status"] = "processing"
            articles = (
                db.query(Article)
                .filter(Article.processed == False)
                .filter(Article.abstract.isnot(None))
                .all()
            )
            rel_count = 0
            for art in articles:
                rels = extract_relationships(art.abstract or "", pmid=art.pmid)
                stored_rels = store_relationships(db, rels, art.id)
                rel_count += stored_rels
                art.processed = True
            db.commit()
            _job_status[job_id]["relationships_extracted"] = rel_count

            if req.compute_embeddings:
                emb_count = compute_and_store_embeddings(db)
                _job_status[job_id]["embeddings_computed"] = emb_count

            _job_status[job_id]["status"] = "completed"
        except Exception as e:
            _job_status[job_id]["status"] = "failed"
            _job_status[job_id]["error"] = str(e)
        finally:
            db.close()

    background_tasks.add_task(_run_processing, job_id=job_id, db_url=settings.database_url)
    return {"job_id": job_id, "status": "queued"}


@router.get("/stats")
def ingestion_stats(db: Session = Depends(get_db)):
    """Return database statistics."""
    from app.db.models import Article, Microbe, Metabolite, MicrobeMetaboliteRelationship

    from sqlalchemy import func

    rel_types = (
        db.query(
            MicrobeMetaboliteRelationship.relationship_type,
            func.count(MicrobeMetaboliteRelationship.id),
        )
        .group_by(MicrobeMetaboliteRelationship.relationship_type)
        .all()
    )

    return {
        "articles": db.query(Article).count(),
        "articles_processed": db.query(Article).filter(Article.processed == True).count(),
        "microbes": db.query(Microbe).count(),
        "metabolites": db.query(Metabolite).count(),
        "relationships": db.query(MicrobeMetaboliteRelationship).count(),
        "relationship_types": {rt[0]: rt[1] for rt in rel_types},
    }

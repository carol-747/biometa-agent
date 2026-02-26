"""REST endpoints for articles."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any

from app.db.database import get_db
from app.db.models import Article

router = APIRouter(prefix="/articles", tags=["articles"])


class ArticleOut(BaseModel):
    pmid: str
    title: str
    abstract: str | None
    journal: str | None
    pub_date: str | None
    doi: str | None
    full_text_link: str | None
    authors: Any
    keywords: Any
    mesh_terms: Any
    chemical_substances: Any
    publication_type: Any
    language: str | None
    country: str | None
    citations_count: int | None

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ArticleOut])
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List articles with pagination."""
    return db.query(Article).offset(skip).limit(limit).all()


@router.get("/count")
def count_articles(db: Session = Depends(get_db)):
    return {"count": db.query(Article).count()}


@router.get("/{pmid}", response_model=ArticleOut)
def get_article(pmid: str, db: Session = Depends(get_db)):
    art = db.query(Article).filter_by(pmid=pmid).first()
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")
    return art


@router.get("/{pmid}/relationships")
def get_article_relationships(pmid: str, db: Session = Depends(get_db)):
    """Get all extracted relationships for an article."""
    from app.db.models import MicrobeMetaboliteRelationship

    art = db.query(Article).filter_by(pmid=pmid).first()
    if not art:
        raise HTTPException(status_code=404, detail="Article not found")

    rels = (
        db.query(MicrobeMetaboliteRelationship)
        .filter_by(article_id=art.id)
        .all()
    )
    return [
        {
            "id": r.id,
            "microbe": r.microbe.name,
            "microbe_type": r.microbe.microbe_type,
            "metabolite": r.metabolite.name,
            "metabolite_class": r.metabolite.metabolite_class,
            "relationship_type": r.relationship_type,
            "confidence": r.confidence_score,
            "evidence": r.evidence_sentence,
        }
        for r in rels
    ]

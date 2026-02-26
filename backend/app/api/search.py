"""Search endpoints: semantic and relationship search."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any

from app.db.database import get_db
from app.nlp.semantic_search import semantic_search, keyword_search

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    pmid: str
    title: str
    abstract: str | None
    journal: str | None
    pub_date: str | None
    doi: str | None
    full_text_link: str | None
    score: float


@router.get("/", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=2, description="Search query"),
    top_k: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Semantic + keyword search over articles."""
    results = semantic_search(db, q, top_k=top_k)
    if not results:
        results = keyword_search(db, q, top_k=top_k)
    return results


@router.get("/relationships")
def search_relationships(
    microbe: str | None = Query(None),
    metabolite: str | None = Query(None),
    relationship_type: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Filter relationships by microbe, metabolite, or type."""
    from app.db.models import MicrobeMetaboliteRelationship, Microbe, Metabolite, Article
    from sqlalchemy import and_

    q = (
        db.query(MicrobeMetaboliteRelationship)
        .join(Microbe)
        .join(Metabolite)
        .join(Article)
    )

    filters = [MicrobeMetaboliteRelationship.confidence_score >= min_confidence]

    if microbe:
        filters.append(Microbe.name.ilike(f"%{microbe}%"))
    if metabolite:
        filters.append(Metabolite.name.ilike(f"%{metabolite}%"))
    if relationship_type:
        filters.append(
            MicrobeMetaboliteRelationship.relationship_type == relationship_type
        )

    rels = q.filter(and_(*filters)).offset(skip).limit(limit).all()

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
            "pmid": r.article.pmid,
            "journal": r.article.journal,
            "pub_date": r.article.pub_date,
            "full_text_link": r.article.full_text_link,
        }
        for r in rels
    ]


@router.get("/network")
def get_network(
    microbe: str | None = Query(None),
    metabolite: str | None = Query(None),
    min_confidence: float = Query(0.3, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Return graph data (nodes + edges) for network visualization.
    Compatible with Cytoscape.js format.
    """
    from app.db.models import MicrobeMetaboliteRelationship, Microbe, Metabolite

    q = (
        db.query(MicrobeMetaboliteRelationship)
        .join(Microbe)
        .join(Metabolite)
        .filter(MicrobeMetaboliteRelationship.confidence_score >= min_confidence)
    )

    if microbe:
        q = q.filter(Microbe.name.ilike(f"%{microbe}%"))
    if metabolite:
        q = q.filter(Metabolite.name.ilike(f"%{metabolite}%"))

    rels = q.limit(limit).all()

    nodes: dict[str, dict] = {}
    edges = []

    for r in rels:
        m_id = f"microbe_{r.microbe_id}"
        met_id = f"metabolite_{r.metabolite_id}"

        if m_id not in nodes:
            nodes[m_id] = {
                "data": {
                    "id": m_id,
                    "label": r.microbe.name,
                    "type": "microbe",
                    "entity_type": r.microbe.microbe_type,
                    "mention_count": r.microbe.mention_count,
                }
            }
        if met_id not in nodes:
            nodes[met_id] = {
                "data": {
                    "id": met_id,
                    "label": r.metabolite.name,
                    "type": "metabolite",
                    "entity_type": r.metabolite.metabolite_class,
                    "mention_count": r.metabolite.mention_count,
                }
            }

        edges.append({
            "data": {
                "id": f"rel_{r.id}",
                "source": m_id,
                "target": met_id,
                "label": r.relationship_type,
                "confidence": r.confidence_score,
                "relationship_type": r.relationship_type,
            }
        })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }

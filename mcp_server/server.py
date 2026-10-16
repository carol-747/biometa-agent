"""MCP server exposing the BiometaAgent literature database as tools.

Lets an MCP client (Claude Desktop, Claude Code) query the microbe-metabolite
knowledge base directly. Every result carries its source PMID so answers built
on these tools stay grounded in the literature.

Run:
    pip install "mcp[cli]"
    DATABASE_URL=postgresql://... python mcp_server/server.py

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "biometa": {
          "command": "python",
          "args": ["/abs/path/to/biometa-agent/mcp_server/server.py"],
          "env": {"DATABASE_URL": "postgresql://biometa:biometa_secret@localhost:5432/biometa_db"}
        }
      }
    }
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from mcp.server.fastmcp import FastMCP  # noqa: E402
from sqlalchemy import or_  # noqa: E402

from app.db.database import get_session_factory  # noqa: E402
from app.db.models import (Article, Metabolite, Microbe,  # noqa: E402
                           MicrobeMetaboliteRelationship)
from app.nlp.relationship_extractor import extract_relationships  # noqa: E402
from app.nlp.semantic_search import semantic_search  # noqa: E402

mcp = FastMCP("biometa")
_Session = None


def _session():
    global _Session
    if _Session is None:
        _Session = get_session_factory()
    return _Session()


def _rel_dict(rel: MicrobeMetaboliteRelationship) -> dict:
    return {
        "microbe": rel.microbe.name, "metabolite": rel.metabolite.name,
        "relationship_type": rel.relationship_type, "confidence": round(rel.confidence_score or 0, 3),
        "evidence": rel.evidence_sentence, "pmid": rel.article.pmid,
        "journal": rel.article.journal, "year": rel.article.pub_date,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{rel.article.pmid}/",
    }


@mcp.tool()
def find_relationships(microbe: str = "", metabolite: str = "", relationship_type: str = "",
                       min_confidence: float = 0.0, limit: int = 25) -> list[dict]:
    """Find microbe-metabolite relationships in the literature database.

    Filter by microbe name, metabolite name and/or relationship type (produces,
    consumes, converts, inhibits, activates, regulates, associates_with,
    interacts). Each result includes the source PMID and evidence sentence.
    """
    db = _session()
    try:
        q = (db.query(MicrobeMetaboliteRelationship)
             .join(Microbe).join(Metabolite).join(Article))
        if microbe:
            q = q.filter(Microbe.name.ilike(f"%{microbe.lower()}%"))
        if metabolite:
            q = q.filter(Metabolite.name.ilike(f"%{metabolite.lower()}%"))
        if relationship_type:
            q = q.filter(MicrobeMetaboliteRelationship.relationship_type == relationship_type)
        q = q.filter(MicrobeMetaboliteRelationship.confidence_score >= min_confidence)
        q = q.order_by(MicrobeMetaboliteRelationship.confidence_score.desc()).limit(min(limit, 100))
        return [_rel_dict(r) for r in q.all()]
    finally:
        db.close()


@mcp.tool()
def search_articles(query: str, limit: int = 10) -> list[dict]:
    """Semantic search over article titles and abstracts. Returns PMIDs and links."""
    db = _session()
    try:
        return [{"pmid": a["pmid"], "title": a["title"], "journal": a.get("journal"),
                 "year": a.get("pub_date"), "score": a.get("score"),
                 "url": a.get("full_text_link") or f"https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/"}
                for a in semantic_search(db, query, top_k=min(limit, 50))]
    finally:
        db.close()


@mcp.tool()
def get_article(pmid: str) -> dict:
    """Fetch one article's metadata, abstract, and all relationships extracted from it."""
    db = _session()
    try:
        art = db.query(Article).filter(Article.pmid == pmid).first()
        if not art:
            return {"error": f"No article with PMID {pmid} in the database."}
        rels = db.query(MicrobeMetaboliteRelationship).filter_by(article_id=art.id).all()
        return {"pmid": art.pmid, "title": art.title, "abstract": art.abstract,
                "journal": art.journal, "year": art.pub_date,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{art.pmid}/",
                "relationships": [_rel_dict(r) for r in rels]}
    finally:
        db.close()


@mcp.tool()
def extract_from_text(text: str) -> list[dict]:
    """Run the relationship extractor (rules v2) on arbitrary text, e.g. a pasted abstract.

    Does not touch the database; useful for checking what the pipeline would
    extract from a new passage. Each result includes the evidence sentence.
    """
    rels = extract_relationships(text, method="rules_v2")
    return [{"microbe": r.microbe, "metabolite": r.metabolite, "relationship_type": r.relationship_type,
             "confidence": r.confidence, "evidence": r.evidence_sentence} for r in rels]


@mcp.tool()
def list_entities(kind: str = "microbe", contains: str = "", limit: int = 50) -> list[dict]:
    """List known microbes or metabolites and how often each is mentioned.

    kind: "microbe" or "metabolite". `contains` filters by substring.
    """
    db = _session()
    try:
        model = Microbe if kind == "microbe" else Metabolite
        q = db.query(model)
        if contains:
            q = q.filter(model.name.ilike(f"%{contains.lower()}%"))
        q = q.order_by(model.mention_count.desc()).limit(min(limit, 200))
        return [{"name": e.name, "type": getattr(e, "microbe_type", None) or getattr(e, "metabolite_class", None),
                 "mentions": e.mention_count} for e in q.all()]
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()

"""Build an in-memory fixture database for the agent groundedness eval.

A handful of articles with known microbe-metabolite relationships, so we can
check exactly which citations the agent is entitled to make for a given query.
No network, no API key, no embeddings — seeds the SQLite tables directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Article, Base, Metabolite, Microbe, MicrobeMetaboliteRelationship

# (pmid, title, journal, year, [(microbe, metabolite, type, confidence, evidence)])
ARTICLES = [
    ("30001001", "Butyrate production by Faecalibacterium prausnitzii in the human colon",
     "Gut Microbes", "2021",
     [("faecalibacterium prausnitzii", "butyrate", "produces", 0.9,
       "Faecalibacterium prausnitzii produces butyrate from acetate.")]),
    ("30001002", "Trimethylamine formation from choline by gut Enterobacteriaceae",
     "Cell Host & Microbe", "2020",
     [("escherichia coli", "trimethylamine", "produces", 0.85,
       "Escherichia coli produces trimethylamine from dietary choline."),
      ("escherichia coli", "choline", "consumes", 0.8,
       "Escherichia coli produces trimethylamine from dietary choline.")]),
    ("30001003", "Secondary bile acids inhibit Clostridioides difficile germination",
     "Nature", "2022",
     [("clostridioides difficile", "deoxycholic acid", "inhibits", 0.88,
       "Deoxycholic acid inhibited the germination of Clostridioides difficile spores.")]),
    ("30001004", "Akkermansia muciniphila and short-chain fatty acid profiles",
     "ISME Journal", "2021",
     [("akkermansia muciniphila", "propionate", "produces", 0.82,
       "Akkermansia muciniphila produces propionate and acetate."),
      ("akkermansia muciniphila", "acetate", "produces", 0.8,
       "Akkermansia muciniphila produces propionate and acetate.")]),
    ("30001005", "Lactobacillus reuteri lowers circulating TMAO in a murine model",
     "Microbiome", "2023",
     [("lactobacillus reuteri", "tmao", "inhibits", 0.8,
       "Lactobacillus reuteri supplementation reduced circulating TMAO.")]),
]


def build_fixture_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    microbes: dict[str, Microbe] = {}
    metabolites: dict[str, Metabolite] = {}

    for pmid, title, journal, year, rels in ARTICLES:
        art = Article(pmid=pmid, title=title, journal=journal, pub_date=year,
                      abstract=" ".join(r[4] for r in rels), processed=True,
                      full_text_link=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
        db.add(art)
        db.flush()
        for micro, met, rtype, conf, ev in rels:
            if micro not in microbes:
                microbes[micro] = Microbe(name=micro, normalized_name=micro, microbe_type="bacteria")
                db.add(microbes[micro]); db.flush()
            if met not in metabolites:
                metabolites[met] = Metabolite(name=met, normalized_name=met, metabolite_class="metabolite")
                db.add(metabolites[met]); db.flush()
            db.add(MicrobeMetaboliteRelationship(
                microbe_id=microbes[micro].id, metabolite_id=metabolites[met].id, article_id=art.id,
                relationship_type=rtype, confidence_score=conf, evidence_sentence=ev, extraction_method="pattern"))
    db.commit()
    return db


ALL_PMIDS = {a[0] for a in ARTICLES}

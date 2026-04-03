"""
Bootstrap / seed script for BiometaAgent.

Fetches PubMed articles, runs the NLP pipeline, and computes embeddings.
Run this once after `docker-compose up` to populate the database.

Usage:
    # From inside the backend container or with the right DATABASE_URL set:
    python scripts/seed.py

    # Custom query and size:
    python scripts/seed.py --query "gut microbiome metabolite" --max 500

    # Skip NLP (fetch only):
    python scripts/seed.py --no-nlp

    # Skip embeddings (faster, no sentence-transformers needed):
    python scripts/seed.py --no-embeddings
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Make sure app/ is importable when run from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed")

DEFAULT_QUERIES = [
    "gut microbiome metabolite production",
    "Lactobacillus metabolites probiotic",
    "short chain fatty acids gut bacteria",
    "microbial secondary metabolites biosynthesis",
    "bacteria bile acid metabolism",
]


def parse_args():
    p = argparse.ArgumentParser(description="Seed BiometaAgent database from PubMed")
    p.add_argument(
        "--query", "-q",
        nargs="+",
        default=DEFAULT_QUERIES,
        help="PubMed search query (can repeat for multiple queries)",
    )
    p.add_argument(
        "--max", "-n",
        type=int,
        default=200,
        dest="max_results",
        help="Max articles per query (default: 200)",
    )
    p.add_argument(
        "--no-nlp",
        action="store_true",
        help="Skip NLP relationship extraction",
    )
    p.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Skip embedding computation",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="PubMed fetch batch size (default: 100)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    from app.core.config import get_settings
    from app.db.database import init_db, get_session_factory, get_engine
    from app.db.models import Article
    from app.services.pubmed_fetcher import fetch_and_store
    from app.nlp.relationship_extractor import extract_relationships, store_relationships
    from app.nlp.semantic_search import compute_and_store_embeddings

    settings = get_settings()
    logger.info("Connecting to database...")
    engine = get_engine()
    init_db()
    SessionFactory = get_session_factory(engine)
    db = SessionFactory()

    total_fetched = 0
    try:
        # ── 1. Fetch articles ─────────────────────────────────────────────────
        for query in args.query:
            logger.info(f"Fetching: {query!r}  (max={args.max_results})")
            n = fetch_and_store(
                db,
                query=query,
                max_results=args.max_results,
                batch_size=args.batch_size,
                email=settings.entrez_email,
            )
            total_fetched += n
            logger.info(f"  → {n} new articles stored")
            time.sleep(1)  # brief pause between queries

        logger.info(f"Fetch complete. Total new articles: {total_fetched}")

        # ── 2. NLP pipeline ───────────────────────────────────────────────────
        if not args.no_nlp:
            unprocessed = (
                db.query(Article)
                .filter(Article.processed == False)
                .filter(Article.abstract.isnot(None))
                .all()
            )
            logger.info(f"Running NLP on {len(unprocessed)} unprocessed articles...")

            total_rels = 0
            for i, art in enumerate(unprocessed, 1):
                rels = extract_relationships(art.abstract or "", pmid=art.pmid)
                stored = store_relationships(db, rels, art.id)
                total_rels += stored
                art.processed = True
                if i % 50 == 0:
                    db.commit()
                    logger.info(f"  {i}/{len(unprocessed)} processed, {total_rels} relationships so far")
            db.commit()
            logger.info(f"NLP complete. Relationships extracted: {total_rels}")

        # ── 3. Embeddings ─────────────────────────────────────────────────────
        if not args.no_embeddings:
            logger.info("Computing semantic embeddings...")
            n_emb = compute_and_store_embeddings(db)
            logger.info(f"Embeddings computed: {n_emb}")

        # ── 4. Summary ────────────────────────────────────────────────────────
        from app.db.models import Microbe, Metabolite, MicrobeMetaboliteRelationship
        logger.info("─" * 50)
        logger.info("Database summary:")
        logger.info(f"  Articles       : {db.query(Article).count()}")
        logger.info(f"  Processed      : {db.query(Article).filter(Article.processed == True).count()}")
        logger.info(f"  Microbes       : {db.query(Microbe).count()}")
        logger.info(f"  Metabolites    : {db.query(Metabolite).count()}")
        logger.info(f"  Relationships  : {db.query(MicrobeMetaboliteRelationship).count()}")
        logger.info("─" * 50)
        logger.info("Done! You can now open http://localhost:3000")

    except KeyboardInterrupt:
        logger.info("Interrupted — committing what we have...")
        db.commit()
    except Exception as e:
        logger.error(f"Seed failed: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

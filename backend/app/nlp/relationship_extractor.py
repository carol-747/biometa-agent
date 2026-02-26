"""
Relationship extraction between microbes and metabolites.
Uses pattern matching on sentences containing both entity types.
Confidence scoring based on match quality and proximity.
"""
import re
import logging
from dataclasses import dataclass
from typing import Any

from app.nlp.entity_extractor import Entity, extract_entities

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Relationship type patterns
# ---------------------------------------------------------------------------

RELATIONSHIP_PATTERNS: dict[str, list[re.Pattern]] = {
    "produces": [
        re.compile(r"\b(produc|secret|synthes|generat|excret|emit|release)\w*\b", re.I),
        re.compile(r"\b(biosynthes\w+|manufacture\w*)\b", re.I),
    ],
    "consumes": [
        re.compile(r"\b(consum|metaboli[sz]e|degrad|breakdown|utiliz|ferment|digest)\w*\b", re.I),
        re.compile(r"\b(uptake|absorb\w*)\b", re.I),
    ],
    "regulates": [
        re.compile(r"\b(regulat|modulat|control|affect|influenc|alter)\w*\b", re.I),
    ],
    "inhibits": [
        re.compile(r"\b(inhibit|suppress|block|reduc\w+|decreas\w+|down.?regulat)\w*\b", re.I),
    ],
    "activates": [
        re.compile(r"\b(activ|stimulat|induc|promot|increas\w+|up.?regulat|enhanc)\w*\b", re.I),
    ],
    "associates_with": [
        re.compile(r"\b(associat|correlat|link|relat|co.?occur)\w*\b", re.I),
    ],
    "converts": [
        re.compile(r"\b(convert|transform|catalyz|bioconvert)\w*\b", re.I),
    ],
    "interacts": [
        re.compile(r"\b(interact|bind\w*|react\w*)\b", re.I),
    ],
}

# Negation patterns (reduce confidence)
NEGATION_PATTERNS = re.compile(
    r"\b(not|no|neither|without|unable|fail|lack|absent|negative)\b", re.I
)


@dataclass
class Relationship:
    microbe: str
    microbe_type: str
    metabolite: str
    metabolite_class: str
    relationship_type: str
    confidence: float
    evidence_sentence: str
    article_pmid: str | None = None
    extraction_method: str = "pattern"


def _split_sentences(text: str) -> list[str]:
    """Simple sentence splitter."""
    return re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)


def _sentence_proximity(microbe_span: tuple, metabolite_span: tuple, text_len: int) -> float:
    """Proximity score: 1.0 if adjacent, decreases with distance."""
    dist = abs(microbe_span[0] - metabolite_span[0])
    return max(0.0, 1.0 - dist / max(text_len, 1))


def extract_relationships(
    text: str, pmid: str | None = None, max_sentences: int = 500
) -> list[Relationship]:
    """Extract microbe-metabolite relationships from text."""
    if not text:
        return []

    relationships: list[Relationship] = []
    sentences = _split_sentences(text)[:max_sentences]

    for sentence in sentences:
        entities = extract_entities(sentence)
        microbes = [e for e in entities if e.label == "MICROBE"]
        metabolites = [e for e in entities if e.label == "METABOLITE"]

        if not microbes or not metabolites:
            continue

        # For each microbe-metabolite pair in the sentence
        for microbe in microbes:
            for metabolite in metabolites:
                rel_type, confidence = _classify_relationship(sentence, microbe, metabolite)
                if confidence < 0.1:
                    continue

                # Penalize for negation
                if NEGATION_PATTERNS.search(sentence):
                    confidence *= 0.5

                relationships.append(
                    Relationship(
                        microbe=microbe.text,
                        microbe_type=microbe.entity_type,
                        metabolite=metabolite.text,
                        metabolite_class=metabolite.entity_type,
                        relationship_type=rel_type,
                        confidence=round(confidence, 3),
                        evidence_sentence=sentence.strip(),
                        article_pmid=pmid,
                        extraction_method="pattern",
                    )
                )

    # Deduplicate: keep highest confidence for each (microbe, metabolite, type)
    seen: dict[tuple, Relationship] = {}
    for rel in relationships:
        key = (rel.microbe.lower(), rel.metabolite.lower(), rel.relationship_type)
        if key not in seen or rel.confidence > seen[key].confidence:
            seen[key] = rel

    return list(seen.values())


def _classify_relationship(
    sentence: str,
    microbe: Entity,
    metabolite: Entity,
) -> tuple[str, float]:
    """
    Returns (relationship_type, confidence) for a sentence.
    """
    best_type = "associates_with"
    best_conf = 0.05  # baseline: any co-occurrence = weak association

    # Check directional order: microbe before metabolite (more likely "produces")
    microbe_first = microbe.start < metabolite.start

    for rel_type, patterns in RELATIONSHIP_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(sentence):
                # Base confidence from pattern match
                conf = 0.65

                # Boost for directional clues
                if rel_type == "produces" and microbe_first:
                    conf += 0.1
                if rel_type == "consumes" and not microbe_first:
                    conf += 0.05

                # Proximity boost
                span_m = (microbe.start, microbe.end)
                span_met = (metabolite.start, metabolite.end)
                prox = _sentence_proximity(span_m, span_met, len(sentence))
                conf += prox * 0.15

                if conf > best_conf:
                    best_conf = conf
                    best_type = rel_type

    return best_type, min(best_conf, 0.95)


def store_relationships(
    db_session,
    relationships: list[Relationship],
    article_id: int,
) -> int:
    """Persist extracted relationships to the database."""
    from app.db.models import Microbe, Metabolite, MicrobeMetaboliteRelationship

    stored = 0
    for rel in relationships:
        try:
            # Upsert microbe
            microbe_obj = db_session.query(Microbe).filter_by(
                name=rel.microbe.lower()
            ).first()
            if not microbe_obj:
                microbe_obj = Microbe(
                    name=rel.microbe.lower(),
                    normalized_name=rel.microbe.lower(),
                    microbe_type=rel.microbe_type,
                )
                db_session.add(microbe_obj)
                db_session.flush()
            microbe_obj.mention_count = (microbe_obj.mention_count or 0) + 1

            # Upsert metabolite
            met_obj = db_session.query(Metabolite).filter_by(
                name=rel.metabolite.lower()
            ).first()
            if not met_obj:
                met_obj = Metabolite(
                    name=rel.metabolite.lower(),
                    normalized_name=rel.metabolite.lower(),
                    metabolite_class=rel.metabolite_class,
                )
                db_session.add(met_obj)
                db_session.flush()
            met_obj.mention_count = (met_obj.mention_count or 0) + 1

            # Check for existing relationship
            existing = db_session.query(MicrobeMetaboliteRelationship).filter_by(
                microbe_id=microbe_obj.id,
                metabolite_id=met_obj.id,
                article_id=article_id,
                relationship_type=rel.relationship_type,
            ).first()

            if existing:
                if rel.confidence > existing.confidence_score:
                    existing.confidence_score = rel.confidence
                    existing.evidence_sentence = rel.evidence_sentence
            else:
                db_rel = MicrobeMetaboliteRelationship(
                    microbe_id=microbe_obj.id,
                    metabolite_id=met_obj.id,
                    article_id=article_id,
                    relationship_type=rel.relationship_type,
                    confidence_score=rel.confidence,
                    evidence_sentence=rel.evidence_sentence,
                    extraction_method=rel.extraction_method,
                )
                db_session.add(db_rel)
                stored += 1

        except Exception as e:
            logger.warning(f"Error storing relationship: {e}")
            db_session.rollback()

    try:
        db_session.commit()
    except Exception as e:
        logger.error(f"Commit error: {e}")
        db_session.rollback()

    return stored

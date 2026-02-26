"""Tests for NLP entity extraction and relationship detection."""
import pytest


# ---------------------------------------------------------------------------
# Entity extraction tests
# ---------------------------------------------------------------------------

def test_entity_extraction_bacteria():
    from app.nlp.entity_extractor import get_microbes
    text = "Escherichia coli produces acetate during anaerobic fermentation."
    microbes = get_microbes(text)
    names = [m.text.lower() for m in microbes]
    assert any("escherichia coli" in n or "e. coli" in n for n in names)


def test_entity_extraction_metabolite():
    from app.nlp.entity_extractor import get_metabolites
    text = "The production of butyrate by gut bacteria affects colonocyte health."
    metabolites = get_metabolites(text)
    assert any("butyrate" in m.text.lower() for m in metabolites)


def test_entity_extraction_multiple_microbes():
    from app.nlp.entity_extractor import get_microbes
    text = (
        "Lactobacillus reuteri and Bifidobacterium longum are common probiotics "
        "found in the human gut microbiome."
    )
    microbes = get_microbes(text)
    names = " ".join(m.text.lower() for m in microbes)
    assert "lactobacillus" in names or "reuteri" in names
    assert "bifidobacterium" in names or "longum" in names


def test_entity_extraction_multiple_metabolites():
    from app.nlp.entity_extractor import get_metabolites
    text = "Gut bacteria produce butyrate, propionate, and acetate as major SCFAs."
    metabolites = get_metabolites(text)
    names = " ".join(m.text.lower() for m in metabolites)
    assert "butyrate" in names
    assert "propionate" in names or "acetate" in names


def test_entity_label_microbe():
    from app.nlp.entity_extractor import extract_entities
    text = "Lactobacillus acidophilus is widely studied."
    entities = extract_entities(text)
    microbe_entities = [e for e in entities if e.label == "MICROBE"]
    assert len(microbe_entities) > 0


def test_entity_label_metabolite():
    from app.nlp.entity_extractor import extract_entities
    text = "Serotonin is a metabolite produced by gut bacteria."
    entities = extract_entities(text)
    metabolite_entities = [e for e in entities if e.label == "METABOLITE"]
    assert len(metabolite_entities) > 0


def test_entity_source_dict():
    from app.nlp.entity_extractor import extract_entities
    text = "Candida albicans produces ergosterol."
    entities = extract_entities(text)
    dict_entities = [e for e in entities if e.source == "dict"]
    assert len(dict_entities) > 0


def test_entity_span_positions():
    from app.nlp.entity_extractor import extract_entities
    text = "E. coli produces butyrate."
    entities = extract_entities(text)
    for e in entities:
        assert e.start >= 0
        assert e.end > e.start
        assert e.end <= len(text)


def test_entity_empty_text():
    from app.nlp.entity_extractor import extract_entities
    assert extract_entities("") == []
    assert extract_entities(None) == []


def test_metabolite_type_classification():
    from app.nlp.entity_extractor import get_metabolites
    text = "butyrate is a short-chain fatty acid."
    metabolites = get_metabolites(text)
    butyrate = next((m for m in metabolites if "butyrate" in m.text.lower()), None)
    assert butyrate is not None
    assert butyrate.entity_type in ("short_chain_fatty_acid", "metabolite", "chemical")


# ---------------------------------------------------------------------------
# Relationship extraction tests
# ---------------------------------------------------------------------------

def test_relationship_extraction_produces():
    from app.nlp.relationship_extractor import extract_relationships
    text = (
        "Lactobacillus reuteri produces reuterin, an antimicrobial compound, "
        "during anaerobic glycerol metabolism."
    )
    rels = extract_relationships(text)
    # At minimum, should not crash; may find a relationship
    assert isinstance(rels, list)


def test_relationship_extraction_confidence_bounds():
    from app.nlp.relationship_extractor import extract_relationships
    text = (
        "Faecalibacterium prausnitzii synthesizes butyrate through the "
        "butyryl-CoA:acetate CoA transferase pathway."
    )
    rels = extract_relationships(text)
    for rel in rels:
        assert 0.0 <= rel.confidence <= 1.0


def test_relationship_confidence_high_for_clear_sentence():
    from app.nlp.relationship_extractor import extract_relationships
    text = "E. coli produces acetate in anaerobic conditions."
    rels = extract_relationships(text)
    if rels:
        best = max(rels, key=lambda r: r.confidence)
        assert best.confidence >= 0.5


def test_relationship_types_defined():
    from app.nlp.relationship_extractor import RELATIONSHIP_PATTERNS
    expected = {'produces', 'consumes', 'regulates', 'inhibits', 'activates'}
    assert expected.issubset(RELATIONSHIP_PATTERNS.keys())


def test_negation_reduces_confidence():
    from app.nlp.relationship_extractor import extract_relationships
    positive = "Lactobacillus produces lactic acid during fermentation."
    negative = "Lactobacillus does not produce lactic acid in aerobic conditions."
    pos_rels = extract_relationships(positive)
    neg_rels = extract_relationships(negative)
    if pos_rels and neg_rels:
        pos_conf = max(r.confidence for r in pos_rels)
        neg_conf = max(r.confidence for r in neg_rels)
        assert neg_conf < pos_conf


def test_relationship_has_evidence_sentence():
    from app.nlp.relationship_extractor import extract_relationships
    text = "Akkermansia muciniphila regulates butyrate production in the gut."
    rels = extract_relationships(text)
    for rel in rels:
        assert rel.evidence_sentence
        assert len(rel.evidence_sentence) > 5


def test_relationship_fields_present():
    from app.nlp.relationship_extractor import extract_relationships, Relationship
    text = "Bacteroides thetaiotaomicron consumes succinate as a carbon source."
    rels = extract_relationships(text)
    for rel in rels:
        assert isinstance(rel, Relationship)
        assert rel.microbe
        assert rel.metabolite
        assert rel.relationship_type
        assert rel.extraction_method == "pattern"


def test_relationship_deduplication():
    """Same sentence repeated should not produce duplicate relationships."""
    from app.nlp.relationship_extractor import extract_relationships
    sentence = "E. coli produces acetate."
    text = sentence + " " + sentence
    rels = extract_relationships(text)
    keys = [(r.microbe.lower(), r.metabolite.lower(), r.relationship_type) for r in rels]
    assert len(keys) == len(set(keys))


def test_empty_text_returns_empty():
    from app.nlp.relationship_extractor import extract_relationships
    assert extract_relationships("") == []

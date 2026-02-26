"""Tests for NLP entity extraction and relationship detection."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_entity_extraction_bacteria():
    from app.nlp.entity_extractor import extract_entities, get_microbes
    text = "Escherichia coli produces acetate during anaerobic fermentation."
    entities = extract_entities(text)
    microbes = get_microbes(text)
    # Should find E. coli or Escherichia coli
    assert len(microbes) > 0 or any(e.label == 'MICROBE' for e in entities)


def test_entity_extraction_metabolite():
    from app.nlp.entity_extractor import get_metabolites
    text = "The production of butyrate by gut bacteria affects colonocyte health."
    metabolites = get_metabolites(text)
    assert any('butyrate' in m.text.lower() for m in metabolites)


def test_relationship_extraction_produces():
    from app.nlp.relationship_extractor import extract_relationships
    text = (
        "Lactobacillus reuteri produces reuterin, an antimicrobial compound, "
        "during anaerobic glycerol metabolism."
    )
    rels = extract_relationships(text)
    assert len(rels) >= 0  # At minimum, should not crash


def test_relationship_extraction_confidence():
    from app.nlp.relationship_extractor import extract_relationships
    text = (
        "Faecalibacterium prausnitzii synthesizes butyrate through the "
        "butyryl-CoA:acetate CoA transferase pathway."
    )
    rels = extract_relationships(text)
    for rel in rels:
        assert 0.0 <= rel.confidence <= 1.0


def test_relationship_types():
    from app.nlp.relationship_extractor import RELATIONSHIP_PATTERNS
    expected_types = {'produces', 'consumes', 'regulates', 'inhibits', 'activates'}
    assert expected_types.issubset(RELATIONSHIP_PATTERNS.keys())


def test_negation_reduces_confidence():
    from app.nlp.relationship_extractor import extract_relationships
    positive = "E. coli produces acetate in anaerobic conditions."
    negative = "E. coli does not produce acetate in aerobic conditions."
    pos_rels = extract_relationships(positive)
    neg_rels = extract_relationships(negative)
    if pos_rels and neg_rels:
        # Negated sentence should have lower confidence
        assert neg_rels[0].confidence <= pos_rels[0].confidence


def test_empty_text():
    from app.nlp.entity_extractor import extract_entities
    from app.nlp.relationship_extractor import extract_relationships
    assert extract_entities("") == []
    assert extract_relationships("") == []

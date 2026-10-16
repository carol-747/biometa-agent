"""Tests for the v2 relationship extractor and stricter entity recognition."""


def test_species_regex_rejects_non_microbe_phrases():
    from app.nlp.entity_extractor import extract_entities
    for phrase in ["The production of butyrate was increased.",
                   "Gut bacteria produce propionate.",
                   "Lactic acid bacteria acidify milk."]:
        mics = [e for e in extract_entities(phrase, strict=True) if e.label == "MICROBE"]
        assert all(e.source != "pattern" or e.text[0].isupper() for e in mics)
        assert not any(e.text in ("The production", "Gut bacteria", "Lactic acid") for e in mics)


def test_known_genus_binomial_still_detected():
    from app.nlp.entity_extractor import extract_entities
    # Not in the dictionary, but Bilophila is a known genus.
    mics = [e.text for e in extract_entities("Bilophila wadsworthia generates hydrogen sulfide.", strict=True)
            if e.label == "MICROBE"]
    assert any("Bilophila" in m for m in mics)


def test_v2_respects_scoped_negation():
    from app.nlp.relationship_extractor import extract_relationships
    rels = extract_relationships("Escherichia coli did not produce butyrate.", method="rules_v2")
    assert rels == []  # negated relations are dropped


def test_v2_assigns_verb_to_nearest_microbe():
    from app.nlp.relationship_extractor import extract_relationships
    rels = extract_relationships(
        "Lactobacillus reuteri reduced TMAO levels, whereas Escherichia coli produced acetate.",
        method="rules_v2")
    triples = {(r.microbe.lower(), r.relationship_type, r.metabolite.lower()) for r in rels}
    assert ("lactobacillus reuteri", "inhibits", "tmao") in triples
    assert ("escherichia coli", "produces", "acetate") in triples
    # The cross pairs must NOT appear.
    assert ("lactobacillus reuteri", "produces", "tmao") not in triples
    assert not any(m == "escherichia coli" and x == "tmao" for m, _, x in triples)


def test_v2_substrate_vs_product():
    from app.nlp.relationship_extractor import extract_relationships
    rels = {(r.microbe.lower(), r.relationship_type, r.metabolite.lower())
            for r in extract_relationships(
                "Clostridium scindens converts primary bile acids to secondary bile acids.", method="rules_v2")}
    assert ("clostridium scindens", "consumes", "primary bile acids") in rels or \
           ("clostridium scindens", "converts", "primary bile acids") in rels
    assert ("clostridium scindens", "produces", "secondary bile acids") in rels or \
           ("clostridium scindens", "converts", "secondary bile acids") in rels


def test_v1_still_available():
    from app.nlp.relationship_extractor import extract_relationships
    rels = extract_relationships("Faecalibacterium prausnitzii produces butyrate.", method="rules_v1")
    assert any(r.relationship_type == "produces" for r in rels)


def test_v2_beats_v1_on_benchmark():
    """Regression guard: v2 must keep a clear lead on the dev benchmark."""
    import json
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from evals.run_extraction_eval import evaluate, load
    items = load("dev")
    v1 = evaluate("rules_v1", items)
    v2 = evaluate("rules_v2", items)
    assert v2["triples"]["f1"] > v1["triples"]["f1"] + 0.2
    assert v2["negation_errors"] == 0
    assert v2["microbes"]["precision"] >= 0.95

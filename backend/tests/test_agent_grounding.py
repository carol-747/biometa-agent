"""Tests for agent citation grounding against a fixture database."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _agent_offline(grounded: bool):
    from app.services.agent import ConversationalAgent
    a = ConversationalAgent(grounded=grounded)
    a.client.api_key = None
    return a


def test_grounded_agent_abstains_when_unsupported():
    from evals.fixtures import build_fixture_db
    db = build_fixture_db()
    agent = _agent_offline(grounded=True)
    analysis = {"microbes": [], "metabolites": ["penicillin"], "relationship_types": [], "search_query": "penicillin"}
    ctx = agent._fetch_context(db, analysis, "role of penicillin?")
    assert ctx["relationships"] == []
    assert ctx["articles"] == []  # off-topic keyword hits are filtered out


def test_grounded_agent_only_cites_supported_articles():
    import re
    from evals.fixtures import build_fixture_db
    db = build_fixture_db()
    agent = _agent_offline(grounded=True)
    analysis = {"microbes": ["Faecalibacterium prausnitzii"], "metabolites": [],
                "relationship_types": [], "search_query": "butyrate"}
    ctx = agent._fetch_context(db, analysis, "what does it produce?")
    reply = agent._format_direct_reply("what does it produce?", ctx)
    cited = set(re.findall(r"3000100\d", reply))
    retrieved = {r["pmid"] for r in ctx["relationships"]} | {a["pmid"] for a in ctx["articles"]}
    assert cited <= retrieved           # no invented citations
    assert cited == {"30001001"}


def test_grounded_eval_improves_precision():
    """The grounded variant must reach perfect citation precision on the fixture eval."""
    from evals.run_agent_eval import evaluate
    base = evaluate(live=False, grounded=False)
    grounded = evaluate(live=False, grounded=True)
    assert grounded["citation"]["precision"] == 1.0
    assert grounded["citation"]["precision"] > base["citation"]["precision"]
    assert grounded["invented_citations"] == 0
    assert grounded["abstention"]["correct"] == grounded["abstention"]["total"]

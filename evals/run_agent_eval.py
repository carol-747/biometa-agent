"""Groundedness eval for the conversational agent.

Against a fixture DB with known articles, each question declares the PMIDs that
support it (empty = nothing in the DB supports it, so the agent should abstain).
We then check the agent's reply for:

* Citation grounding: every PMID cited in the reply is one the retrieval step
  actually returned (no invented citations).
* Citation precision/recall vs. the supporting PMIDs for the question.
* Abstention: on unsupported questions, the reply signals "not found" and cites
  nothing.

Runs offline by default against the agent's deterministic no-API reply. With
ANTHROPIC_API_KEY set, pass --live to grade the actual Claude reply instead;
the same checks apply.

    python evals/run_agent_eval.py
    python evals/run_agent_eval.py --live
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

import logging  # noqa: E402

logging.disable(logging.WARNING)

from evals.fixtures import ALL_PMIDS, build_fixture_db  # noqa: E402
from app.services.agent import ConversationalAgent  # noqa: E402

RESULTS = ROOT / "evals" / "results"
PMID_RE = re.compile(r"\b(3000100\d)\b")
ABSTAIN_RE = re.compile(r"no (?:relationship|match|result|data|record|evidence)|not found|"
                        r"n't found|couldn't find|could not find|no information|nothing in the database",
                        re.I)

# question, entities to seed the retrieval, supporting PMIDs (empty = should abstain)
QUESTIONS = [
    ("What does Faecalibacterium prausnitzii produce?",
     {"microbes": ["Faecalibacterium prausnitzii"], "metabolites": []}, ["30001001"]),
    ("Which bacteria produce trimethylamine from choline?",
     {"microbes": ["Escherichia coli"], "metabolites": ["trimethylamine", "choline"]}, ["30001002"]),
    ("What inhibits Clostridioides difficile germination?",
     {"microbes": ["Clostridioides difficile"], "metabolites": ["deoxycholic acid"]}, ["30001003"]),
    ("What short-chain fatty acids does Akkermansia muciniphila produce?",
     {"microbes": ["Akkermansia muciniphila"], "metabolites": ["propionate", "acetate"]}, ["30001004"]),
    ("Does Lactobacillus reuteri affect TMAO?",
     {"microbes": ["Lactobacillus reuteri"], "metabolites": ["TMAO"]}, ["30001005"]),
    # Unsupported: entities exist in the query but no relationship is in the fixture DB.
    ("What metabolites does Salmonella enterica produce?",
     {"microbes": ["Salmonella enterica"], "metabolites": []}, []),
    ("Does Bifidobacterium longum degrade cellulose?",
     {"microbes": ["Bifidobacterium longum"], "metabolites": ["cellulose"]}, []),
    ("What is the role of penicillin in gut inflammation?",
     {"microbes": [], "metabolites": ["penicillin"]}, []),
]


def _reply(agent, db, question, entities, live):
    analysis = {**entities, "relationship_types": [], "search_query": question}
    ctx = agent._fetch_context(db, analysis, question)
    retrieved = {r["pmid"] for r in ctx["relationships"]} | {a["pmid"] for a in ctx["articles"]}
    if live:
        text = agent.client.messages.create(
            model=agent.model, max_tokens=1024, system=__import__("app.services.agent", fromlist=["SYSTEM_PROMPT"]).SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"{question}\n\n[DATABASE CONTEXT]\n{agent._format_context(ctx)}"}],
        ).content[0].text
    else:
        text = agent._format_direct_reply(question, ctx)
    return text, retrieved


def evaluate(live: bool, grounded: bool = True) -> dict:
    agent = ConversationalAgent(grounded=grounded)
    if not live:
        agent.client.api_key = None
    db = build_fixture_db()

    rows, c = [], {"grounded": 0, "cite_tp": 0, "cite_fp": 0, "cite_fn": 0,
                   "abstain_ok": 0, "abstain_total": 0, "hallucinated_on_abstain": 0}
    for q, entities, support in QUESTIONS:
        text, retrieved = _reply(agent, db, q, entities, live)
        cited = set(PMID_RE.findall(text))
        invented = cited - retrieved           # cited but never retrieved
        off_support = cited - set(support)      # cited but not a supporting PMID
        row_grounded = not invented
        c["grounded"] += row_grounded
        c["cite_tp"] += len(cited & set(support))
        c["cite_fp"] += len(off_support)
        c["cite_fn"] += len(set(support) - cited)

        row = {"question": q, "supported": support, "cited": sorted(cited),
               "invented_citations": sorted(invented), "grounded": row_grounded}
        if not support:
            c["abstain_total"] += 1
            abstained = bool(ABSTAIN_RE.search(text)) and not cited
            c["abstain_ok"] += abstained
            c["hallucinated_on_abstain"] += bool(cited)
            row["abstained"] = abstained
        rows.append(row)

    def prf(tp, fp, fn):
        p = tp / (tp + fp) if tp + fp else 1.0
        r = tp / (tp + fn) if tp + fn else 1.0
        return {"precision": round(p, 3), "recall": round(r, 3)}

    return {
        "mode": "live" if live else "offline",
        "grounded": grounded,
        "n_questions": len(QUESTIONS),
        "groundedness_rate": round(c["grounded"] / len(QUESTIONS), 3),
        "invented_citations": c["cite_fp"] if False else sum(len(r["invented_citations"]) for r in rows),
        "citation": prf(c["cite_tp"], c["cite_fp"], c["cite_fn"]),
        "abstention": {"correct": c["abstain_ok"], "total": c["abstain_total"],
                       "hallucinated_citations": c["hallucinated_on_abstain"]},
        "rows": rows,
    }


def markdown(variants: list[dict]) -> str:
    base = variants[-1]
    L = ["# Agent groundedness evaluation", "",
         f"Mode: **{base['mode']}** · {base['n_questions']} questions against the fixture database "
         f"({len(ALL_PMIDS)} articles). Each question declares which PMIDs support it; questions with no "
         "supporting article should be answered with an abstention and no citation.", "",
         "| Variant | Groundedness | Invented citations | Citation precision | Citation recall | Correct abstentions |",
         "|---|---|---|---|---|---|"]
    for res in variants:
        name = "grounded (v2)" if res["grounded"] else "baseline"
        L.append(f"| {name} | {res['groundedness_rate']:.0%} | {res['invented_citations']} | "
                 f"{res['citation']['precision']:.2f} | {res['citation']['recall']:.2f} | "
                 f"{res['abstention']['correct']} / {res['abstention']['total']} |")
    L += ["",
          "*Groundedness* = share of replies that cite no PMID outside what retrieval returned. "
          "*Citation precision* = share of cited PMIDs that actually support the question. The baseline stays "
          "grounded (it never invents a PMID) but over-cites off-topic papers from the keyword-search fallback; "
          "the grounded variant only surfaces articles that mention a queried entity and abstains otherwise.",
          "", f"## Per-question detail ({'grounded (v2)' if base['grounded'] else 'baseline'})", "",
          "| Question | Supporting PMIDs | Cited | Invented | Grounded |", "|---|---|---|---|---|"]
    for r in base["rows"]:
        L.append(f"| {r['question']} | {', '.join(r['supported']) or '—'} | {', '.join(r['cited']) or '—'} | "
                 f"{', '.join(r['invented_citations']) or '—'} | {'yes' if r['grounded'] else 'NO'} |")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--live", action="store_true", help="Grade the real Claude reply (needs ANTHROPIC_API_KEY)")
    p.add_argument("--out", default=str(RESULTS / "agent_results.md"))
    args = p.parse_args(argv)

    variants = [evaluate(args.live, grounded=False), evaluate(args.live, grounded=True)]
    RESULTS.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(markdown(variants))
    Path(args.out).with_suffix(".json").write_text(json.dumps(variants, indent=2))
    for res in variants:
        name = "grounded" if res["grounded"] else "baseline"
        print(f"[{res['mode']}/{name}] groundedness {res['groundedness_rate']:.0%}, "
              f"invented {res['invented_citations']}, citation precision {res['citation']['precision']:.2f}, "
              f"abstentions {res['abstention']['correct']}/{res['abstention']['total']}")
    print(f"Report: {args.out}")


if __name__ == "__main__":
    main()

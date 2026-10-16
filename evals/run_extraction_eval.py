"""Score relationship extractors against the gold benchmark.

    python evals/run_extraction_eval.py                         # rules_v1 vs rules_v2, dev + held-out
    python evals/run_extraction_eval.py --methods llm           # needs ANTHROPIC_API_KEY

Metrics
-------
* Entities: precision / recall of microbe and metabolite mentions (exact surface text).
* Pairs: is the asserted (microbe, metabolite) pair found at all? (type ignored)
* Triples: pair found AND relation type is one of the gold-acceptable types.
* Negation errors: explicitly negated pairs that the extractor asserts anyway.
* Calibration: precision of predicted pairs by confidence bucket. A useful
  confidence score should have precision rising with confidence.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import logging  # noqa: E402

logging.disable(logging.WARNING)

from app.nlp.entity_extractor import extract_entities  # noqa: E402
from app.nlp.relationship_extractor import extract_relationships  # noqa: E402

DATA = ROOT / "evals" / "data"
RESULTS = ROOT / "evals" / "results"
SPLITS = {"dev": "relation_benchmark.jsonl", "held_out": "relation_heldout.jsonl"}
BUCKETS = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.01)]


def load(split: str) -> list[dict]:
    path = DATA / SPLITS[split]
    return [json.loads(line) for line in path.open()] if path.exists() else []


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3), "tp": tp, "fp": fp, "fn": fn}


def predict(method: str, text: str):
    rels = extract_relationships(text, method=method)
    strict = method != "rules_v1"
    ents = extract_entities(text, strict=strict)
    if method == "llm":  # the LLM returns entities implicitly through its relations
        mics = {r.microbe.lower() for r in rels}
        mets = {r.metabolite.lower() for r in rels}
    else:
        mics = {e.text.lower() for e in ents if e.label == "MICROBE"}
        mets = {e.text.lower() for e in ents if e.label == "METABOLITE"} - mics
    pairs: dict[tuple, tuple] = {}
    for r in rels:  # one prediction per pair: keep the most confident type
        key = (r.microbe.lower(), r.metabolite.lower())
        if key not in pairs or r.confidence > pairs[key][1]:
            pairs[key] = (r.relationship_type, r.confidence)
    return mics, mets, pairs


def evaluate(method: str, items: list[dict]) -> dict:
    c = defaultdict(int)
    by_tag = defaultdict(lambda: defaultdict(int))
    buckets = defaultdict(lambda: [0, 0])
    errors = []
    for it in items:
        mics, mets, pairs = predict(method, it["text"])
        g_mics = {m.lower() for m in it["microbes"]}
        g_mets = {m.lower() for m in it["metabolites"]}
        c["mic_tp"] += len(mics & g_mics); c["mic_fp"] += len(mics - g_mics); c["mic_fn"] += len(g_mics - mics)
        c["met_tp"] += len(mets & g_mets); c["met_fp"] += len(mets - g_mets); c["met_fn"] += len(g_mets - mets)

        gold = {(r["microbe"].lower(), r["metabolite"].lower()): r["types"] for r in it["relations"]}
        negated = {(n["microbe"].lower(), n["metabolite"].lower()) for n in it["negated"]}
        for key, (typ, conf) in pairs.items():
            ok_pair = key in gold
            ok_type = ok_pair and typ in gold[key]
            c["pair_tp" if ok_pair else "pair_fp"] += 1
            c["tri_tp" if ok_type else "tri_fp"] += 1
            if key in negated:
                c["neg_err"] += 1
            for lo, hi in BUCKETS:
                if lo <= conf < hi:
                    buckets[(lo, hi)][0] += ok_pair
                    buckets[(lo, hi)][1] += 1
            if not ok_type:
                why = "negated pair asserted" if key in negated else ("wrong type" if ok_pair else "spurious pair")
                errors.append({"id": it["id"], "text": it["text"], "predicted": f"{key[0]} -[{typ}]-> {key[1]}",
                               "expected": f"{gold[key]}" if ok_pair else "-", "error": why})
            for tag in it["tags"]:
                by_tag[tag]["fp"] += (not ok_pair)
        for key, types in gold.items():
            hit = key in pairs
            c["pair_fn"] += not hit
            c["tri_fn"] += not (hit and pairs[key][0] in types)
            if not hit:
                errors.append({"id": it["id"], "text": it["text"], "predicted": "-",
                               "expected": f"{key[0]} -[{'/'.join(types)}]-> {key[1]}", "error": "missed"})
            for tag in it["tags"]:
                by_tag[tag]["gold"] += 1
                by_tag[tag]["hit"] += hit and pairs[key][0] in types
        c["negated_total"] += len(negated)

    return {
        "method": method, "n_sentences": len(items),
        "microbes": _prf(c["mic_tp"], c["mic_fp"], c["mic_fn"]),
        "metabolites": _prf(c["met_tp"], c["met_fp"], c["met_fn"]),
        "pairs": _prf(c["pair_tp"], c["pair_fp"], c["pair_fn"]),
        "triples": _prf(c["tri_tp"], c["tri_fp"], c["tri_fn"]),
        "negation_errors": c["neg_err"], "negated_total": c["negated_total"],
        "calibration": [{"bucket": f"{lo:.2f}-{min(hi, 1):.2f}", "n": n, "precision": round(k / n, 3) if n else None}
                        for (lo, hi), (k, n) in sorted(buckets.items())],
        "by_tag": {t: dict(v) for t, v in sorted(by_tag.items())},
        "errors": errors,
    }


def markdown(results: dict[str, dict[str, dict]]) -> str:
    L = ["# Relationship extraction: evaluation results", ""]
    for split, by_method in results.items():
        if not by_method:
            continue
        n = next(iter(by_method.values()))["n_sentences"]
        L += [f"## {split.replace('_', '-')} set ({n} sentences)", "",
              "| Method | Pair P | Pair R | Pair F1 | Triple F1 | Microbe P | Metabolite P | Negated pairs asserted |",
              "|---|---|---|---|---|---|---|---|"]
        for m, r in by_method.items():
            L.append(f"| {m} | {r['pairs']['precision']:.2f} | {r['pairs']['recall']:.2f} | {r['pairs']['f1']:.2f} | "
                     f"{r['triples']['f1']:.2f} | {r['microbes']['precision']:.2f} | {r['metabolites']['precision']:.2f} | "
                     f"{r['negation_errors']} / {r['negated_total']} |")
        L += ["", "Calibration (precision of predicted pairs by confidence):", "",
              "| Method | " + " | ".join(b["bucket"] for b in next(iter(by_method.values()))["calibration"]) + " |",
              "|---|" + "---|" * len(next(iter(by_method.values()))["calibration"])]
        for m, r in by_method.items():
            L.append(f"| {m} | " + " | ".join("–" if b["precision"] is None else f"{b['precision']:.2f} (n={b['n']})"
                                              for b in r["calibration"]) + " |")
        L.append("")
        for m, r in by_method.items():
            L += [f"<details><summary>{m}: {len(r['errors'])} errors</summary>", "",
                  "| ID | Error | Predicted | Expected |", "|---|---|---|---|"]
            L += [f"| {e['id']} | {e['error']} | {e['predicted']} | {e['expected']} |" for e in r["errors"]]
            L += ["", "</details>", ""]
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--methods", nargs="+", default=["rules_v1", "rules_v2"])
    p.add_argument("--out", default=str(RESULTS / "extraction_results.md"))
    args = p.parse_args(argv)

    results = {split: {m: evaluate(m, load(split)) for m in args.methods} for split in SPLITS if load(split)}
    RESULTS.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(markdown(results))
    Path(args.out).with_suffix(".json").write_text(json.dumps(results, indent=2))
    for split, by_method in results.items():
        for m, r in by_method.items():
            print(f"{split:9s} {m:9s} pair F1 {r['pairs']['f1']:.2f}  triple F1 {r['triples']['f1']:.2f}  "
                  f"microbe P {r['microbes']['precision']:.2f}  negation errors {r['negation_errors']}/{r['negated_total']}")
    print(f"Report: {args.out}")


if __name__ == "__main__":
    main()

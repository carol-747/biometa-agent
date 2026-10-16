# Evaluation suite

This directory measures the two things that decide whether a literature agent
can be trusted: **does extraction get the relationships right**, and **does the
agent only cite what the evidence supports**. Both run offline (no API key, no
database server) so they can gate every commit in CI.

## 1. Relationship extraction

`run_extraction_eval.py` scores extractors against hand-labeled sentences.

- **Gold data**: `data/relation_benchmark.jsonl` (70 sentences, the dev set) and
  `data/relation_heldout.jsonl` (30 sentences never used while writing the rules).
  Each sentence lists every microbe and metabolite mention, the relationships it
  *asserts* (with the set of acceptable relation types), and any pair it
  *negates*. Regenerate with `python data/build_benchmark.py` /
  `python data/build_heldout.py`.
- **Failure modes covered**: passive voice, scoped negation, multi-clause
  sentences with two subjects, "produces B from A" (substrate vs. product),
  coordinated metabolites, metabolite-acts-on-microbe, nominal forms
  ("butyrate producer"), hedging, out-of-dictionary species, and distractor
  co-mentions that assert nothing.
- **Metrics**: entity precision/recall, pair P/R/F1 (relationship found at all),
  triple F1 (found *and* correct type), count of negated pairs wrongly asserted,
  and a confidence-calibration table.

### Labeling guidelines

- A relationship is labeled only if the sentence asserts it; background
  knowledge is never used.
- "X produces B from A" → X *produces* B **and** X *consumes* A. "X converts A
  to B" accepts `converts` or the produces/consumes split.
- Negated pairs go in `negated`, not `relations`; a correct extractor returns
  nothing for them.
- Association/correlation language maps to `associates_with` (and `inhibits` /
  `activates` when a direction is explicit, e.g. "lower", "higher").

## 2. Agent groundedness

`run_agent_eval.py` checks the conversational agent against a fixture database
(`fixtures.py`, 5 articles with known relationships). Each question declares the
PMIDs that support it; questions with no supporting article should be answered
with an abstention and no citation.

Metrics: groundedness (no PMID cited that retrieval never returned), citation
precision/recall against the supporting PMIDs, and correct-abstention count.
By default it reports the baseline agent and the grounded agent side by side.

Add `--live` to grade the real Claude reply instead of the offline fallback
(needs `ANTHROPIC_API_KEY`); the same checks apply.

## Running

```bash
pip install -r evals/requirements.txt      # plus backend deps on PYTHONPATH
python evals/run_extraction_eval.py        # writes results/extraction_results.md
python evals/run_agent_eval.py             # writes results/agent_results.md
python evals/run_extraction_eval.py --methods rules_v2 llm   # needs ANTHROPIC_API_KEY
```

Results are committed under `results/` so the numbers in the top-level README
are reproducible.

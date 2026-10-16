# Agent groundedness evaluation

Mode: **offline** · 8 questions against the fixture database (5 articles). Each question declares which PMIDs support it; questions with no supporting article should be answered with an abstention and no citation.

| Variant | Groundedness | Invented citations | Citation precision | Citation recall | Correct abstentions |
|---|---|---|---|---|---|
| baseline | 100% | 0 | 0.46 | 1.00 | 2 / 3 |
| grounded (v2) | 100% | 0 | 1.00 | 1.00 | 3 / 3 |

*Groundedness* = share of replies that cite no PMID outside what retrieval returned. *Citation precision* = share of cited PMIDs that actually support the question. The baseline stays grounded (it never invents a PMID) but over-cites off-topic papers from the keyword-search fallback; the grounded variant only surfaces articles that mention a queried entity and abstains otherwise.

## Per-question detail (grounded (v2))

| Question | Supporting PMIDs | Cited | Invented | Grounded |
|---|---|---|---|---|
| What does Faecalibacterium prausnitzii produce? | 30001001 | 30001001 | — | yes |
| Which bacteria produce trimethylamine from choline? | 30001002 | 30001002 | — | yes |
| What inhibits Clostridioides difficile germination? | 30001003 | 30001003 | — | yes |
| What short-chain fatty acids does Akkermansia muciniphila produce? | 30001004 | 30001004 | — | yes |
| Does Lactobacillus reuteri affect TMAO? | 30001005 | 30001005 | — | yes |
| What metabolites does Salmonella enterica produce? | — | — | — | yes |
| Does Bifidobacterium longum degrade cellulose? | — | — | — | yes |
| What is the role of penicillin in gut inflammation? | — | — | — | yes |
# BiometaAgent

**Microbe-Metabolite Relationship Retrieval Agent**

A full-stack AI-powered system for discovering, extracting, and visualizing relationships between microorganisms and metabolites from PubMed scientific literature. Powered by Claude AI for conversational search.

What makes this more than a demo: a **measured** extraction pipeline and a
**groundedness-tested** agent. The relationship extractor and the chat agent are
both evaluated against hand-labeled benchmarks that run in CI, and the
improvements below are the before/after those evals produced.

---

## Evaluation results

Reproduce with `python evals/run_extraction_eval.py` and `python evals/run_agent_eval.py`
(offline, no API key). Full method and labeling notes in [`evals/README.md`](evals/README.md).

### Relationship extraction — v1 vs. v2

70 hand-labeled sentences (dev) covering passive voice, scoped negation,
multi-clause sentences, substrate-vs-product, and distractor co-mentions, plus a
30-sentence held-out set the rules were never tuned against.

| Set | Extractor | Pair F1 | Triple F1 | Microbe precision | Negated pairs wrongly asserted |
|---|---|---|---|---|---|
| dev | v1 (sentence-scoped) | 0.79 | 0.59 | 0.80 | 12 / 13 |
| dev | **v2 (pair-scoped)** | **0.97** | **0.97** | **1.00** | **0 / 13** |
| held-out | v1 | 0.78 | 0.59 | 0.81 | 6 / 6 |
| held-out | **v2** | **0.91** | **0.91** | **1.00** | **0 / 6** |

v1 labeled every microbe–metabolite pair in a sentence with whichever verb
appeared anywhere in it, and only halved confidence on negation. v2 reads the
words *between* each specific pair, handles passive voice and substrate/product
("produces B from A"), assigns each verb to its nearest subject, and treats
scoped negation as "no relationship". An optional Claude tool-use extractor
(`--methods llm`) is included and is held to the same benchmark.

### Agent groundedness

8 questions against a fixture database; questions with no supporting article
should be answered with an abstention and no citation.

| Agent | Groundedness | Invented citations | Citation precision | Correct abstentions |
|---|---|---|---|---|
| baseline | 100% | 0 | 0.46 | 2 / 3 |
| **grounded** | **100%** | **0** | **1.00** | **3 / 3** |

Neither version invents a PMID, but the baseline over-cites off-topic papers
returned by the keyword-search fallback; the grounded agent only surfaces
articles that mention a queried entity and abstains otherwise.

---

## MCP server

`mcp_server/server.py` exposes the literature database to any MCP client (Claude
Desktop, Claude Code) as five tools: `find_relationships`, `search_articles`,
`get_article`, `extract_from_text`, and `list_entities`. Every result carries
its source PMID, so answers built on these tools stay grounded. Setup and the
Claude Desktop config are in the file's docstring and `mcp_server/requirements.txt`.

---

## Features

| Feature | Implementation |
|---------|---------------|
| PubMed data fetching | Bio.Entrez (Biopython) — all 19 metadata fields |
| Biomedical NER | scispaCy (`en_core_sci_sm`) + dictionary matching + regex |
| Relationship extraction | Pattern matching with 8 relationship types + confidence scoring |
| Semantic search | sentence-transformers (`all-MiniLM-L6-v2`) embeddings |
| Conversational AI | Anthropic Claude API (multi-turn, context-aware) |
| REST API | FastAPI with OpenAPI docs |
| Database | PostgreSQL with SQLAlchemy ORM |
| Network visualization | Cytoscape.js with interactive graph |
| Frontend | React with dark-mode UI |
| Containerization | Docker Compose |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Anthropic API key
- (Optional) NCBI Entrez email for PubMed access

### 1. Clone and configure

```bash
git clone https://github.com/carol-747/biometa-agent
cd biometa-agent
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and ENTREZ_EMAIL
```

### 2. Launch with Docker Compose

```bash
docker-compose up --build
```

Services:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432

### 3. Fetch initial data

Via the UI:
1. Open http://localhost:3000
2. Go to the **Ingest** tab
3. Enter a query (e.g., `gut microbiome metabolite`) and click **Fetch Articles**
4. Wait for the job to complete (fetches articles + runs NLP)

Via API:
```bash
curl -X POST http://localhost:8000/api/v1/ingest/pubmed \
  -H "Content-Type: application/json" \
  -d '{"query": "microbe metabolite gut", "max_results": 1000, "run_nlp": true}'
```

### 4. Start chatting

Open http://localhost:3000 → **Chat** tab and ask:
- "What metabolites does E. coli produce?"
- "How does Lactobacillus regulate butyrate levels?"
- "Which bacteria are associated with TMAO production?"

---

## Project Structure

```
biometa-agent/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── core/
│   │   │   └── config.py           # Settings (pydantic-settings)
│   │   ├── db/
│   │   │   ├── models.py           # SQLAlchemy ORM models
│   │   │   └── database.py         # DB engine, session, init
│   │   ├── api/
│   │   │   ├── articles.py         # Article CRUD endpoints
│   │   │   ├── search.py           # Search + network endpoints
│   │   │   ├── chat.py             # Conversational agent endpoints
│   │   │   └── ingestion.py        # PubMed fetch + NLP pipeline
│   │   ├── nlp/
│   │   │   ├── entity_extractor.py # Microbe + metabolite NER
│   │   │   ├── relationship_extractor.py  # Relationship detection
│   │   │   └── semantic_search.py  # Embeddings + similarity search
│   │   └── services/
│   │       ├── pubmed_fetcher.py   # Bio.Entrez wrapper
│   │       └── agent.py            # Claude conversational agent
│   ├── tests/
│   │   ├── test_nlp.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Main app with tab navigation
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx   # Chat UI with relationship display
│   │   │   ├── NetworkGraph.jsx    # Cytoscape.js visualization
│   │   │   ├── IngestPanel.jsx     # Data fetching control panel
│   │   │   └── SearchResults.jsx   # Article search
│   │   └── utils/
│   │       └── api.js              # Axios API client
│   ├── public/index.html
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── dictionaries/
│       ├── bacteria.json           # ~80 bacterial species
│       ├── fungi.json              # ~35 fungal species
│       ├── viruses.json            # ~35 viral species
│       ├── metabolites.json        # ~120 metabolites
│       └── metabolite_classes.json # Metabolite classification
├── models/                         # (NER model cache)
├── evals/                          # offline eval suite (runs in CI)
│   ├── data/                       # gold benchmarks + generators
│   ├── run_extraction_eval.py      # v1 vs v2 vs llm on labeled sentences
│   ├── run_agent_eval.py           # citation grounding + abstention
│   ├── fixtures.py                 # in-memory DB with known relationships
│   └── results/                    # committed eval reports
├── mcp_server/                     # MCP tools over the literature DB
│   └── server.py
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Database Schema

### `articles`
All 19 PubMed metadata fields:

| Field | Type | Description |
|-------|------|-------------|
| pmid | VARCHAR | PubMed ID (unique) |
| title | TEXT | Article title |
| abstract | TEXT | Full abstract |
| authors | JSON | `[{name, affiliation}]` |
| journal | VARCHAR | Journal name |
| pub_date | VARCHAR | Publication date |
| doi | VARCHAR | Digital Object Identifier |
| keywords | JSON | Author keywords |
| mesh_terms | JSON | MeSH controlled vocabulary |
| publication_type | ARRAY | Research article, review, etc. |
| language | VARCHAR | ISO language code |
| country | VARCHAR | Publisher country |
| affiliations | JSON | Author institutions |
| citations_count | INT | Citation count |
| full_text_link | TEXT | PMC or PubMed URL |
| grant_info | JSON | `[{id, agency, country}]` |
| chemical_substances | JSON | Chemical registry entries |
| references | JSON | Reference PMID list |
| article_ids | JSON | `{type: id}` map |

### `microbes`
| Field | Description |
|-------|-------------|
| name | Normalized species name |
| microbe_type | bacteria / fungi / virus / archaea |
| taxonomy_id | NCBI taxonomy ID |
| mention_count | Times mentioned across articles |

### `metabolites`
| Field | Description |
|-------|-------------|
| name | Normalized metabolite name |
| metabolite_class | fatty acid / amino acid / bile acid / etc. |
| chebi_id / pubchem_id | Database cross-references |
| mention_count | Times mentioned across articles |

### `relationships`
| Field | Description |
|-------|-------------|
| microbe_id | FK → microbes |
| metabolite_id | FK → metabolites |
| article_id | FK → articles (source evidence) |
| relationship_type | produces / consumes / regulates / inhibits / activates / converts / associates_with / interacts |
| confidence_score | 0.0–1.0 based on pattern matching |
| evidence_sentence | Sentence from abstract |
| extraction_method | pattern / ner / llm |

---

## API Reference

Full interactive docs at http://localhost:8000/docs

### Chat Endpoints

```
POST /api/v1/chat/
```
Send a natural language query. Supports multi-turn conversation.

**Request:**
```json
{
  "message": "What metabolites does E. coli produce?",
  "session_id": null
}
```

**Response:**
```json
{
  "reply": "Based on the literature, E. coli produces...",
  "session_id": "uuid",
  "relationships": [...],
  "articles": [...],
  "analysis": {"microbes": ["E. coli"], "metabolites": [], ...}
}
```

### Search Endpoints

```
GET /api/v1/search/?q=butyrate&top_k=20
GET /api/v1/search/relationships?microbe=E.%20coli&relationship_type=produces
GET /api/v1/search/network?microbe=Lactobacillus&min_confidence=0.5
```

### Ingestion Endpoints

```
POST /api/v1/ingest/pubmed   - Start PubMed fetch job
GET  /api/v1/ingest/status/{job_id} - Poll job status
POST /api/v1/ingest/process  - Run NLP on unprocessed articles
GET  /api/v1/ingest/stats    - Database statistics
```

### Article Endpoints

```
GET /api/v1/articles/              - List articles (paginated)
GET /api/v1/articles/count         - Total article count
GET /api/v1/articles/{pmid}        - Get article by PMID
GET /api/v1/articles/{pmid}/relationships - Get relationships for article
```

---

## NLP Pipeline

### Entity Extraction (3-tier)
1. **Dictionary matching**: Fast regex over curated lists of bacteria, fungi, viruses, metabolites
2. **spaCy NER** *(optional)*: biomedical NER via scispaCy's `en_core_sci_sm` when installed, falling back to `en_core_web_sm`; skipped entirely if spaCy is absent (dictionary + regex still run)
3. **Pattern matching**: genus-aware binomial species regex for entities not in the dictionaries

### Relationship Extraction
Identifies 8 relationship types (`produces`, `consumes`, `converts`, `inhibits`,
`activates`, `regulates`, `associates_with`, `interacts`) from sentences
containing both a microbe and a metabolite. Two rule-based extractors are
available (selected with `method=`), plus an optional Claude tool-use extractor:

- **`rules_v2` (default)** — *pair-scoped*: for each microbe–metabolite pair it
  reads only the text linking that specific pair. It handles passive voice
  ("B is produced by X"), substrate vs. product ("produces B from A" → produces
  B **and** consumes A), nearest-subject assignment in multi-clause sentences,
  and **scoped negation — a negated pair yields no relationship** (it is not
  emitted at all).
- **`rules_v1` (legacy)** — *sentence-scoped*: labels every pair in a sentence
  with whichever trigger word appears anywhere in it, and only halves the
  confidence on negation. Kept for the before/after comparison in the evals.

Confidence scoring (rules) combines a base trigger-match score, entity proximity,
and directional cues; hedging ("may", "suggest") lowers it. See the measured
accuracy of each method in [Evaluation results](#evaluation-results) and
[`evals/`](evals/).

### Semantic Search
Uses `all-MiniLM-L6-v2` (384-dim embeddings) with cosine similarity. Falls back to ILIKE keyword search if embeddings unavailable.

---

## Development

### Run backend locally

```bash
cd backend
pip install -r requirements.txt
# Optional biomedical NER (dictionary + regex extraction work without it):
#   pip install scispacy && pip install <en_core_sci_sm wheel URL from the scispaCy releases>
# or a lighter fallback:  python -m spacy download en_core_web_sm
export DATABASE_URL=postgresql://biometa:biometa_secret@localhost:5432/biometa_db
export ANTHROPIC_API_KEY=your_key
uvicorn app.main:app --reload
```

### Run tests

```bash
cd backend
pytest tests/ -v
```

### Run the evals

```bash
python evals/run_extraction_eval.py     # extraction: v1 vs v2, dev + held-out
python evals/run_agent_eval.py          # agent: citation grounding + abstention
```

Both run offline and write reports to `evals/results/`. Add `ANTHROPIC_API_KEY`
and `--methods rules_v2 llm` (extraction) or `--live` (agent) to evaluate the
Claude-based paths.

### Run frontend locally

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000 npm start
```

---

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for conversational AI |
| `ENTREZ_EMAIL` | researcher@example.com | NCBI requires email for Entrez |
| `DATABASE_URL` | postgresql://... | PostgreSQL connection string |
| `MAX_PUBMED_RESULTS` | 5000 | Cap on PubMed fetch per query |
| `DEBUG` | false | Enable debug logging |

---

## Architecture

```
User Browser
    │
    ▼
React Frontend (port 3000)
    │ REST API calls
    ▼
FastAPI Backend (port 8000)
    ├── /api/v1/chat/     → ConversationalAgent → Claude API
    ├── /api/v1/search/   → SemanticSearch → PostgreSQL
    ├── /api/v1/ingest/   → PubMedFetcher → NLP Pipeline → PostgreSQL
    └── /api/v1/articles/ → PostgreSQL
    │
    ▼
PostgreSQL (port 5432)
    ├── articles (19 fields)
    ├── microbes
    ├── metabolites
    ├── relationships
    └── conversation_sessions
```

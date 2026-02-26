# BiometaAgent

**Microbe-Metabolite Relationship Retrieval Agent**

A full-stack AI-powered system for discovering, extracting, and visualizing relationships between microorganisms and metabolites from PubMed scientific literature. Powered by Claude AI for conversational search.

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
git clone <repo>
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
2. **scispaCy NER**: Biomedical named entity recognition (`en_core_sci_sm` model)
3. **Pattern matching**: Binomial species name regex for novel entities

### Relationship Extraction
Pattern-based extraction identifies 8 relationship types from sentences containing both a microbe and metabolite:

| Type | Example patterns |
|------|-----------------|
| produces | produces, secretes, synthesizes, generates |
| consumes | consumes, metabolizes, degrades, utilizes |
| regulates | regulates, modulates, controls, affects |
| inhibits | inhibits, suppresses, blocks, decreases |
| activates | activates, stimulates, induces, promotes |
| converts | converts, transforms, catalyzes |
| associates_with | associates, correlates, linked to |
| interacts | interacts, binds, reacts |

Confidence scoring includes:
- Pattern match strength (0.65 base)
- Entity proximity within sentence (+0–15%)
- Directional order (microbe before metabolite for "produces")
- Negation detection (50% penalty)

### Semantic Search
Uses `all-MiniLM-L6-v2` (384-dim embeddings) with cosine similarity. Falls back to ILIKE keyword search if embeddings unavailable.

---

## Development

### Run backend locally

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
export DATABASE_URL=postgresql://biometa:biometa_secret@localhost:5432/biometa_db
export ANTHROPIC_API_KEY=your_key
uvicorn app.main:app --reload
```

### Run tests

```bash
cd backend
pytest tests/ -v
```

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

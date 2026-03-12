# MinDD Startup Intelligence System

A multi-tenant RAG (Retrieval-Augmented Generation) backend for startup due-diligence.  
Ingests pitch decks, financial models, and investor updates; answers investor questions with grounded evidence.

---

## Features

| Feature | Description |
|---|---|
| Multi-tenant ingestion | PDF, TXT, Excel per startup; strict data isolation |
| Spreadsheet reasoning | Extracts values, formulas, and financial metrics from Excel |
| Semantic retrieval | FAISS vector search (per startup) + structured metric injection |
| QA answering | OpenAI GPT-4 with grounded citations; rule-based fallback |
| Cross-startup comparison | Compare two or more startups side-by-side |
| Evaluation framework | 12 investor questions with grounding + hallucination checks |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
copy .env.example .env
# Edit .env and set OPENAI_API_KEY (optional but recommended)
```

### 3. Generate sample data

```bash
python scripts/generate_sample_data.py
```

This creates two sample startups under `data/startups/`:
- **alpha** — AlphaFlow (B2B SaaS workflow automation)
- **beta** — BetaMart (E-commerce artisan marketplace)

Each startup has: `pitch_deck.pdf`, `investor_update.pdf`, `financial_model.xlsx`

### 4. Start the API server

```bash
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive API documentation.

### 5. Ingest startups

```bash
# Ingest AlphaFlow
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"startup_id": "alpha", "startup_name": "AlphaFlow", "description": "B2B SaaS"}'

# Ingest BetaMart
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"startup_id": "beta", "startup_name": "BetaMart", "description": "E-commerce marketplace"}'
```

### 6. Ask questions

```bash
# Single startup query
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"startup_id": "alpha", "question": "What is the company burn rate and runway?"}'

# Cross-startup comparison
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"startup_ids": ["alpha", "beta"], "question": "Which company has stronger financial traction?"}'
```

### 7. Run evaluation

```bash
# Via script (ingests + evaluates end-to-end)
python scripts/run_evaluation.py

# Or via API after ingestion
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"startup_id": "alpha"}'
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest` | Ingest all documents for a startup |
| `DELETE` | `/ingest/{startup_id}` | Remove all data for a startup |
| `POST` | `/ask` | Answer investor question (single startup) |
| `POST` | `/compare` | Compare multiple startups |
| `POST` | `/evaluate` | Run evaluation suite |
| `GET` | `/startups` | List all ingested startups |
| `GET` | `/startups/{id}/metrics` | Get structured financial metrics |
| `GET` | `/health` | Health check |

### POST /ask

```json
{
  "startup_id": "alpha",
  "question": "What is the company's runway?",
  "top_k": 5
}
```

Response:
```json
{
  "startup_id": "alpha",
  "question": "...",
  "answer": "Based on the financial model, AlphaFlow has approximately 12.5 months of runway...",
  "evidence": [{"text": "...", "source": "financial_model.xlsx", "score": 0.92}],
  "sources": ["financial_model.xlsx", "investor_update.pdf"],
  "metrics": [{"metric_name": "runway", "value": 12.5, "unit": "months"}]
}
```

### POST /compare

```json
{
  "startup_ids": ["alpha", "beta"],
  "question": "Which company has stronger financial traction?"
}
```

---

## Project Structure

```
mindd-startup-intelligence/
├── main.py                          # FastAPI app entry point
├── config.py                        # Settings (env vars)
├── requirements.txt
├── .env.example
│
├── app/
│   ├── api/
│   │   ├── schemas.py               # Pydantic request/response models
│   │   └── routes/
│   │       ├── ingest.py            # POST /ingest
│   │       ├── ask.py               # POST /ask, GET /startups
│   │       ├── compare.py           # POST /compare
│   │       └── evaluate.py          # POST /evaluate
│   │
│   ├── ingestion/
│   │   ├── document_parser.py       # PDF + text parsing
│   │   ├── spreadsheet_parser.py    # Excel with formula resolution
│   │   ├── chunker.py               # Overlapping text chunking
│   │   └── pipeline.py              # Orchestrates full ingestion
│   │
│   ├── retrieval/
│   │   ├── embedder.py              # sentence-transformers / OpenAI
│   │   ├── vector_store.py          # Per-tenant FAISS index
│   │   └── retriever.py             # Retrieval pipeline
│   │
│   ├── reasoning/
│   │   ├── qa_chain.py              # Single-startup QA
│   │   └── comparison.py            # Cross-startup comparison
│   │
│   ├── evaluation/
│   │   ├── evaluator.py             # Grounding + hallucination checks
│   │   └── test_questions.py        # 12 investor questions
│   │
│   └── storage/
│       └── metadata_store.py        # SQLAlchemy + SQLite
│
├── scripts/
│   ├── generate_sample_data.py      # Create sample PDFs + Excel
│   └── run_evaluation.py            # End-to-end evaluation runner
│
├── data/startups/
│   ├── alpha/                       # AlphaFlow documents
│   └── beta/                        # BetaMart documents
│
├── storage/
│   ├── mindd.db                     # SQLite (created at runtime)
│   └── indexes/
│       ├── alpha/                   # AlphaFlow FAISS index
│       └── beta/                    # BetaMart FAISS index
│
├── evaluation/
│   └── results.json                 # Evaluation output
│
└── architecture/
    ├── diagram.md                   # System architecture diagrams
    └── design_memo.md               # 4-page architecture decision memo
```

---

## Configuration

All settings in `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(empty)* | OpenAI key for GPT reasoning + embeddings |
| `EMBEDDING_MODEL` | `sentence-transformers` | `sentence-transformers` or `openai` |
| `ST_MODEL_NAME` | `all-MiniLM-L6-v2` | Sentence-Transformers model |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `RETRIEVAL_TOP_K` | `5` | Number of chunks to retrieve |

**Without OpenAI key**: embeddings use sentence-transformers (downloaded ~90MB on first run); answers use rule-based fallback showing relevant metrics and document excerpts.

**With OpenAI key**: full AI-powered answering with citations.

---

## Architecture Decision

See `architecture/design_memo.md` for the full 4-page memo.

**Summary**: We use **Option A (dedicated FAISS index per startup)** over Option B (shared index with metadata filtering) because:
1. Physical isolation eliminates cross-tenant data leakage by construction
2. No risk of filter bugs exposing one investor's portfolio data to another
3. Simple tenant deletion (delete one file)
4. Scales to 50K startups with S3 + LRU caching (see memo Section 5)

---

## Evaluation Results

The evaluation framework runs 12 investor questions per startup and measures:
- **Grounding score**: fraction of answer content found in retrieved context (target > 0.6)
- **Retrieval relevance**: correct source type retrieved (target > 0.8)
- **Hallucination rate**: answers with uncited numeric claims (target < 0.1)

Run `python scripts/run_evaluation.py` to generate `evaluation/results.json`.

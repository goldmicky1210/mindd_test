# MinDD System Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT / INVESTOR                              │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │  HTTPS REST
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Gateway                                 │
│                                                                         │
│   POST /ingest     POST /ask     POST /compare     POST /evaluate       │
└────────┬───────────────┬──────────────┬──────────────────┬─────────────┘
         │               │              │                  │
         ▼               │              │                  │
┌────────────────┐       │              │                  │
│  Ingestion     │       │              │                  │
│  Pipeline      │       │              │                  │
│                │       │              │                  │
│ ┌────────────┐ │       │              │                  │
│ │ Doc Parser │ │       │              │                  │
│ │  (PDF/TXT) │ │       │              │                  │
│ └────────────┘ │       │              │                  │
│ ┌────────────┐ │       │              │                  │
│ │ Sheet      │ │       │              │                  │
│ │ Parser     │ │       │              │                  │
│ │ (Excel +   │ │       │              │                  │
│ │  Formulas) │ │       │              │                  │
│ └────────────┘ │       │              │                  │
│ ┌────────────┐ │       │              │                  │
│ │  Chunker   │ │       │              │                  │
│ └─────┬──────┘ │       │              │                  │
└───────┼────────┘       │              │                  │
        │                │              │                  │
        ▼                ▼              ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Embedder                                       │
│            sentence-transformers (all-MiniLM-L6-v2)                    │
│                    OR  OpenAI text-embedding-3-small                    │
└──────────────────────┬────────────────────────────────┬────────────────┘
                       │                                │
           ┌───────────▼───────────┐        ┌──────────▼──────────┐
           │  Per-Startup          │        │   SQLite Metadata   │
           │  FAISS Index          │        │   Store             │
           │                       │        │                     │
           │  storage/indexes/     │        │  - startups         │
           │  ├─ alpha/            │        │  - documents        │
           │  │  ├─ index.faiss    │        │  - financial_metrics│
           │  │  └─ metadata.json  │        │                     │
           │  └─ beta/             │        │  storage/mindd.db   │
           │     ├─ index.faiss    │        └──────────┬──────────┘
           │     └─ metadata.json  │                   │
           └───────────┬───────────┘                   │
                       │                               │
                       └──────────────┬────────────────┘
                                      │
                              ┌───────▼────────┐
                              │   Retriever     │
                              │                 │
                              │  1. Embed query │
                              │  2. FAISS search│
                              │     (per-tenant)│
                              │  3. Fetch metrics│
                              │  4. Build context│
                              └───────┬─────────┘
                                      │
                              ┌───────▼─────────┐
                              │   Reasoning     │
                              │                 │
                              │  QA Chain  /    │
                              │  Comparison     │
                              │                 │
                              │  OpenAI GPT-4   │
                              │  (or fallback)  │
                              └───────┬─────────┘
                                      │
                              ┌───────▼─────────┐
                              │  API Response   │
                              │  - answer       │
                              │  - evidence     │
                              │  - sources      │
                              │  - metrics      │
                              └─────────────────┘
```

## Multi-Tenant Isolation

```
Request: { "startup_id": "alpha", "question": "..." }
                │
                ▼
        Tenant Boundary Check
                │
      ┌─────────▼──────────┐
      │  FAISS Index:alpha  │  ← only alpha's vectors
      │  Metrics: alpha     │  ← only alpha's metrics
      └─────────────────────┘
                │
        No cross-tenant data possible
```

## Cross-Startup Comparison Flow

```
Request: { "startup_ids": ["alpha","beta"], "question": "..." }
                │
         ┌──────┴──────┐
         ▼             ▼
    Retrieve(alpha)  Retrieve(beta)
         │             │
         └──────┬───────┘
                ▼
        Combined Context
                │
         LLM Comparison
                │
         Comparative Answer
```

## Data Flow: Spreadsheet Ingestion

```
financial_model.xlsx
        │
        ▼
  openpyxl (data_only=True)   ──→  cell values
  openpyxl (data_only=False)  ──→  formulas
        │
        ▼
  Formula Extractor
  ┌─────────────────────────────────┐
  │  = B2 / C2  → Runway = Cash/Burn│
  │  = (B2-A2)/A2 → Growth rate     │
  └─────────────────────────────────┘
        │
   ┌────┴──────────┐
   ▼               ▼
Structured      Text Chunks
Metrics         (for embedding)
(SQLite)        (FAISS)
```

# MinDD Architecture Design Memo

**Author:** MinDD Engineering  
**Date:** March 2026  
**Version:** 1.0

---

## 1. Executive Summary

This memo describes the architecture of the MinDD Startup Intelligence System — a multi-tenant RAG (Retrieval-Augmented Generation) backend that ingests startup documents and financial models, then answers investor questions with evidence grounded in company data.

The core architectural recommendation is **Option A: one dedicated FAISS index per startup**, combined with a shared SQLite metadata store for structured financial metrics.

---

## 2. System Overview

The system consists of five layers:

| Layer | Component | Technology |
|---|---|---|
| API | REST gateway | FastAPI |
| Ingestion | Doc + spreadsheet parsing | pdfplumber, openpyxl |
| Embedding | Vector representation | sentence-transformers / OpenAI |
| Retrieval | Semantic search | FAISS (per-tenant) |
| Reasoning | Answer generation | OpenAI GPT-4 / rule-based fallback |

---

## 3. Architecture Decision: Option A vs Option B

### Option A — Dedicated Index Per Startup
Each startup has its own isolated FAISS index stored at `storage/indexes/<startup_id>/`.

**Advantages:**
- **Zero cross-tenant data leakage**: impossible by construction. Each tenant's vectors are in a separate file and never searched together.
- **Simple deletion**: removing a startup's data is a single `DELETE` — no complex metadata filter needed.
- **Performance isolation**: a pathological startup with 10,000 documents does not degrade search latency for others.
- **Index tuning per tenant**: future work could use HNSW for large startups and flat search for small ones.
- **Compliance-friendly**: auditors can verify that Startup B's data is physically absent from Startup A's index.

**Disadvantages:**
- **Memory overhead**: loading N indexes into memory simultaneously requires N × (index size) RAM. Mitigated with lazy-loading (only load indexes for active requests).
- **Cross-tenant operations**: comparison queries require loading two indexes, not one search call. This is acceptable because comparisons are explicitly multi-tenant.
- **Index file management**: at 50,000 startups, the filesystem has 50,000 index files. Manageable with object storage (S3) and a caching layer.

### Option B — Shared Index with Metadata Filtering
All vectors in one large index; `startup_id` is a metadata field filtered at query time.

**Advantages:**
- Single index to manage.
- Cross-startup batch operations (e.g., sector benchmarks) are efficient.

**Disadvantages:**
- **Metadata filtering in FAISS is not native**: FAISS does not support filtered search. You must either (a) post-filter (retrieve 10× and discard), wasting compute, or (b) use a different engine (Pinecone, Weaviate, Qdrant) that supports payload filtering natively.
- **Data leakage risk**: a filter bug or missing filter parameter can expose another startup's data. In investment due diligence, this is a critical compliance failure.
- **Scaling difficulty**: a single index with 1B vectors is hard to partition and rebuild.
- **Noisy neighbors**: a poorly chunked document from one startup can appear in another's results if the filter fails.

### Recommendation: **Option A**

For MinDD's use case (strict multi-tenancy, compliance, due diligence), Option A's physical isolation is the correct default. The performance cost is manageable with the optimizations described in Section 5.

---

## 4. Financial Spreadsheet Reasoning

Financial models are treated as first-class data sources with two complementary representations:

**Structured metrics (SQLite)**  
Key financial indicators (ARR, burn rate, runway, gross margin, etc.) are extracted from the spreadsheet and stored as typed values. These are always included in the retrieval context regardless of semantic similarity, ensuring critical metrics are never missed.

**Text chunks (FAISS)**  
Each sheet is converted to a human-readable text block and embedded. This enables natural language queries like "what assumptions drive revenue?" to retrieve relevant formula descriptions and row labels.

**Formula resolution**  
- `openpyxl` is loaded twice: once with `data_only=False` (formulas as strings) and once with `data_only=True` (computed values).
- Formula strings (e.g., `=B2/C2`) are preserved as text for transparency.
- Derived metrics like `Runway = Cash / Monthly Burn` are surfaced as both a formula string (for explanation) and a numeric value (for answering quantitative questions).

This hybrid approach handles both quantitative questions ("What is the runway?") and qualitative questions ("How is runway calculated?").

---

## 5. Scaling to 50,000 Startups

The current SQLite + local FAISS design is suitable for development and small production. Here is the migration path to 50,000 startups:

### Ingestion

| Concern | Solution |
|---|---|
| Sync ingestion blocks API | Move to async task queue (Celery + Redis or AWS SQS) |
| Large PDFs | Streaming parse with pdfplumber; parallelise page extraction |
| Excel with 100K rows | Process in batches; skip empty rows early |
| Duplicate ingestion | Content-hash deduplication before embedding |

### Storage

| Concern | Solution |
|---|---|
| 50K FAISS files on disk | Store indexes in S3; LRU cache of N most-active in memory |
| SQLite doesn't scale | Migrate to PostgreSQL (with pgvector extension for embeddings) OR keep SQLite per-tenant |
| Index rebuild time | Incremental index updates; nightly full rebuild |

### Retrieval

| Concern | Solution |
|---|---|
| Loading FAISS index per request | In-memory LRU cache of top-K most-queried startups (TTL eviction) |
| Cold start latency | Pre-warm cache for active startups on server startup |
| Large indexes (10K+ chunks) | Switch from `IndexFlatIP` to `IndexHNSWFlat` (approximate; 10× faster at 1M+ vectors) |
| Embedding latency | Batch embedding pipeline; cache query embeddings |

### Multi-Region / High Availability

```
Investor Request
    │
    ▼
Load Balancer (AWS ALB)
    │
    ├── API Node 1 (FastAPI)
    ├── API Node 2 (FastAPI)
    └── API Node N (FastAPI)
         │
         ├── Shared: PostgreSQL (startup metadata, financial metrics)
         ├── Shared: Redis (query embedding cache, LRU index cache keys)
         └── Shared: S3 (FAISS index files, raw documents)
```

### Cost Analysis (50,000 Startups)

Assumptions: avg 20 docs/startup, avg 5 chunks/doc = 5M chunks total.

| Component | Monthly Cost |
|---|---|
| Embedding (one-time, OpenAI 3-small) | ~$15 total for 5M chunks |
| S3 storage (5M × 0.5KB vectors) | ~$0.06/month |
| PostgreSQL (RDS t3.medium) | ~$70/month |
| Redis cache (t3.micro) | ~$25/month |
| API servers (2× t3.medium) | ~$120/month |
| LLM inference (GPT-4o-mini, 10K queries/day) | ~$45/month |
| **Total** | **~$260/month** |

---

## 6. Retrieval Quality

The system implements a hybrid retrieval strategy:

1. **Semantic search** (FAISS cosine similarity): finds contextually relevant text passages.
2. **Structured metric injection**: always injects all financial metrics as structured context, bypassing the retrieval step for quantitative data. This prevents the common failure mode where a burn rate question fails because the embedding search didn't surface the right cell.
3. **Evidence ranking**: chunks ranked by cosine similarity score; metrics shown first.

**Future improvements (extra credit):**
- **Reranking**: use a cross-encoder (e.g., ms-marco-MiniLM) to rerank top-20 to top-5.
- **Query classification**: classify question as `financial_metric` vs `qualitative` to weight metric injection accordingly.
- **Hybrid BM25 + semantic**: add BM25 keyword search for exact metric name matching; fuse scores with RRF.

---

## 7. Multi-Tenant Security

- **Tenant isolation**: all retrieval and reasoning operations require an explicit `startup_id`. There is no global search path.
- **No cross-contamination**: vector indexes are separate files; metadata queries use `WHERE startup_id = ?` with parameterised queries.
- **Deletion**: `DELETE /ingest/{startup_id}` removes the FAISS index file and all database rows. No residual data.
- **Future**: add JWT-based auth where each token is scoped to a set of `startup_id` values.

---

## 8. Conclusion

The MinDD architecture uses physical tenant isolation (Option A) with a hybrid retrieval approach (semantic + structured metrics) to deliver accurate, grounded answers on startup financial data. The design is production-ready for small-to-medium scale and has a clear migration path to 50,000+ startups using standard cloud infrastructure.

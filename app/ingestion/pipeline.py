"""
Ingestion pipeline: reads all documents for a startup, parses them,
embeds the chunks, stores vectors in FAISS, and saves metadata to SQLite.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from app.ingestion.chunker import chunk_text
from app.ingestion.document_parser import parse_document
from app.ingestion.spreadsheet_parser import parse_spreadsheet
from app.retrieval.embedder import Embedder
from app.retrieval.vector_store import VectorStore
from app.storage.metadata_store import metadata_store
from config import settings


SUPPORTED_DOCS = {".pdf", ".txt", ".md"}
SUPPORTED_SHEETS = {".xlsx", ".xls"}


def ingest_startup(
    startup_id: str,
    startup_name: str,
    startup_dir: str | Path | None = None,
    description: str = "",
) -> dict[str, Any]:
    """
    Ingest all documents in *startup_dir* (defaults to data/startups/<startup_id>).
    Returns a summary of what was ingested.
    """
    if startup_dir is None:
        startup_dir = Path(settings.data_dir) / startup_id
    else:
        startup_dir = Path(startup_dir)

    if not startup_dir.exists():
        raise FileNotFoundError(f"Startup directory not found: {startup_dir}")

    # Register startup
    metadata_store.upsert_startup(startup_id, startup_name, description)

    embedder = Embedder()
    vector_store = VectorStore(startup_id)

    summary: dict[str, Any] = {
        "startup_id": startup_id,
        "documents_ingested": [],
        "total_chunks": 0,
        "metrics_extracted": 0,
    }

    for file_path in startup_dir.iterdir():
        # Skip hidden files and Excel temporary lock files
        if file_path.name.startswith("~$") or file_path.name.startswith("."):
            continue
        suffix = file_path.suffix.lower()

        if suffix in SUPPORTED_DOCS:
            result = _ingest_document(
                file_path, startup_id, embedder, vector_store
            )
            summary["documents_ingested"].append(result)
            summary["total_chunks"] += result["chunks"]

        elif suffix in SUPPORTED_SHEETS:
            result = _ingest_spreadsheet(
                file_path, startup_id, embedder, vector_store
            )
            summary["documents_ingested"].append(result)
            summary["total_chunks"] += result["chunks"]
            summary["metrics_extracted"] += result.get("metrics", 0)

    vector_store.save()
    return summary


def _ingest_document(
    file_path: Path,
    startup_id: str,
    embedder: Embedder,
    vector_store: VectorStore,
) -> dict[str, Any]:
    text = parse_document(file_path)
    chunks = chunk_text(text)

    doc_id = f"{startup_id}::{file_path.name}"
    metadata_store.add_document(
        doc_id=doc_id,
        startup_id=startup_id,
        filename=file_path.name,
        doc_type=file_path.suffix.lstrip("."),
        chunk_count=len(chunks),
    )

    chunk_metas = [
        {
            "startup_id": startup_id,
            "source": file_path.name,
            "doc_type": file_path.suffix.lstrip("."),
            "chunk_index": i,
            "text": chunk,
        }
        for i, chunk in enumerate(chunks)
    ]

    if chunk_metas:
        embeddings = embedder.embed_texts([c["text"] for c in chunk_metas])
        vector_store.add(embeddings, chunk_metas)

    return {"file": file_path.name, "type": "document", "chunks": len(chunks)}


def _ingest_spreadsheet(
    file_path: Path,
    startup_id: str,
    embedder: Embedder,
    vector_store: VectorStore,
) -> dict[str, Any]:
    parsed = parse_spreadsheet(file_path)
    text_chunks = parsed["text_chunks"]
    metrics = parsed["metrics"]

    doc_id = f"{startup_id}::{file_path.name}"
    metadata_store.add_document(
        doc_id=doc_id,
        startup_id=startup_id,
        filename=file_path.name,
        doc_type="excel",
        chunk_count=len(text_chunks),
    )

    # Store structured financial metrics
    for metric in metrics:
        metric_id = f"{startup_id}::{file_path.name}::{metric['metric_name']}::{metric.get('sheet','')}"
        metadata_store.upsert_financial_metric(
            metric_id=metric_id,
            startup_id=startup_id,
            metric_name=metric["metric_name"],
            value=metric.get("value"),
            value_text=metric.get("value_text"),
            unit=metric.get("unit"),
            period=metric.get("period"),
            source_file=file_path.name,
            extra={"sheet": metric.get("sheet"), "display_name": metric.get("display_name")},
        )

    # Embed text chunks
    chunk_metas = [
        {
            "startup_id": startup_id,
            "source": file_path.name,
            "doc_type": "excel",
            "chunk_index": i,
            "text": chunk,
        }
        for i, chunk in enumerate(text_chunks)
    ]

    if chunk_metas:
        embeddings = embedder.embed_texts([c["text"] for c in chunk_metas])
        vector_store.add(embeddings, chunk_metas)

    return {
        "file": file_path.name,
        "type": "excel",
        "chunks": len(text_chunks),
        "metrics": len(metrics),
    }

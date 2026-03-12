"""
Retrieval pipeline: given a startup_id + question, return relevant chunks
plus structured financial metrics.
"""

from __future__ import annotations

from app.retrieval.embedder import Embedder
from app.retrieval.vector_store import VectorStore
from app.storage.metadata_store import metadata_store
from config import settings


class Retriever:
    def __init__(self, startup_id: str):
        self.startup_id = startup_id
        self._embedder = Embedder()
        self._vector_store = VectorStore(startup_id)

    def retrieve(self, question: str, top_k: int | None = None) -> dict:
        """
        Returns:
          {
            "chunks":  list[dict],   # vector-retrieved text chunks
            "metrics": list[dict],   # structured financial metrics from DB
            "context": str,          # concatenated context ready for LLM
          }
        """
        k = top_k or settings.retrieval_top_k

        # Vector search
        query_vec = self._embedder.embed_query(question)
        chunks = self._vector_store.search(query_vec, top_k=k)

        # Structured metrics (always included – cheap lookup)
        metrics = metadata_store.get_financial_metrics(self.startup_id)

        context = _build_context(chunks, metrics)

        return {
            "chunks": chunks,
            "metrics": metrics,
            "context": context,
        }


def _build_context(chunks: list[dict], metrics: list[dict]) -> str:
    parts: list[str] = []

    if metrics:
        metric_lines = ["[Structured Financial Metrics]"]
        for m in metrics:
            name = m["metric_name"].replace("_", " ").title()
            val = m.get("value_text") or (f"{m['value']}" if m.get("value") is not None else "N/A")
            unit = m.get("unit") or ""
            period = f" ({m['period']})" if m.get("period") else ""
            metric_lines.append(f"  {name}: {val} {unit}{period}".rstrip())
        parts.append("\n".join(metric_lines))

    if chunks:
        parts.append("[Retrieved Document Excerpts]")
        for i, chunk in enumerate(chunks, start=1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            score = chunk.get("score", 0.0)
            parts.append(f"[{i}] Source: {source} (relevance: {score:.3f})\n{text}")

    return "\n\n".join(parts)

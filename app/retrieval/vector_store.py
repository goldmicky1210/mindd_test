"""
Per-startup FAISS vector store.

Each startup gets its own isolated index stored under:
  storage/indexes/<startup_id>/index.faiss
  storage/indexes/<startup_id>/metadata.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from config import settings


class VectorStore:
    def __init__(self, startup_id: str):
        self.startup_id = startup_id
        self._dir = settings.indexes_dir / startup_id
        self._dir.mkdir(parents=True, exist_ok=True)

        self._index_path = self._dir / "index.faiss"
        self._meta_path = self._dir / "metadata.json"

        self._index: faiss.Index | None = None
        self._metadata: list[dict[str, Any]] = []

        if self._index_path.exists() and self._meta_path.exists():
            self._load()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def add(self, embeddings: np.ndarray, metadata: list[dict[str, Any]]):
        """Add vectors + associated metadata. embeddings shape: (N, dim)."""
        if embeddings.shape[0] == 0:
            return

        embeddings = embeddings.astype(np.float32)
        dim = embeddings.shape[1]

        if self._index is None:
            self._index = faiss.IndexFlatIP(dim)  # inner-product (cosine on L2-norm)

        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        self._index.add(embeddings)
        self._metadata.extend(metadata)

    def save(self):
        if self._index is None:
            return
        faiss.write_index(self._index, str(self._index_path))
        self._meta_path.write_text(json.dumps(self._metadata, ensure_ascii=False), encoding="utf-8")

    def reset(self):
        """Delete index and metadata for fresh re-ingestion."""
        self._index = None
        self._metadata = []
        if self._index_path.exists():
            self._index_path.unlink()
        if self._meta_path.exists():
            self._meta_path.unlink()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[dict[str, Any]]:
        """Return top-k matching chunks with scores."""
        if self._index is None or self._index.ntotal == 0:
            return []

        query_vector = query_vector.astype(np.float32)
        faiss.normalize_L2(query_vector)

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_vector, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = dict(self._metadata[idx])
            meta["score"] = float(score)
            results.append(meta)

        return results

    @property
    def is_empty(self) -> bool:
        return self._index is None or self._index.ntotal == 0

    @property
    def total_chunks(self) -> int:
        return len(self._metadata)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load(self):
        self._index = faiss.read_index(str(self._index_path))
        self._metadata = json.loads(self._meta_path.read_text(encoding="utf-8"))

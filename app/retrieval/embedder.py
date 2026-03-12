"""Embedding generation – sentence-transformers (default) or OpenAI."""

from __future__ import annotations

import numpy as np
from config import settings


class Embedder:
    """Unified embedder that wraps either sentence-transformers or OpenAI."""

    def __init__(self):
        self._model = None
        self._openai_client = None
        self.dim: int = 0
        self._init()

    def _init(self):
        if settings.use_openai_embeddings:
            from openai import OpenAI

            self._openai_client = OpenAI(api_key=settings.openai_api_key)
            self.dim = 1536  # text-embedding-ada-002 / text-embedding-3-small
        else:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.st_model_name)
            self.dim = self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Return shape (N, dim) float32 array."""
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        if self._openai_client:
            return self._embed_openai(texts)
        return self._embed_st(texts)

    def embed_query(self, query: str) -> np.ndarray:
        """Return shape (1, dim) float32 array."""
        return self.embed_texts([query])

    def _embed_st(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return vecs.astype(np.float32)

    def _embed_openai(self, texts: list[str]) -> np.ndarray:
        response = self._openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        vecs = [item.embedding for item in response.data]
        return np.array(vecs, dtype=np.float32)

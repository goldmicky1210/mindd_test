"""Split text into overlapping chunks suitable for embedding."""

from __future__ import annotations


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[str]:
    """
    Split *text* into chunks of at most *chunk_size* characters with
    *overlap* characters of context carried over between chunks.

    Splitting prefers paragraph breaks, then sentence breaks, falling back
    to hard character slicing.
    """
    if not text or not text.strip():
        return []

    # Split on double newlines first (paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # Para fits in the current chunk
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            # Save what we have
            if current:
                chunks.append(current)
                # Keep overlap tail
                current = _tail(current, overlap)

            # Para itself may be longer than chunk_size – break it by sentences
            if len(para) > chunk_size:
                for sentence_chunk in _split_long(para, chunk_size, overlap):
                    if len(current) + len(sentence_chunk) + 2 <= chunk_size:
                        current = (current + " " + sentence_chunk).strip()
                    else:
                        if current:
                            chunks.append(current)
                            current = _tail(current, overlap)
                        current = sentence_chunk
            else:
                current = (_tail(current, overlap) + "\n\n" + para).strip()

    if current:
        chunks.append(current)

    return [c for c in chunks if c.strip()]


def _tail(text: str, n: int) -> str:
    """Return the last *n* characters of *text*."""
    return text[-n:] if len(text) > n else text


def _split_long(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Hard-split a long paragraph by sentences then characters."""
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= chunk_size:
            current = (current + " " + sent).strip()
        else:
            if current:
                chunks.append(current)
                current = _tail(current, overlap)
            if len(sent) > chunk_size:
                # Hard slice
                for i in range(0, len(sent), chunk_size - overlap):
                    chunks.append(sent[i : i + chunk_size])
                current = ""
            else:
                current = sent
    if current:
        chunks.append(current)
    return chunks

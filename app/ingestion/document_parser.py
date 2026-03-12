"""Parse PDF and plain-text documents into raw text."""

from pathlib import Path


def parse_document(file_path: str | Path) -> str:
    """Extract text from a PDF or text file."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(path)
    elif suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported document type: {suffix}")


def _parse_pdf(path: Path) -> str:
    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text.strip())
        return "\n\n".join(text_parts)
    except Exception as exc:
        raise RuntimeError(f"Failed to parse PDF {path}: {exc}") from exc

"""
QA chain: uses retrieved context to answer investor questions.
Falls back to a template-based answer if no OpenAI key is configured.
"""

from __future__ import annotations

from app.retrieval.retriever import Retriever
from config import settings

SYSTEM_PROMPT = """You are a financial analyst assistant for an investment intelligence platform.
You have access to a startup's pitch deck, investor updates, and financial model data.
Answer the investor's question accurately using ONLY the provided context.
Always cite the source of your information (e.g., "According to the financial model..." or "The pitch deck states...").
If the context does not contain enough information to answer the question, say so clearly.
Be concise but thorough. Use numbers and metrics when available."""

USER_TEMPLATE = """Context:
{context}

Investor Question: {question}

Please provide a detailed answer with evidence citations."""


def answer_question(
    startup_id: str,
    question: str,
    top_k: int | None = None,
) -> dict:
    """
    Returns:
      {
        "answer":     str,
        "evidence":   list[dict],   # retrieved chunks
        "sources":    list[str],    # unique source filenames
        "metrics":    list[dict],   # structured financial metrics used
        "startup_id": str,
      }
    """
    retriever = Retriever(startup_id)
    retrieval = retriever.retrieve(question, top_k=top_k)

    context = retrieval["context"]
    chunks = retrieval["chunks"]
    metrics = retrieval["metrics"]

    if settings.llm_available:
        answer = _call_openai(question, context, metrics)
    else:
        answer = _fallback_answer(question, context, metrics)

    sources = list({c["source"] for c in chunks if c.get("source")})

    return {
        "answer": answer,
        "evidence": [
            {
                "text": c.get("text", ""),
                "source": c.get("source", ""),
                "score": round(c.get("score", 0.0), 4),
                "doc_type": c.get("doc_type", ""),
            }
            for c in chunks
        ],
        "sources": sources,
        "metrics": metrics,
        "startup_id": startup_id,
    }


def _call_openai(question: str, context: str, metrics: list[dict]) -> str:
    from openai import OpenAI
    from openai import RateLimitError, AuthenticationError, APIError

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TEMPLATE.format(context=context, question=question)},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        return _fallback_answer(question, context, metrics, note="OpenAI quota exceeded - showing data-driven answer.")
    except AuthenticationError:
        return _fallback_answer(question, context, metrics, note="OpenAI API key is invalid - showing data-driven answer.")
    except APIError as exc:
        return _fallback_answer(question, context, metrics, note=f"OpenAI API error ({exc.status_code}) - showing data-driven answer.")


def _fallback_answer(
    question: str,
    context: str,
    metrics: list[dict],
    note: str = "",
) -> str:
    """Rule-based answer used when no LLM is available or OpenAI fails."""
    q_lower = question.lower()
    lines: list[str] = []

    if note:
        lines.append(f"[{note}]")
        lines.append("")

    # Always show ALL metrics, highlighting ones relevant to the question
    relevant_metrics = []
    other_metrics = []
    for m in metrics:
        name = m["metric_name"]
        keywords = name.replace("_", " ").split()
        val = m.get("value_text") or (str(m["value"]) if m.get("value") is not None else None)
        if not val:
            continue
        display = name.replace("_", " ").title()
        period = f" ({m['period']})" if m.get("period") else ""
        entry = f"  • {display}: {val}{period}"
        if any(kw in q_lower for kw in keywords):
            relevant_metrics.append(entry)
        else:
            other_metrics.append(entry)

    if relevant_metrics:
        lines.append("Direct answer from financial model:")
        lines.extend(relevant_metrics)

    if other_metrics:
        lines.append("\nOther available metrics:")
        lines.extend(other_metrics)

    # Append relevant document excerpts
    if context:
        doc_parts = [p.strip() for p in context.split("\n\n") if p.strip() and not p.startswith("[Structured")]
        if doc_parts:
            lines.append("\nRelevant document excerpts:")
            for part in doc_parts[:2]:
                lines.append(part)

    if not lines or (len(lines) == 1 and note):
        lines.append(
            "No matching data found. Please ensure the relevant documents have been ingested."
        )

    return "\n".join(lines)

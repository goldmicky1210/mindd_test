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
        answer = _call_openai(question, context)
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


def _call_openai(question: str, context: str) -> str:
    from openai import OpenAI

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


def _fallback_answer(question: str, context: str, metrics: list[dict]) -> str:
    """Rule-based answer when no LLM is available."""
    q_lower = question.lower()

    # Try to match question against metric names
    metric_answers = []
    for m in metrics:
        name = m["metric_name"]
        keywords = name.replace("_", " ").split()
        if any(kw in q_lower for kw in keywords):
            val = m.get("value_text") or (str(m["value"]) if m.get("value") is not None else None)
            if val:
                display = m.get("metric_name", "").replace("_", " ").title()
                period = f" ({m['period']})" if m.get("period") else ""
                metric_answers.append(f"{display}: {val}{period}")

    if metric_answers:
        lines = ["Based on the financial model data:"] + [f"  • {a}" for a in metric_answers]
        if context:
            lines.append("\nAdditional context from documents is available in the evidence field.")
        return "\n".join(lines)

    if context:
        # Return the first relevant paragraph from context
        paragraphs = [p.strip() for p in context.split("\n\n") if p.strip()]
        if paragraphs:
            return (
                f"Based on the available documents:\n\n{paragraphs[0]}\n\n"
                "(Note: Set OPENAI_API_KEY for AI-generated answers.)"
            )

    return (
        "Insufficient data to answer this question from the ingested documents. "
        "Please ensure the relevant documents have been ingested and set OPENAI_API_KEY "
        "for full AI-powered reasoning."
    )

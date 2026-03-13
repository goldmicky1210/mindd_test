"""
Cross-startup comparison reasoning.
Retrieves evidence from multiple startups and generates a comparative answer.
"""

from __future__ import annotations

from app.retrieval.retriever import Retriever
from app.storage.metadata_store import metadata_store
from config import settings

COMPARE_SYSTEM = """You are a senior investment analyst comparing multiple startups for a VC fund.
You have access to each company's financial data, pitch decks, and investor updates.
Provide a clear, balanced comparison focusing on the specific question asked.
Use concrete metrics and cite evidence from each company.
Conclude with an objective assessment."""

COMPARE_USER = """You are comparing the following startups: {startup_names}.

{combined_context}

Question: {question}

Provide a comparative analysis with:
1. Key metrics for each startup relevant to the question
2. Side-by-side comparison
3. Your assessment of which company has stronger performance on this dimension, with reasoning"""


def compare_startups(
    startup_ids: list[str],
    question: str,
    top_k: int | None = None,
) -> dict:
    """
    Returns:
      {
        "answer":           str,
        "startup_evidence": dict[startup_id -> {chunks, metrics}],
        "sources":          dict[startup_id -> list[str]],
      }
    """
    if len(startup_ids) < 2:
        raise ValueError("At least two startup IDs are required for comparison.")

    startup_evidence: dict[str, dict] = {}
    startup_names: dict[str, str] = {}

    for sid in startup_ids:
        info = metadata_store.get_startup(sid)
        startup_names[sid] = info.name if info else sid

        retriever = Retriever(sid)
        retrieval = retriever.retrieve(question, top_k=top_k)
        startup_evidence[sid] = {
            "chunks": retrieval["chunks"],
            "metrics": retrieval["metrics"],
            "context": retrieval["context"],
        }

    combined_context = _build_combined_context(startup_ids, startup_names, startup_evidence)
    names_str = " vs ".join(startup_names[sid] for sid in startup_ids)

    if settings.llm_available:
        answer = _call_openai_compare(names_str, combined_context, question, startup_ids, startup_names, startup_evidence)
    else:
        answer = _fallback_compare(startup_ids, startup_names, startup_evidence, question)

    sources = {
        sid: list({c["source"] for c in startup_evidence[sid]["chunks"] if c.get("source")})
        for sid in startup_ids
    }

    return {
        "answer": answer,
        "startup_evidence": {
            sid: {
                "metrics": startup_evidence[sid]["metrics"],
                "top_chunks": [
                    {
                        "text": c.get("text", ""),
                        "source": c.get("source", ""),
                        "score": round(c.get("score", 0.0), 4),
                    }
                    for c in startup_evidence[sid]["chunks"][:3]
                ],
            }
            for sid in startup_ids
        },
        "sources": sources,
    }


def _build_combined_context(
    startup_ids: list[str],
    startup_names: dict[str, str],
    evidence: dict[str, dict],
) -> str:
    parts = []
    for sid in startup_ids:
        name = startup_names[sid]
        ctx = evidence[sid]["context"]
        parts.append(f"=== {name} (ID: {sid}) ===\n{ctx}")
    return "\n\n".join(parts)


def _call_openai_compare(
    names_str: str,
    combined_context: str,
    question: str,
    startup_ids: list[str],
    startup_names: dict[str, str],
    startup_evidence: dict[str, dict],
) -> str:
    from openai import OpenAI
    from openai import RateLimitError, AuthenticationError, PermissionDeniedError, APIError

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": COMPARE_SYSTEM},
                {
                    "role": "user",
                    "content": COMPARE_USER.format(
                        startup_names=names_str,
                        combined_context=combined_context,
                        question=question,
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except RateLimitError:
        note = "OpenAI quota exceeded (HTTP 429) - add billing at platform.openai.com/account/billing"
        return _fallback_compare(startup_ids, startup_names, startup_evidence, question, note=note)
    except AuthenticationError:
        note = "OpenAI authentication failed (HTTP 401) - check OPENAI_API_KEY in .env"
        return _fallback_compare(startup_ids, startup_names, startup_evidence, question, note=note)
    except PermissionDeniedError:
        note = (
            "OpenAI access denied (HTTP 403) - try changing OPENAI_CHAT_MODEL=gpt-3.5-turbo in .env, "
            "or check project permissions at platform.openai.com/settings"
        )
        return _fallback_compare(startup_ids, startup_names, startup_evidence, question, note=note)
    except APIError as exc:
        note = f"OpenAI API error (HTTP {exc.status_code})"
        return _fallback_compare(startup_ids, startup_names, startup_evidence, question, note=note)


def _fallback_compare(
    startup_ids: list[str],
    startup_names: dict[str, str],
    evidence: dict[str, dict],
    question: str,
    note: str = "",
) -> str:
    lines: list[str] = []
    if note:
        lines.append(f"[{note} - showing data-driven comparison]")
        lines.append("")
    lines += [f"Comparison: {' vs '.join(startup_names.values())}", ""]
    q_lower = question.lower()

    for sid in startup_ids:
        name = startup_names[sid]
        lines.append(f"--- {name} ---")
        metrics = evidence[sid]["metrics"]
        matched = []
        for m in metrics:
            keywords = m["metric_name"].replace("_", " ").split()
            if any(kw in q_lower for kw in keywords) or not q_lower:
                val = m.get("value_text") or (str(m["value"]) if m.get("value") is not None else None)
                if val:
                    display = m["metric_name"].replace("_", " ").title()
                    matched.append(f"  {display}: {val}")
        if matched:
            lines.extend(matched)
        else:
            # Show all available metrics
            for m in metrics[:5]:
                val = m.get("value_text") or (str(m["value"]) if m.get("value") is not None else "N/A")
                display = m["metric_name"].replace("_", " ").title()
                lines.append(f"  {display}: {val}")
        lines.append("")

    if not note:
        lines.append("(Set a valid OPENAI_API_KEY with available credits for AI-powered analysis.)")
    return "\n".join(lines)

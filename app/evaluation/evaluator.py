"""
Evaluation framework.

For each test question:
  1. Run retrieval + QA
  2. Check retrieval relevance  (expected_source present in retrieved sources)
  3. Check grounding score      (fraction of answer words found in context)
  4. Flag potential hallucination (answer references numbers/facts not in context)
"""

from __future__ import annotations

import re

from app.evaluation.test_questions import QUESTION_SETS
from app.reasoning.qa_chain import answer_question
from app.storage.metadata_store import metadata_store


def run_evaluation(startup_id: str, question_set: str = "default") -> dict:
    if not metadata_store.get_startup(startup_id):
        raise FileNotFoundError(f"Startup '{startup_id}' not found. Ingest documents first.")

    questions = QUESTION_SETS.get(question_set)
    if not questions:
        raise ValueError(f"Unknown question set: '{question_set}'. Available: {list(QUESTION_SETS)}")

    results = []

    for q_spec in questions:
        question = q_spec["question"]
        expected_keywords = [k.lower() for k in q_spec.get("expected_keywords", [])]
        expected_source = q_spec.get("expected_source", "any")

        qa_result = answer_question(startup_id=startup_id, question=question)
        answer = qa_result["answer"]
        chunks = qa_result["evidence"]
        sources = qa_result["sources"]
        metrics = qa_result["metrics"]

        # --- Retrieval relevance ---
        if expected_source == "any":
            retrieval_relevant = bool(chunks or metrics)
        else:
            retrieved_types = {c.get("doc_type", "") for c in chunks}
            retrieval_relevant = expected_source in retrieved_types or bool(metrics)

        # --- Grounding score ---
        context_text = " ".join(c.get("text", "") for c in chunks).lower()
        # Add metric values to context
        for m in metrics:
            if m.get("value_text"):
                context_text += " " + str(m["value_text"]).lower()
            if m.get("value"):
                context_text += " " + str(m["value"]).lower()

        answer_words = set(re.findall(r"\b\w+\b", answer.lower()))
        if answer_words:
            context_words = set(re.findall(r"\b\w+\b", context_text))
            # Ignore stopwords
            stopwords = {
                "the", "a", "an", "is", "are", "was", "were", "of", "in", "to",
                "and", "or", "for", "with", "that", "this", "it", "its", "be",
                "on", "at", "by", "from", "as", "has", "have", "had", "not",
                "no", "i", "we", "our", "their", "your", "based", "according",
            }
            content_words = answer_words - stopwords
            if content_words:
                grounding_score = len(content_words & context_words) / len(content_words)
            else:
                grounding_score = 1.0
        else:
            grounding_score = 0.0

        # --- Hallucination detection (heuristic) ---
        # Flag if numbers in the answer are not present in context
        answer_numbers = set(re.findall(r"\b\d+\.?\d*\b", answer))
        context_numbers = set(re.findall(r"\b\d+\.?\d*\b", context_text))
        hallucination_flag = bool(answer_numbers - context_numbers) and grounding_score < 0.4

        # --- Keyword check (answer quality) ---
        has_evidence = bool(chunks) or any(
            kw in answer.lower() for kw in expected_keywords
        )

        results.append(
            {
                "question": question,
                "answer": answer,
                "retrieved_sources": sources,
                "metrics_used": [m["metric_name"] for m in metrics],
                "has_evidence": has_evidence,
                "grounding_score": round(grounding_score, 3),
                "hallucination_flag": hallucination_flag,
                "retrieval_relevant": retrieval_relevant,
            }
        )

    total = len(results)
    avg_grounding = sum(r["grounding_score"] for r in results) / total if total else 0.0
    relevance_rate = sum(1 for r in results if r["retrieval_relevant"]) / total if total else 0.0
    hallucination_rate = sum(1 for r in results if r["hallucination_flag"]) / total if total else 0.0

    return {
        "startup_id": startup_id,
        "total_questions": total,
        "avg_grounding_score": round(avg_grounding, 3),
        "retrieval_relevance_rate": round(relevance_rate, 3),
        "hallucination_rate": round(hallucination_rate, 3),
        "results": results,
    }

"""
End-to-end evaluation runner.

1. Generates sample data (if not already present)
2. Ingests both startups
3. Runs evaluation suite on each
4. Prints and saves results to evaluation/results.json

Run:
    python scripts/run_evaluation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.evaluator import run_evaluation
from app.ingestion.pipeline import ingest_startup


def main():
    results_dir = Path("evaluation")
    results_dir.mkdir(exist_ok=True)

    startups = [
        {"id": "alpha", "name": "AlphaFlow", "description": "B2B SaaS workflow automation"},
        {"id": "beta",  "name": "BetaMart",  "description": "E-commerce artisan marketplace"},
    ]

    # ---- Ensure sample data exists ----
    for s in startups:
        data_path = Path("data/startups") / s["id"]
        if not data_path.exists() or not list(data_path.iterdir()):
            print(f"Sample data missing for {s['name']}. Generating...")
            from scripts.generate_sample_data import main as gen_main
            gen_main()
            break

    # ---- Ingest ----
    print("\n=== Ingesting Startups ===")
    for s in startups:
        print(f"\nIngesting {s['name']} ({s['id']})...")
        try:
            summary = ingest_startup(s["id"], s["name"], description=s["description"])
            print(f"  Chunks: {summary['total_chunks']}, Metrics: {summary['metrics_extracted']}")
            for doc in summary["documents_ingested"]:
                print(f"    {doc['file']}: {doc['chunks']} chunks")
        except Exception as exc:
            print(f"  ERROR: {exc}")

    # ---- Evaluate ----
    all_results: dict[str, dict] = {}
    print("\n=== Running Evaluation ===")

    for s in startups:
        print(f"\nEvaluating {s['name']}...")
        try:
            result = run_evaluation(startup_id=s["id"])
            all_results[s["id"]] = result

            print(f"  Questions:          {result['total_questions']}")
            print(f"  Avg Grounding:      {result['avg_grounding_score']:.1%}")
            print(f"  Retrieval Relevant: {result['retrieval_relevance_rate']:.1%}")
            print(f"  Hallucination Rate: {result['hallucination_rate']:.1%}")

            print("\n  Question-by-Question:")
            for r in result["results"]:
                flag = "OK" if r["retrieval_relevant"] else "XX"
                hall = " [HALLUCINATION?]" if r["hallucination_flag"] else ""
                print(f"  [{flag}] {r['question'][:60]}...")
                print(f"       Grounding: {r['grounding_score']:.2f} | Sources: {r['retrieved_sources']}{hall}")

        except Exception as exc:
            print(f"  ERROR: {exc}")

    # ---- Save results ----
    out_path = results_dir / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()

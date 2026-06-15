from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from medintel.config import get_settings
from medintel.r2_storage import LocalLake

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUESTION_BANK = ROOT / "pipeline" / "evals" / "local_representative_questions.jsonl"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _contains_all(text: str, terms: list[str]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term.lower() in lower]


def _score(question: dict[str, Any], response: dict[str, Any], elapsed_ms: int) -> dict[str, Any]:
    citations = response.get("citations") or []
    contexts = response.get("retrieved_context") or []
    citation_sources = {str(citation.get("source_type")) for citation in citations}
    citation_doc_ids = {str(citation.get("doc_id")) for citation in citations}
    answer = str(response.get("answer") or "")
    context_text = " ".join(str(context.get("text_chunk") or "") for context in contexts)

    expected_sources = set(question.get("expected_sources") or [])
    expected_doc_ids = set(question.get("expected_doc_ids") or [])
    expected_terms = list(question.get("expected_terms") or [])
    answer_terms = _contains_all(answer, expected_terms)
    context_terms = _contains_all(context_text, expected_terms)
    source_hits = expected_sources.intersection(citation_sources)
    doc_hits = expected_doc_ids.intersection(citation_doc_ids)

    source_recall = len(source_hits) / len(expected_sources) if expected_sources else 1.0
    doc_hit = bool(doc_hits) if expected_doc_ids else True
    answer_term_recall = len(answer_terms) / len(expected_terms) if expected_terms else 1.0
    context_term_recall = len(context_terms) / len(expected_terms) if expected_terms else 1.0
    passed = bool(citations) and source_recall >= 1.0 and doc_hit and (answer_term_recall >= 0.34 or context_term_recall >= 0.67)

    return {
        "id": question["id"],
        "question": question["question"],
        "passed": passed,
        "source_recall": round(source_recall, 3),
        "doc_hit": doc_hit,
        "answer_term_recall": round(answer_term_recall, 3),
        "context_term_recall": round(context_term_recall, 3),
        "expected_sources": sorted(expected_sources),
        "citation_sources": sorted(citation_sources),
        "expected_doc_ids": sorted(expected_doc_ids),
        "citation_doc_ids": sorted(citation_doc_ids),
        "expected_terms": expected_terms,
        "answer_terms_found": answer_terms,
        "context_terms_found": context_terms,
        "answer_provider": response.get("answer_provider"),
        "answer_model": response.get("answer_model"),
        "answer_warning": response.get("answer_warning"),
        "latency_ms": response.get("latency_ms", elapsed_ms),
        "wall_latency_ms": elapsed_ms,
        "answer": answer,
        "citations": citations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="local-representative")
    parser.add_argument("--question-bank", default=str(DEFAULT_QUESTION_BANK))
    parser.add_argument("--api-url", default="http://127.0.0.1:4000")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--min-pass-rate", type=float, default=0.85)
    parser.add_argument("--min-doc-hit-rate", type=float, default=0.75)
    parser.add_argument("--min-source-recall", type=float, default=0.9)
    parser.add_argument("--enforce-thresholds", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    questions = _read_jsonl(Path(args.question_bank))
    if args.limit is not None:
        questions = questions[: args.limit]

    if args.dry_run:
        print(json.dumps({"question_count": len(questions), "questions": questions}, indent=2))
        return

    lake = LocalLake(get_settings())
    out_dir = lake.path("evals", args.run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_path = out_dir / f"rag_eval_{stamp}.jsonl"
    summary_path = out_dir / f"rag_eval_{stamp}_summary.json"

    results: list[dict[str, Any]] = []
    endpoint = args.api_url.rstrip("/") + "/api/rag/query"
    with results_path.open("w", encoding="utf-8") as handle:
        for index, question in enumerate(questions, start=1):
            started = time.time()
            try:
                response = _post_json(
                    endpoint,
                    {
                        "question": question["question"],
                        "filters": {"sources": question.get("sources") or []},
                    },
                    args.timeout,
                )
                elapsed_ms = int((time.time() - started) * 1000)
                result = _score(question, response, elapsed_ms)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                elapsed_ms = int((time.time() - started) * 1000)
                result = {
                    "id": question["id"],
                    "question": question["question"],
                    "passed": False,
                    "error": str(exc),
                    "wall_latency_ms": elapsed_ms,
                }
            results.append(result)
            handle.write(json.dumps(result, sort_keys=True) + "\n")
            print(json.dumps({
                "index": index,
                "id": result["id"],
                "passed": result["passed"],
                "latency_ms": result.get("latency_ms", result.get("wall_latency_ms")),
            }))

    passed = sum(1 for result in results if result.get("passed"))
    doc_hit_results = [result for result in results if "doc_hit" in result]
    doc_hit_rate = sum(1 for result in doc_hit_results if result.get("doc_hit")) / len(doc_hit_results) if doc_hit_results else 1.0
    source_recall_values = [float(result.get("source_recall", 0)) for result in results if "source_recall" in result]
    avg_source_recall = sum(source_recall_values) / len(source_recall_values) if source_recall_values else 1.0
    pass_rate = passed / len(results) if results else 0
    thresholds = {
        "min_pass_rate": args.min_pass_rate,
        "min_doc_hit_rate": args.min_doc_hit_rate,
        "min_source_recall": args.min_source_recall,
        "enforced": args.enforce_thresholds,
    }
    threshold_status = {
        "pass_rate_ok": pass_rate >= args.min_pass_rate,
        "doc_hit_rate_ok": doc_hit_rate >= args.min_doc_hit_rate,
        "source_recall_ok": avg_source_recall >= args.min_source_recall,
    }
    summary = {
        "run_id": args.run_id,
        "question_bank": str(args.question_bank),
        "api_url": args.api_url,
        "questions": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(pass_rate, 3) if results else 0,
        "doc_hit_rate": round(doc_hit_rate, 3),
        "avg_source_recall": round(avg_source_recall, 3),
        "thresholds": thresholds,
        "threshold_status": threshold_status,
        "avg_latency_ms": round(sum(int(result.get("latency_ms") or result.get("wall_latency_ms") or 0) for result in results) / len(results), 1) if results else 0,
        "results_path": str(results_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest_summary = out_dir / "latest_summary.json"
    latest_results = out_dir / "latest_results.jsonl"
    latest_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    latest_results.write_text(results_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if args.enforce_thresholds and not all(threshold_status.values()):
        sys.exit(2)


if __name__ == "__main__":
    main()

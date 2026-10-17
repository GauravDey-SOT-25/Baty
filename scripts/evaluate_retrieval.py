#!/usr/bin/env python3
"""Offline retrieval and evidence-abstention evaluation; never performs I/O to URLs."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def metrics_for(rows: list[dict]) -> dict:
    positive = [row for row in rows if row["expected_record_ids"]]
    tp = sum(len(set(row["expected_record_ids"]) & set(row["retrieved_record_ids"])) for row in positive)
    fp = sum(len(set(row["retrieved_record_ids"]) - set(row["expected_record_ids"])) for row in positive)
    fn = sum(len(set(row["expected_record_ids"]) - set(row["retrieved_record_ids"])) for row in positive)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    negative = [row for row in rows if not row["expected_record_ids"]]
    correct_abstentions = sum(not row["retrieved_record_ids"] for row in negative)
    source_rows = [row for row in positive if row["expected_record_ids"]]
    expected_lookup = {ref["id"]: ref for row in source_rows for ref in row["factual_sources"]}
    citations = [
        returned for row in positive for returned in row["retrieved_records"]
        if returned["id"] in expected_lookup
    ]
    correct_attribution = sum(
        returned.get("source_url") == expected_lookup[returned["id"]].get("source_url")
        for returned in citations
    )
    abstention_cases = [row for row in rows if row["category"] == "missing_evidence_abstention"]
    correct_assistant_abstentions = sum(row.get("assistant_abstained") is True for row in abstention_cases)
    return {
        "n": len(rows), "positive_n": len(positive), "negative_n": len(negative),
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
        "negative_query_correct_abstention_rate": correct_abstentions / len(negative) if negative else None,
        "negative_query_false_match_rate": 1 - correct_abstentions / len(negative) if negative else None,
        "expected_source_url_attribution_accuracy": correct_attribution / len(citations) if citations else None,
        "citation_checks": len(citations),
        "assistant_missing_evidence_abstention_accuracy": (
            correct_assistant_abstentions / len(abstention_cases) if abstention_cases else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data/evaluation/cyber_retrieval_v1.jsonl")
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/processed/incidents.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/cyber-retrieval-v1.json")
    args = parser.parse_args()
    corpus_bytes = args.corpus.read_bytes()
    source_bytes = args.data.read_bytes()
    examples = [json.loads(line) for line in source_bytes.decode().splitlines() if line.strip()]
    if len({item["id"] for item in examples}) != len(examples):
        raise SystemExit("Evaluation IDs must be unique")

    from src.incident_search import search as retrieval
    from src.assistant.service import answer as answer_application
    retrieval.CORPUS = args.corpus
    retrieval._records.cache_clear()
    rows = []
    for item in examples:
        found = retrieval.search_incidents(item["query"], limit=5)["incidents"]
        row = {
            "id": item["id"],
            "category": item["category"],
            "query": item["query"],
            "expected_record_ids": item["expected_record_ids"],
            "should_abstain": item["should_abstain"],
            "retrieved_record_ids": [str(record["id"]) for record in found],
            "retrieved_records": [{
                "id": record.get("id"),
                "title": record.get("title"),
                "source": record.get("source"),
                "source_url": record.get("source_url"),
                "published_at": record.get("published_at"),
                "relevance_score": record.get("relevance_score"),
            } for record in found],
            "factual_sources": item["factual_sources"],
            "hit": bool(set(item["expected_record_ids"]) & {str(r["id"]) for r in found}),
        }
        if item["category"] == "missing_evidence_abstention":
            app_answer = answer_application(item["query"], include_local_records=True)
            row["assistant_answer_basis"] = app_answer.get("answer_basis")
            row["assistant_abstained"] = (
                app_answer.get("answer_basis") == "abstention_missing_evidence"
                and not app_answer.get("sources")
            )
        rows.append(row)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    summary = {category: metrics_for(group) for category, group in sorted(grouped.items())}
    summary["all_retrieval_cases"] = metrics_for(rows)
    outputs = {
        "evaluation_id": "cyber_retrieval_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        "dataset_size": len(rows),
        "model_invoked": False,
        "network_access": "None; all URLs are metadata and were not opened/resolved.",
        "metrics": summary,
        "results": rows,
        "limitations": [
            "Project-authored retrieval queries and labels are diagnostic; not independently reviewed.",
            "The benchmark is small, focuses on CISA snapshots, and does not estimate real-world query distribution.",
            "Expected source IDs judge known positive targets. Extra retrieved records are counted as false positives even if a human might consider them useful context.",
            "No free-form model answer correctness is inferred from retrieval success.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": summary, "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

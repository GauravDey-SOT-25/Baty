#!/usr/bin/env python3
"""Offline evaluation over a small project-authored cybersecurity suite.

URLs are analyzed as text only and never resolved, opened, or fetched. QA
outputs use the local base model and require manual rubric review; this script
never scores its own free-form generations as correct.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def binary_metrics(rows: list[dict]) -> dict:
    positive = {"phishing", "suspicious"}
    tp = sum(r["label"] in positive and r["prediction"] == "phishing" for r in rows)
    tn = sum(r["label"] == "benign" and r["prediction"] == "benign" for r in rows)
    fp = sum(r["label"] == "benign" and r["prediction"] == "phishing" for r in rows)
    fn = sum(r["label"] in positive and r["prediction"] == "benign" for r in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "n": len(rows), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall,
        "f1": (2 * precision * recall / (precision + recall)) if precision + recall else 0.0,
        "false_positive_rate": fp / (fp + tn) if fp + tn else 0.0,
        "accuracy": (tp + tn) / len(rows) if rows else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data/evaluation/cyber_eval_v1.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/cyber-eval-v1.json")
    parser.add_argument("--max-tokens", type=int, default=256)
    args = parser.parse_args()
    source_bytes = args.data.read_bytes()
    examples = [json.loads(line) for line in source_bytes.decode("utf-8").splitlines() if line.strip()]
    if len({item["id"] for item in examples}) != len(examples):
        raise SystemExit("Evaluation IDs must be unique")

    from src.message_analysis.analyzer import analyze_message
    from src.url_analysis.analyzer import analyze_url
    from src.assistant.local_model import MODEL_DIR, answer_locally
    from src.assistant.service import answer as answer_application

    outputs: dict[str, list[dict]] = {"message": [], "url": [], "qa": []}
    for item in examples:
        row = {"id": item["id"], "label": item["label"], "provenance": item["provenance"]}
        if item["task"] == "message":
            details = analyze_message(item["text"])
            row.update({"prediction": "phishing" if details["risk"] in {"moderate", "high"} else "benign",
                        "risk": details["risk"], "indicators": details["evidence"]})
            outputs["message"].append(row)
        elif item["task"] == "url":
            try:
                details = analyze_url(item["url"])
                prediction = "phishing" if details["risk"] == "moderate" or details.get("model_signal") == "phishing" else "benign"
                row.update({"prediction": prediction, "risk": details["risk"],
                            "model_signal": details.get("model_signal"), "indicators": details.get("indicators", [])})
            except ValueError as exc:
                # A rejected URL is a positive safety finding in this test set.
                row.update({"prediction": "phishing", "risk": "rejected", "indicators": [],
                            "note": f"Locally rejected: {exc}"})
            outputs["url"].append(row)
        elif item["task"] == "qa":
            answer = answer_locally(item["question"], [], args.max_tokens, use_adapter=False)
            if answer is None:
                raise SystemExit("Local base model unavailable; QA evaluation incomplete")
            app_response = answer_application(item["question"])
            row.update({"question": item["question"], "rubric": item["rubric"],
                        "base_model_answer": answer, "application_answer": app_response["answer"],
                        "application_sources": app_response.get("sources", []),
                        "application_answer_basis": app_response.get("answer_basis", "not_reported"),
                        "manual_review": None})
            outputs["qa"].append(row)
        else:
            raise SystemExit(f"Unsupported task type in {item['id']}")

    outputs["metrics"] = {
        "message_rule_baseline": binary_metrics(outputs["message"]),
        "url_classifier_and_static_guard": binary_metrics(outputs["url"]),
        "qa": {"n": len(outputs["qa"]), "correct": None,
               "note": "Free-form answers require manual scoring against each stored rubric."},
    }
    outputs["metadata"] = {
        "evaluation_id": "cyber_eval_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "dataset_path": str(args.data),
        "dataset_size": len(examples),
        "dataset_license": "Project-authored synthetic examples; public URL strings are included for passive text-only analysis, no web content copied.",
        "split": "Evaluation-only fixed set; never used for training or validation.",
        "model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        "model_path": str(MODEL_DIR),
        "model_mode": "base-model output explicitly disables adapters; app output uses existing local safety/retrieval wrapper",
        "inference_backend": {name: importlib.metadata.version(name) for name in ("mlx", "mlx-lm")},
        "network_access": "None; URLs are parsed only and never resolved or fetched.",
        "limitations": [
            "Small synthetic evaluation set is not representative of real phishing prevalence or threat diversity.",
            "Project-authored examples may align with the rules they test; metrics are diagnostic only.",
            "URL predictions use an existing model trained on UCI PhiUSIIL plus static URL checks; domain-shift and calibration remain concerns.",
            "QA correctness is not automatically graded; inspect output against each rubric and record manual_review as pass/fail.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for key, value in outputs["metrics"].items():
        print(f"{key}: {json.dumps(value, sort_keys=True)}")
    print(f"Saved offline evaluation to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

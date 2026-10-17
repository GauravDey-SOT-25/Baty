#!/usr/bin/env python3
"""Compare base and Trendyol-adapted local generations on the fixed QA prompts."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def normalize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def overlap(left: str, right: str) -> float:
    a, b = normalize(left), normalize(right)
    return len(a & b) / len(a | b) if a | b else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "data/evaluation/cyber_eval_v1.jsonl")
    parser.add_argument("--train", type=Path, default=ROOT / "data/processed/trendyol-m5/train.jsonl")
    parser.add_argument("--adapter", type=Path, default=ROOT / "adapters/trendyol-m5-experiment")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/trendyol-m5-qa-comparison.json")
    parser.add_argument("--max-tokens", type=int, default=192)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"Refusing to overwrite {args.output}")
    source = args.data.read_bytes()
    rows = [json.loads(line) for line in source.decode("utf-8").splitlines() if line.strip()]
    questions = [r for r in rows if r.get("task") == "qa"]
    training_rows = [json.loads(line) for line in args.train.read_text(encoding="utf-8").splitlines() if line.strip()]
    prompts = [next(m["content"] for m in r["messages"] if m["role"] == "user") for r in training_rows]
    for row in questions:
        nearest = max((overlap(row["question"], prompt) for prompt in prompts), default=0.0)
        if nearest >= 0.75:
            raise SystemExit(f"Near-duplicate evaluation prompt {row['id']} overlaps training (Jaccard={nearest:.3f})")
        row["nearest_train_prompt_token_jaccard"] = round(nearest, 4)

    from src.assistant import local_model
    local_model.ADAPTER_DIR = args.adapter
    out = []
    for row in questions:
        base = local_model.answer_locally(row["question"], [], args.max_tokens, use_adapter=False)
        tuned = local_model.answer_locally(row["question"], [], args.max_tokens, use_adapter=True)
        if base is None or tuned is None:
            raise SystemExit("Base model or adapter failed to load; comparison incomplete")
        out.append({
            "id": row["id"], "question": row["question"], "rubric": row["rubric"],
            "nearest_train_prompt_token_jaccard": row["nearest_train_prompt_token_jaccard"],
            "base_model_answer": base, "adapter_answer": tuned,
            "human_review": None
        })
    report = {
        "evaluation_id": "cyber_eval_v1_qa_base_vs_trendyol_adapter",
        "dataset_sha256": hashlib.sha256(source).hexdigest(),
        "adapter_path": str(args.adapter),
        "max_tokens": args.max_tokens,
        "review_note": "Generations require rubric review. This small project-authored set is diagnostic, not an independent benchmark.",
        "scores": None,
        "qa": out
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(out)} paired generations to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

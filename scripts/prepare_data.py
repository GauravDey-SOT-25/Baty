#!/usr/bin/env python3
"""Normalize instruction JSONL and create deterministic duplicate-safe splits."""
import argparse
import hashlib
import json
import random
import re
from pathlib import Path

SEED = 17


def normalize(row):
    if not isinstance(row, dict):
        return None
    raw_user = str(row.get("user", row.get("instruction", "")))
    raw_assistant = str(row.get("assistant", row.get("output", row.get("response", ""))))
    raw_system = str(row.get("system", "You are a careful, defensive cybersecurity assistant."))
    # The reviewed source serializes many intended line breaks as the two characters \\n+    # throughout ordinary prose. Keep the untouched source file separately and
    # record this formatting-only normalization in the prepared example.
    escaped_newlines = sum(value.count("\\n") for value in (raw_user, raw_assistant, raw_system))
    user = raw_user.replace("\\n", "\n").strip()
    assistant = raw_assistant.replace("\\n", "\n").strip()
    system = raw_system.replace("\\n", "\n").strip()
    if not user or not assistant:
        return None
    provenance = row.get("_provenance", {})
    return {"messages": [{"role": "system", "content": system}, {"role": "user", "content": user},
                         {"role": "assistant", "content": assistant}],
            "source_id": row.get("id", row.get("source_id", provenance.get("row_idx"))),
            "source": row.get("source", provenance.get("dataset_id", "unknown")),
            "source_revision": provenance.get("revision"),
            "license": row.get("license", provenance.get("license")),
            "normalization": {"literal_backslash_n_to_newline": escaped_newlines}}


def fingerprint(record):
    user = record["messages"][1]["content"].casefold()
    assistant = record["messages"][2]["content"].casefold()
    normalized = re.sub(r"\s+", " ", user + "\n" + assistant).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def prepare(rows, seed=SEED):
    prompts = {}
    conflicting_prompts = set()
    for row in rows:
        item = normalize(row)
        if item is None:
            continue
        normalized_user = re.sub(r"\s+", " ", item["messages"][1]["content"].casefold()).strip()
        prompt_key = hashlib.sha256(normalized_user.encode()).hexdigest()
        response_key = hashlib.sha256(re.sub(r"\s+", " ", item["messages"][2]["content"].casefold()).strip().encode()).hexdigest()
        if prompt_key not in prompts:
            prompts[prompt_key] = (response_key, item)
        elif prompts[prompt_key][0] != response_key:
            conflicting_prompts.add(prompt_key)
    deduped = [(key, item) for key, (response, item) in prompts.items() if key not in conflicting_prompts]
    # Deterministic hash-based split keeps exact duplicates grouped (deduplication removes them first).
    random.Random(seed).shuffle(deduped)
    n = len(deduped)
    n_test = max(1, round(n * .1)) if n >= 10 else 0
    n_valid = max(1, round(n * .1)) if n >= 10 else 0
    chunks = {"train": deduped[:n - n_valid - n_test] if n >= 10 else deduped,
              "valid": deduped[n - n_valid - n_test:n - n_test] if n >= 10 else [],
              "test": deduped[n - n_test:] if n >= 10 else []}
    return {name: [row for _, row in values] for name, values in chunks.items()}


def read_jsonl(path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--limit", type=int, default=1000)
    a = p.parse_args()
    splits = prepare(list(read_jsonl(a.input))[:a.limit], a.seed)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, rows in splits.items():
        target = a.output_dir / f"{name}.jsonl"
        target.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        stats[name] = len(rows)
    (a.output_dir / "split-statistics.json").write_text(json.dumps({"seed": a.seed, "counts": stats}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

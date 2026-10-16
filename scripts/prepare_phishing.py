#!/usr/bin/env python3
"""Deduplicate and deterministically split labeled email/URL records."""
import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

LABEL_NAMES = {0: "legitimate_email", 1: "phishing_email", 2: "legitimate_url", 3: "phishing_url",
               "0": "legitimate_email", "1": "phishing_email", "2": "legitimate_url", "3": "phishing_url"}


def prepare(rows, seed=17):
    unique, seen, label_sets = [], {}, {}
    for idx, row in enumerate(rows):
        content = str(row.get("content", "")).strip()
        label = row.get("labels", row.get("label"))
        if not content or label is None:
            continue
        label = LABEL_NAMES.get(label, LABEL_NAMES.get(str(label), str(label)))
        key = hashlib.sha256(content.casefold().encode()).hexdigest()
        if key in seen:
            if seen[key]["label"] != str(label):
                label_sets[key].add(str(label))
            continue
        seen[key] = {"content": content, "label": str(label), "source_id": row.get("id", idx),
                     "modality": "url" if "_url" in str(label) else "email",
                     "source": row.get("_provenance", {}).get("dataset_id", "unknown"), "license": row.get("license")}
        label_sets[key] = {str(label)}
    # Conflicting exact-text labels are ambiguous; exclude rather than leaking or deciding one is correct.
    unique = []
    for key, value in seen.items():
        if len(label_sets[key]) == 1:
            unique.append(value)
    by_label = defaultdict(list)
    for row in unique:
        by_label[row["label"]].append(row)
    splits = {"train": [], "valid": [], "test": []}
    rng = random.Random(seed)
    for group in by_label.values():
        rng.shuffle(group)
        n = len(group)
        n_test = int(n * .1)
        n_valid = int(n * .1)
        if n >= 3:
            n_test, n_valid = max(1, n_test), max(1, n_valid)
        splits["train"].extend(group[:n - n_valid - n_test])
        splits["valid"].extend(group[n - n_valid - n_test:n - n_test])
        splits["test"].extend(group[n - n_test:])
    for values in splits.values():
        rng.shuffle(values)
    return splits


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--output-dir", type=Path, default=Path("data/processed/phishing"))
    p.add_argument("--seed", type=int, default=17)
    a = p.parse_args()
    rows = [json.loads(line) for line in a.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    splits = prepare(rows, a.seed)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    stats = {"seed": a.seed, "counts": {}, "labels": {}}
    for name, records in splits.items():
        path = a.output_dir / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
        stats["counts"][name] = len(records)
        stats["labels"][name] = dict(Counter(r["label"] for r in records))
    (a.output_dir / "split-statistics.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()

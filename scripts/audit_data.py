#!/usr/bin/env python3
"""Audit local JSONL/CSV datasets without altering the input."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def read_rows(path: Path):
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        for line in path.open(encoding="utf-8"):
            if line.strip():
                yield json.loads(line)
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            yield from csv.DictReader(f)
    else:
        raise ValueError("Supported formats: JSONL and CSV")


def audit(path: Path):
    rows = list(read_rows(path))
    columns = Counter()
    missing = Counter()
    labels = Counter()
    fingerprints = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        columns.update(row.keys())
        for key, value in row.items():
            if value is None or not str(value).strip():
                missing[key] += 1
        label = row.get("labels", row.get("label"))
        if label is not None:
            labels[str(label)] += 1
        payload = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")).casefold()
        fingerprints[payload] += 1
    return {"file": str(path), "rows": len(rows), "columns": sorted(columns),
            "missing_values": dict(missing), "label_distribution": dict(labels),
            "exact_duplicate_rows": sum(n - 1 for n in fingerprints.values() if n > 1),
            "malformed_records": sum(not isinstance(row, dict) for row in rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.input)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()

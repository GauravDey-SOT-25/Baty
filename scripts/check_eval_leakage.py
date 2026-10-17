#!/usr/bin/env python3
"""Local exact/near-duplicate audit between eval prompts and instruction splits.

Only prompt/query text is compared. Outputs contain IDs and similarity scores,
not matched text. No network access and no training data is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"[a-z0-9]+", re.I)


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(unicodedata.normalize("NFKC", text).casefold()))


def shingles(text: str, size: int = 3) -> set[tuple[str, ...]]:
    words = normalize(text).split()
    if len(words) < size:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + size]) for i in range(len(words) - size + 1)}


def prompt_text(row: dict) -> str:
    if isinstance(row.get("messages"), list):
        return "\n".join(str(message.get("content", "")) for message in row["messages"]
                         if isinstance(message, dict) and message.get("role") == "user")
    for field in ("query", "question", "text", "prompt", "input"):
        if row.get(field):
            return str(row[field])
    return ""


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{number}: {exc}") from exc
        if isinstance(row, dict):
            result.append(row)
    return result


def audit(eval_rows: list[dict], split_paths: dict[str, Path], threshold: float = 0.8) -> dict:
    training = []
    split_counts = {}
    split_hashes = {}
    for split, path in split_paths.items():
        rows = load_rows(path)
        split_counts[split] = len(rows)
        split_hashes[split] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        for index, row in enumerate(rows):
            text = prompt_text(row)
            if text:
                training.append((split, str(row.get("id", row.get("source_id", index))), text))

    matches = []
    for index, row in enumerate(eval_rows):
        text = prompt_text(row)
        norm = normalize(text)
        eval_id = str(row.get("id", index))
        eval_shingles = shingles(text)
        best = (0.0, None, None, False)
        for split, source_id, candidate in training:
            candidate_norm = normalize(candidate)
            if not norm or not candidate_norm:
                continue
            candidate_shingles = shingles(candidate)
            union = eval_shingles | candidate_shingles
            similarity = len(eval_shingles & candidate_shingles) / len(union) if union else 0.0
            exact = norm == candidate_norm
            if exact:
                similarity = 1.0
            if similarity > best[0]:
                best = (similarity, split, source_id, exact)
        if best[0] >= threshold:
            matches.append({"evaluation_id": eval_id, "nearest_split": best[1],
                            "nearest_source_id": best[2], "jaccard_3gram": round(best[0], 4),
                            "exact_normalized_match": best[3]})

    return {
        "method": "NFKC/casefold alphanumeric normalization; exact normalized prompt check and word 3-gram Jaccard",
        "near_duplicate_threshold": threshold,
        "evaluation_count": len(eval_rows),
        "instruction_split_counts": split_counts,
        "instruction_split_sha256": split_hashes,
        "prompt_count_compared": len(training),
        "near_duplicate_matches": matches,
        "clear_at_threshold": not matches,
        "limitations": [
            "Lexical overlap cannot detect paraphrase, answer leakage, or semantic similarity.",
            "Short prompts can have coarse Jaccard scores; matches require human review.",
            "Only user prompts/queries are compared; system and assistant messages are excluded.",
            "This is a diagnostic audit, not proof of split independence.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, action="append", required=True,
                        help="Evaluation JSONL; may be repeated.")
    parser.add_argument("--split-dir", type=Path, default=ROOT / "data/processed/instructions")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/evaluation-leakage-audit.json")
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()
    split_paths = {name: args.split_dir / f"{name}.jsonl" for name in ("train", "valid", "test")}
    reports = []
    for path in args.evaluation:
        rows = load_rows(path)
        item = audit(rows, split_paths, args.threshold)
        item["evaluation_path"] = str(path)
        item["evaluation_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        reports.append(item)
    output = {"audit_id": "evaluation_prompt_overlap_v1", "network_access": "none",
              "audits": reports}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

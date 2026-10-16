from __future__ import annotations

import json
import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "data" / "processed" / "incidents.jsonl"


def search_incidents(description: str, limit: int = 5) -> dict:
    terms = set(re.findall(r"[a-z0-9]{3,}", (description or "").lower()))
    records = []
    if CORPUS.exists():
        for line in CORPUS.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    ranked = []
    for item in records:
        searchable = " ".join(str(item.get(k, "")) for k in ("title", "text", "summary")).lower()
        overlap = terms & set(re.findall(r"[a-z0-9]{3,}", searchable))
        if overlap:
            ranked.append((len(overlap), item))
    ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("published_at", ""))))
    return {"incidents": [item for _, item in ranked[:max(1, min(limit, 10))]],
            "corpus_records": len(records),
            "message": "Lexical local search only; HN or other incident sources have not yet been ingested." if not records else "Results are ranked by word overlap and require source verification."}

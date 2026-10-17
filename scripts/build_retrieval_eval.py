#!/usr/bin/env python3
"""Build a fixed retrieval benchmark from pinned IDs in the local CISA snapshot.

Queries and labels are project-authored; factual source metadata is copied from
the local CISA KEV/advisory records. The script makes no network requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASES = [
    # Exact CVE lookup
    ("kev-exact-01", "exact_cve", "CVE-2026-102764", ["CVE-2026-102764"]),
    ("kev-exact-02", "exact_cve", "CVE-2025-61624", ["CVE-2025-61624"]),
    ("kev-exact-03", "exact_cve", "CVE-2026-21589", ["CVE-2026-21589"]),
    ("kev-exact-04", "exact_cve", "CVE-2026-105134", ["CVE-2026-105134"]),
    ("kev-exact-05", "exact_cve", "CVE-2026-76519", ["CVE-2026-76519"]),
    ("kev-exact-06", "exact_cve", "CVE-2026-0322", ["CVE-2026-0322"]),
    # CISA advisory lookup
    ("advisory-exact-01", "exact_advisory", "Eclipse Foundation Eclipse Milo", ["/node/25629"]),
    ("advisory-exact-02", "exact_advisory", "Thermo Fisher Torrent Suite Software", ["/node/25627"]),
    ("advisory-exact-03", "exact_advisory", "Cyber Threat Actors Use a Variety of Techniques to Target Election and Campaign Officials", ["/node/25636"]),
    # Relevant local-record searches with authored paraphrase
    ("kev-relevant-01", "relevant_security_record", "BeyondTrust Remote Support spoofing authentication bypass", ["CVE-2026-102764"]),
    ("kev-relevant-02", "relevant_security_record", "Fortinet FortiPAM FortiProxy FortiSwitchManager path traversal", ["CVE-2025-61624"]),
    ("kev-relevant-03", "relevant_security_record", "Atlassian Data Center files accessible external parties", ["CVE-2026-21589"]),
    ("kev-relevant-04", "relevant_security_record", "AhsayCBS command injection replication receiver", ["CVE-2026-105134"]),
    ("kev-relevant-05", "relevant_security_record", "Cisco Secure Email Gateway relative path traversal", ["CVE-2026-76519"]),
    ("kev-relevant-06", "relevant_security_record", "Palo Alto Networks PAN-OS code injection firewall", ["CVE-2026-0322"]),
    ("advisory-relevant-01", "relevant_security_record", "CISA advisory vulnerabilities in Eclipse Milo", ["/node/25629"]),
    ("advisory-relevant-02", "relevant_security_record", "CISA advisory vulnerabilities in Thermo Fisher Torrent Suite", ["/node/25627"]),
    # Broad or common-word queries; correct behavior is to return no evidence.
    ("ambiguous-01", "ambiguous_query", "Cisco", []),
    ("ambiguous-02", "ambiguous_query", "Microsoft patch", []),
    ("ambiguous-03", "ambiguous_query", "security", []),
    ("ambiguous-04", "ambiguous_query", "latest vulnerability updates", []),
    ("common-01", "common_word_false_match", "What is vulnerability security?", []),
    ("common-02", "common_word_false_match", "latest security update", []),
    ("common-03", "common_word_false_match", "What are general security practices?", []),
    ("missing-01", "missing_evidence_abstention", "What is the local status of CVE-2099-54321?", []),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/processed/incidents.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "data/evaluation/cyber_retrieval_v1.jsonl")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/evaluation/cyber_retrieval_v1-manifest.json")
    args = parser.parse_args()
    raw = args.corpus.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    by_id = {str(row["id"]): row for row in rows if isinstance(row, dict) and row.get("id")}
    if len(by_id) != len([row for row in rows if isinstance(row, dict) and row.get("id")]):
        raise SystemExit("Corpus contains duplicate record IDs")
    examples = []
    for example_id, category, query, expected_ids in CASES:
        refs = []
        for record_id in expected_ids:
            item = by_id.get(record_id)
            if item is None:
                raise SystemExit(f"Expected source record missing from corpus: {record_id}")
            if item.get("record_type") not in {"known_exploited_vulnerability", "cisa_advisory"}:
                raise SystemExit(f"Benchmark factual reference must be an official CISA record: {record_id}")
            refs.append({
                "id": record_id,
                "title": item.get("title"),
                "source": item.get("source"),
                "source_url": item.get("source_url"),
                "published_at": item.get("published_at"),
                "snapshot_released_at": item.get("catalog_released_at") or item.get("fetched_at"),
                "license_note": item.get("license"),
            })
        examples.append({
            "id": example_id,
            "category": category,
            "query": query,
            "expected_record_ids": expected_ids,
            "should_abstain": not bool(expected_ids),
            "query_provenance": "Project-authored retrieval query; not used for training or tuning.",
            "factual_sources": refs,
        })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in examples).encode()
    args.output.write_bytes(serialized)
    manifest = {
        "evaluation_id": "cyber_retrieval_v1",
        "example_count": len(examples),
        "evaluation_sha256": hashlib.sha256(serialized).hexdigest(),
        "corpus_sha256": hashlib.sha256(raw).hexdigest(),
        "corpus_path": str(args.corpus),
        "source_policy": "Factual references use only official CISA KEV/advisory snapshot records; queries and labels are project-authored.",
        "license_notes": "CISA public catalog/feed metadata and attributed summaries. Confirm source terms before redistribution. Evaluation-only; do not train on this file.",
        "network_access": "None; generated from the local corpus snapshot.",
        "categories": {category: sum(row["category"] == category for row in examples) for _, category, _, _ in CASES},
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

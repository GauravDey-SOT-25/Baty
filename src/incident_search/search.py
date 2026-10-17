from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "data" / "processed" / "incidents.jsonl"
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", re.I)
STOP = set("""a an the and or for with from that this have has was were into when what how are but not can could would should about your their they them there then than been being use used using system systems issue incident is it to of in on at by as be do does did we our you i me my all any more most current latest recent now today status update version versions patch vulnerability vulnerable exploit exploited exploitation confirmed report reported article advisory source organization organization’s organization’s installed product products""".split())
STOP.update({"security", "cybersecurity", "cyber", "practice", "practices"})
FIELD_WEIGHTS = {"title": 3.0, "vendor": 2.5, "product": 2.5, "id": 4.0,
                 "summary": 1.6, "text": 0.7}
MIN_SCORE = 1.15
MIN_QUERY_COVERAGE = 0.60


@lru_cache(maxsize=2)
def _records(path: str, stamp: int):
    records = []
    p = Path(path)
    if not p.exists():
        return ()
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("id") and item.get("source_url"):
            records.append(item)
    return tuple(records)


def _terms(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    return {term for term in TOKEN_RE.findall(normalized) if term not in STOP and len(term) > 1}


def _result(item: dict, overlap: set[str], score: float) -> dict:
    result = {key: item.get(key) for key in (
        "id", "record_type", "title", "summary", "vendor", "product", "published_at", "due_date",
        "known_ransomware_campaign_use", "source_url", "advisory_urls", "required_action", "author",
        "parent_id", "score", "descendants", "child_ids", "outbound_url", "source", "source_url_root",
        "catalog_version", "catalog_released_at", "fetched_at", "license") if item.get(key) is not None}
    result["text"] = str(item.get("summary") or item.get("text", ""))[:4000]
    result["source"] = item.get("source")
    result["catalog_version"] = item.get("catalog_version")
    result["similarities"] = sorted(overlap)
    result["relevance_score"] = round(score, 4)
    result["retrieval_method"] = "field-weighted lexical BM25; score is not semantic similarity"
    return result


def search_incidents(description: str, limit: int = 5) -> dict:
    normalized_query = unicodedata.normalize("NFKC", (description or "")[:8000]).casefold()
    query = _terms(normalized_query)
    records = _records(str(CORPUS), CORPUS.stat().st_mtime_ns if CORPUS.exists() else 0)
    limitations = ["Lexical ranking is not semantic similarity.", "The corpus is a dated local snapshot; verify current vendor guidance.",
                   "Hacker News posts are community discussion, not authoritative confirmation.",
                   "This is not a comprehensive incident-postmortem archive."]
    if not query:
        return {"incidents": [], "corpus_records": len(records), "message": "Enter descriptive terms or a CVE identifier to search local security records.", "limitations": limitations}

    cve_ids = set(re.findall(r"\bcve-\d{4}-\d+\b", normalized_query))
    if cve_ids:
        exact = [item for item in records if str(item.get("id", "")).casefold() in cve_ids]
        if not exact:
            return {"incidents": [], "corpus_records": len(records),
                    "message": "No exact CVE identifier match exists in this local snapshot.",
                    "limitations": limitations}
        selected = []
        for item in exact[:max(1, min(limit, 10))]:
            fields = {name: _terms(str(item.get(name, ""))) for name in FIELD_WEIGHTS}
            terms = set().union(*fields.values())
            selected.append(_result(item, query & terms, 1000.0))
        return {"incidents": selected, "corpus_records": len(records),
                "message": "Exact CVE identifier match in the local snapshot; verify current details at the attributed source.",
                "limitations": limitations}
    if len(query) < 2 and not cve_ids:
        return {"incidents": [], "corpus_records": len(records),
                "message": "The query is too broad for reliable local retrieval; add a product, vulnerability type, or exact CVE identifier.",
                "limitations": limitations}

    fields = [{name: _terms(str(item.get(name, ""))) for name in FIELD_WEIGHTS} for item in records]
    n = max(1, len(records))
    df = {term: sum(any(term in doc[name] for name in FIELD_WEIGHTS) for doc in fields) for term in query}
    ranked = []
    for item, field_terms in zip(records, fields):
        overlap = query & set().union(*field_terms.values())
        exact_id = any(cve == str(item.get("id", "")).casefold() for cve in cve_ids)
        if not overlap and not exact_id:
            continue
        score = 0.0
        for term in overlap:
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            for field, weight in FIELD_WEIGHTS.items():
                if term in field_terms[field]:
                    # Binary field frequency prevents repeated boilerplate from inflating relevance.
                    score += idf * weight
        coverage = len(overlap) / max(1, len(query))
        # Penalize partial matches directly. The former 1.8 multiplier
        # saturated at just 56% query coverage, admitting product-name
        # coincidences as though they matched the complete request.
        score *= coverage
        if coverage < MIN_QUERY_COVERAGE and not exact_id:
            continue
        if exact_id:
            score += 12.0
        if score < MIN_SCORE and not exact_id:
            continue
        ranked.append((score, _result(item, overlap, score)))

    ranked.sort(key=lambda pair: (-pair[0], str(pair[1].get("published_at", ""))))
    # Keep only records reasonably close to the best lexical candidate. This
    # removes weak tail matches without suppressing similarly relevant records.
    if ranked:
        best = ranked[0][0]
        ranked = [pair for pair in ranked if pair[0] >= max(MIN_SCORE, best * 0.70)]
    selected = [item for _, item in ranked[:max(1, min(limit, 10))]]
    return {"incidents": selected, "corpus_records": len(records),
            "message": ("Local CISA advisory, KEV, and Hacker News records matched. Community posts are anecdotal; matches are not evidence that your organization was affected."
                        if selected else "No sufficiently relevant local security records matched; no evidence is available from this corpus."),
            "limitations": limitations}

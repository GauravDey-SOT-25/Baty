from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "data" / "processed" / "incidents.jsonl"
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9._-]{1,}", re.I)
STOP = {"the","and","for","with","from","that","this","have","has","was","were","into","when","what","how","are","but","not","can","could","would","should","about","your","their","they","them","there","then","than","been","being","use","used","using","system","systems","issue","incident"}

@lru_cache(maxsize=2)
def _records(path: str, stamp: int):
    records=[]
    p=Path(path)
    if not p.exists(): return ()
    for line in p.read_text(encoding="utf-8").splitlines():
        try: item=json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(item,dict) and item.get("id") and item.get("source_url"):
            records.append(item)
    return tuple(records)

def _terms(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text or "") if t.lower() not in STOP}

def search_incidents(description: str, limit: int = 5) -> dict:
    query=_terms((description or "")[:8000])
    records=_records(str(CORPUS),CORPUS.stat().st_mtime_ns if CORPUS.exists() else 0)
    if not query:
        return {"incidents":[],"corpus_records":len(records),"message":"Enter descriptive terms or a CVE identifier to search local security records.","limitations":["The local corpus contains CISA Known Exploited Vulnerabilities records, not a comprehensive incident-postmortem archive."]}
    document_terms=[_terms(" ".join(str(item.get(k,"")) for k in ("title","text","summary","vendor","product","id"))) for item in records]
    df={term:sum(term in doc for doc in document_terms) for term in query}
    ranked=[]
    n=max(1,len(records))
    for item,doc in zip(records,document_terms):
        overlap=query & doc
        if not overlap: continue
        # Simple BM25-like lexical score; ranking aid only, not semantic similarity.
        score=0.0
        full=" ".join(str(item.get(k,"")) for k in ("title","summary","vendor","product","id")).lower()
        for term in overlap:
            idf=math.log(1+(n-df[term]+0.5)/(df[term]+0.5))
            tf=full.count(term)+sum(str(item.get(k," ")).lower().count(term) for k in ("text",))
            score+=idf*(tf*2.2)/(tf+1.2)
        if item.get("id","").lower() in (description or "").lower(): score+=10
        result={k:item.get(k) for k in ("id","record_type","title","summary","vendor","product","published_at","due_date","known_ransomware_campaign_use","source_url","advisory_urls","required_action","author","parent_id","score","descendants","child_ids","outbound_url") if item.get(k) is not None}
        result["text"] = str(item.get("summary") or item.get("text", ""))[:4000]
        result["source"] = item.get("source")
        result["catalog_version"] = item.get("catalog_version")
        result["similarities"] = sorted(overlap)
        result["retrieval_method"] = "lexical overlap; no semantic claim"
        ranked.append((score,result))
    ranked.sort(key=lambda x:(-x[0],str(x[1].get("published_at",""))))
    return {"incidents":[item for _,item in ranked[:max(1,min(limit,10))]],"corpus_records":len(records),"message":"Local CISA advisory, KEV, and Hacker News records matched. Community posts are anecdotal; matches are not evidence that your organization was affected.","limitations":["Lexical ranking is not semantic similarity.","The corpus is a dated local snapshot; verify current vendor guidance.","Hacker News posts are community discussion, not authoritative confirmation.","This is not a comprehensive incident-postmortem archive."]}

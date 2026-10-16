#!/usr/bin/env python3
"""Combine normalized official CISA and bounded Hacker News records for local retrieval."""
import argparse, json
from pathlib import Path
SOURCES=(Path("data/processed/kev.jsonl"),Path("data/processed/advisories.jsonl"),Path("data/processed/hacker-news.jsonl"))
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=Path("data/processed/incidents.jsonl"));a=p.parse_args();records=[]
 for source in SOURCES:
  if source.exists():
   for line in source.read_text(encoding="utf-8").splitlines():
    try: item=json.loads(line)
    except json.JSONDecodeError: continue
    if isinstance(item,dict) and item.get("id") and item.get("source_url"): records.append(item)
 ids=[str(r["id"]) for r in records]
 if len(ids)!=len(set(ids)): raise ValueError("Duplicate record IDs found across retrieval inputs")
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records),encoding="utf-8")
 from collections import Counter
 print(json.dumps({"records":len(records),"types":dict(Counter(r.get("record_type") for r in records)),"output":str(a.output)},indent=2))
if __name__=="__main__":main()

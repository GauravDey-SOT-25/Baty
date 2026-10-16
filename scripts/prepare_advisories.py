#!/usr/bin/env python3
"""Convert a bounded official CISA RSS snapshot into local retrieval records."""
import argparse, json, re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

FEED_URL="https://www.cisa.gov/cybersecurity-advisories/all.xml"
MAX_FEED_BYTES=5_000_000
class TextOnly(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in {"script","style"}: self.skip+=1
        elif tag in {"p","li","br","div"}: self.parts.append(" ")
    def handle_endtag(self, tag):
        if tag in {"script","style"} and self.skip: self.skip-=1
        elif tag in {"p","li","div"}: self.parts.append(" ")
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)
    def text(self): return re.sub(r"\s+"," "," ".join(self.parts)).strip()

def parse_feed(path: Path, fetched_at: str | None=None):
    content=path.read_bytes()
    if len(content)>MAX_FEED_BYTES or b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper(): raise ValueError("Feed exceeds size limit or contains a DTD/entity declaration")
    root=ET.fromstring(content); channel=root.find("channel")
    if channel is None: raise ValueError("Expected RSS channel")
    fetched_at=fetched_at or datetime.now(timezone.utc).isoformat(); records=[]
    for item in channel.findall("item"):
        title=(item.findtext("title") or "").strip(); url=(item.findtext("link") or "").strip()
        if not title or not url.startswith("https://www.cisa.gov/"): continue
        parser=TextOnly(); parser.feed(item.findtext("description") or ""); summary=parser.text()[:8000]
        if not summary: continue
        guid=(item.findtext("guid") or url).strip()
        records.append({"id":guid,"record_type":"cisa_advisory","title":title,"summary":summary,"text":title+" "+summary,"published_at":(item.findtext("pubDate") or "").strip(),"source_url":url,"source":"CISA Cybersecurity Advisories RSS","source_url_root":FEED_URL,"fetched_at":fetched_at,"license":"CISA RSS metadata and summaries; source attribution retained"})
    return records

def main():
 p=argparse.ArgumentParser();p.add_argument("input",type=Path,nargs="?",default=Path("data/raw/cisa-advisories.xml"));p.add_argument("--output",type=Path,default=Path("data/processed/advisories.jsonl"));a=p.parse_args(); rows=parse_feed(a.input);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8");print(json.dumps({"records":len(rows),"output":str(a.output)},indent=2))
if __name__=="__main__":main()

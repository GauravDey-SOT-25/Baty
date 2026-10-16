#!/usr/bin/env python3
"""Select cybersecurity-relevant Hacker News records from one local Parquet month."""
import argparse, html, json, re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import pyarrow.parquet as pq

SOURCE="open-index/hacker-news"
REVISION="c54ced5973b95d80cd934b8921f44ec8d87c3cd1"
KEYWORDS=re.compile(r"\b(cyber.?security|infosec|phish(?:ing)?|ransomware|malware|breach|data leak|vulnerabilit(?:y|ies)|\bCVE-\d{4}-\d+\b|exploit(?:ation)?|patch(?:ing)?|zero[ -]day|incident response|credential theft|security (?:flaw|advisory|research|tool|incident)|auth(?:entication)? bypass|supply chain attack|botnet|intrusion|compromis(?:e|ed|ing)|spyware|trojan|denial.of.service|DDoS)\b",re.I)
class Strip(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.skip=0
 def handle_starttag(self,tag,attrs):
  if tag in {"script","style"}:self.skip+=1
 def handle_endtag(self,tag):
  if tag in {"script","style"} and self.skip:self.skip-=1
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
 def text(self):return re.sub(r"\s+"," "," ".join(self.parts)).strip()
def clean(value):
 p=Strip();p.feed(html.unescape(str(value or "")));return p.text()[:12000]
def extract(path:Path):
 pf=pq.ParquetFile(path)
 required={"id","by","time","text","parent","url","score","title","type","descendants","kids","deleted","dead"}
 if not required.issubset(pf.schema_arrow.names):raise ValueError(f"Unexpected HN schema: {pf.schema_arrow.names}")
 rows=[]
 for batch in pf.iter_batches(batch_size=8192,columns=sorted(required)):
  for row in batch.to_pylist():
   if row.get("deleted") or row.get("dead"):continue
   title=clean(row.get("title")); text=clean(row.get("text"))
   combined=(title+" "+text).strip()
   if not combined or not KEYWORDS.search(combined):continue
   item_id=row.get("id")
   if item_id is None:continue
   ts=row.get("time")
   if isinstance(ts,datetime):published=ts.astimezone(timezone.utc).isoformat()
   else:published=str(ts or "")
   item_url=f"https://news.ycombinator.com/item?id={item_id}"
   rows.append({"id":str(item_id),"record_type":"community_discussion","title":title,"text":text,"summary":(text or title)[:1200],"author":row.get("by"),"published_at":published,"parent_id":row.get("parent"),"score":row.get("score"),"descendants":row.get("descendants"),"child_ids":row.get("kids") or [],"source_url":item_url,"outbound_url":row.get("url"),"source":SOURCE,"source_revision":REVISION,"license":"ODC-By 1.0 database; original post/comment authors retain rights; attribution linked to item"})
 return rows,pf.metadata.num_rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument("input",type=Path);ap.add_argument("--output",type=Path,default=Path("data/processed/hacker-news.jsonl"));a=ap.parse_args();records,total=extract(a.input);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records),encoding="utf-8");print(json.dumps({"source":SOURCE,"revision":REVISION,"input_rows":total,"selected_rows":len(records),"output":str(a.output)},indent=2))
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Run local model against fixed held-out prompt/answer examples for review."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.assistant.local_model import answer_locally

def main():
 p=argparse.ArgumentParser();p.add_argument("--data",type=Path,default=Path("data/processed/curated/test.jsonl"));p.add_argument("--output",type=Path,default=Path("reports/assistant-evaluation.jsonl"));p.add_argument("--max-tokens",type=int,default=160);a=p.parse_args()
 examples=[json.loads(line) for line in a.data.read_text(encoding="utf-8").splitlines() if line.strip()];a.output.parent.mkdir(parents=True,exist_ok=True);out=[]
 for i,item in enumerate(examples,1):
  msgs=item["messages"]; question=next(m["content"] for m in msgs if m["role"]=="user"); reference=next(m["content"] for m in msgs if m["role"]=="assistant")
  generated=answer_locally(question,[],a.max_tokens)
  if generated is None: raise SystemExit("Local model unavailable; evaluation not completed")
  out.append({"source_id":item.get("source_id"),"question":question,"reference_answer":reference,"model_answer":generated})
  print(f"Generated {i}/{len(examples)}")
 a.output.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in out),encoding="utf-8")
 print(f"Saved qualitative review set to {a.output}")
if __name__=="__main__":main()

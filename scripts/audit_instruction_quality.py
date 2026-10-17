#!/usr/bin/env python3
"""Report review flags for instruction data; flags are not automatic quality verdicts."""
import argparse,json,re
from pathlib import Path

FIELDS={"user":("user","prompt","question"),"assistant":("assistant","response","answer")}
FLAGS={"internal_reasoning":re.compile(r"\b(the user wants to know|let me start|let me explain|I should (?:explain|consider|provide)|I need to (?:explain|provide)|my thought process)\b",re.I),"placeholder_language":re.compile(r"\b(information not found|not enough information to answer)\b",re.I),"generic_model_disclaimer":re.compile(r"\b(as an AI(?: language model)?|I do not have the capability)\b",re.I)}
def find_text(row,field):
 for key in FIELDS[field]:
  if isinstance(row.get(key),str):return row[key]
  if isinstance(row.get(key),list):
   for message in row[key]:
    if isinstance(message,dict) and message.get("role")==("assistant" if field=="assistant" else "user"):return str(message.get("content",""))
 messages=row.get("messages")
 if isinstance(messages,list):
  role="assistant" if field=="assistant" else "user"
  for message in messages:
   if isinstance(message,dict) and message.get("role")==role:
    return str(message.get("content",""))
 return ""
def audit(path):
 counts={k:0 for k in FLAGS}; rows=0; missing_user=0; missing_answer=0; answer_lengths=[]; seen=set();duplicates=0
 for line in path.read_text(encoding="utf-8").splitlines():
  if not line.strip():continue
  row=json.loads(line);rows+=1;u=find_text(row,"user");a=find_text(row,"assistant")
  if not u.strip():missing_user+=1
  if not a.strip():missing_answer+=1
  answer_lengths.append(len(a));key=(u.strip().casefold(),a.strip().casefold())
  if key in seen:duplicates+=1
  seen.add(key)
  for name,pattern in FLAGS.items():
   if pattern.search(a):counts[name]+=1
 return {"file":str(path),"rows":rows,"missing_user":missing_user,"missing_answer":missing_answer,"exact_prompt_answer_duplicates":duplicates,"assistant_character_lengths":{"min":min(answer_lengths,default=0),"median":sorted(answer_lengths)[len(answer_lengths)//2] if answer_lengths else 0,"max":max(answer_lengths,default=0)},"review_flag_counts":counts,"note":"Automated string flags are triage aids, not factuality or safety labels; human review remains necessary."}
def main():
 p=argparse.ArgumentParser();p.add_argument("inputs",nargs="+",type=Path);p.add_argument("--output",type=Path,default=Path("reports/instruction-quality-audit.json"));a=p.parse_args();result={str(x):audit(x) for x in a.inputs};a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8");print(json.dumps(result,indent=2))
if __name__=="__main__":main()

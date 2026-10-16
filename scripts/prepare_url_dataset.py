#!/usr/bin/env python3
"""Prepare UCI PhiUSIIL URLs with exact-dedupe and domain-grouped splits."""
import argparse, csv, hashlib, json, random, re, ipaddress, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter, defaultdict
from urllib.parse import urlsplit
from src.url_analysis.text import classifier_text

SOURCE = "UCI PhiUSIIL Phishing URL (Website)"
REVISION = "UCI dataset 967, last updated 2024-05-12"
LICENSE = "CC-BY-4.0"

MULTI_LABEL_SUFFIXES={"co.uk","org.uk","ac.uk","gov.uk","com.au","net.au","org.au","com.br","com.cn","com.hk","co.in","firm.in","net.in","org.in","co.jp","ne.jp","or.jp","com.mx","co.nz","co.za","com.sg","com.tr","com.tw","com.ua","com.ar","com.pl","com.ru","com.de","com.fr","com.es","com.it","com.nl","com.se","com.no","com.fi","com.io","com.dev"}

def registrable_domain(host: str) -> str:
    try: return str(ipaddress.ip_address(host))
    except ValueError: pass
    labels=host.lower().rstrip(".").split(".")
    suffix=".".join(labels[-2:]) if len(labels)>=2 else host
    take=3 if suffix in MULTI_LABEL_SUFFIXES and len(labels)>=3 else 2
    return ".".join(labels[-take:])

def safe_text(raw: str) -> tuple[str, str]:
    value = (raw or "").strip()
    parts = urlsplit(value if "://" in value else "//" + value)
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or any(c.isspace() for c in host):
        return "", ""
    # Preserve query key structure but remove potentially identifying/token values.
    safe = classifier_text(value)
    return safe, registrable_domain(host)

def grouped_splits(rows, seed=17):
    # Split by entire hostnames, so related URLs cannot occur across partitions.
    from sklearn.model_selection import GroupShuffleSplit
    groups=[row["domain"] for row in rows]
    all_indices=list(range(len(rows)))
    if len(set(groups)) < 5:
        keys=list(set(groups)); random.Random(seed).shuffle(keys)
        names=("train","valid","test")
        assignment={key:names[i % 3] for i,key in enumerate(keys)}
        return {name:[row for row in rows if assignment[row["domain"]]==name] for name in names}
    splitter=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=seed)
    train_idx,hold_idx=next(splitter.split(all_indices,groups=groups))
    hold_rows=[rows[i] for i in hold_idx]
    hold_groups=[groups[i] for i in hold_idx]
    splitter2=GroupShuffleSplit(n_splits=1,test_size=.5,random_state=seed+1)
    valid_rel,test_rel=next(splitter2.split(hold_rows,groups=hold_groups))
    return {"train":[rows[i] for i in train_idx],"valid":[hold_rows[i] for i in valid_rel],"test":[hold_rows[i] for i in test_rel]}

def prepare(csv_path: Path, seed=17):
    seen={}; rows=[]; malformed=0; missing=0; conflicts=0
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader=csv.DictReader(f)
        input_count=0
        required={"URL","label"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames): raise ValueError(f"Expected columns URL,label; got {reader.fieldnames}")
        for idx, record in enumerate(reader):
            input_count += 1
            url,domain=safe_text(record.get("URL", ""))
            try: raw_label=int(record.get("label", ""))
            except (ValueError,TypeError): malformed+=1; continue
            if not url or raw_label not in (0,1): missing+=1; continue
            label="legitimate" if raw_label==1 else "phishing"
            digest=hashlib.sha256(url.casefold().encode()).hexdigest()
            if digest in seen:
                if seen[digest]["label"] != label: conflicts+=1; seen[digest]["conflict"]=True
                continue
            row={"content":url,"label":label,"source_id":record.get("FILENAME") or idx,"source":SOURCE,"source_revision":REVISION,"license":LICENSE,"domain":domain}
            seen[digest]=row
    rows=[r for r in seen.values() if not r.get("conflict")]
    splits=grouped_splits(rows,seed)
    stats={"source":SOURCE,"source_revision":REVISION,"license":LICENSE,"seed":seed,"input_rows":input_count,"usable_unique_urls":len(rows),"malformed_rows":malformed,"missing_or_invalid_rows":missing,"duplicate_label_conflicts":conflicts,"split_counts":{},"split_labels":{},"domain_overlap":False,"group_key":"approximate registrable domain (built-in common suffix list; see limitations)","query_values":"replaced with REDACTED; fragments removed"}
    for name,part in splits.items(): stats["split_counts"][name]=len(part); stats["split_labels"][name]=dict(Counter(r["label"] for r in part))
    return splits,stats

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("input",type=Path,nargs="?",default=Path("data/raw/phiusiil.csv")); ap.add_argument("--output-dir",type=Path,default=Path("data/processed/phishing")); ap.add_argument("--seed",type=int,default=17); a=ap.parse_args()
    splits,stats=prepare(a.input,a.seed); a.output_dir.mkdir(parents=True,exist_ok=True)
    domains={n:{r["domain"] for r in part} for n,part in splits.items()}
    if domains["train"] & domains["test"] or domains["train"] & domains["valid"] or domains["valid"] & domains["test"]: raise RuntimeError("domain leakage across splits")
    for name,part in splits.items(): (a.output_dir/f"{name}.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in part),encoding="utf-8")
    stats["domain_overlap"]=False; (a.output_dir/"split-statistics.json").write_text(json.dumps(stats,indent=2)+"\n",encoding="utf-8"); print(json.dumps(stats,indent=2))
if __name__=="__main__": main()

#!/usr/bin/env python3
"""Fetch one pinned HN Parquet month, bounded to files below 250 MB."""
import argparse,re,subprocess
from pathlib import Path
REVISION="c54ced5973b95d80cd934b8921f44ec8d87c3cd1"
MAX_BYTES=250_000_000

def main():
 p=argparse.ArgumentParser();p.add_argument("month",help="Month available in open-index/hacker-news, e.g. 2026-08");p.add_argument("--output-dir",type=Path,default=Path("data/raw"));a=p.parse_args()
 if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])",a.month):raise SystemExit("month must use YYYY-MM")
 url=f"https://huggingface.co/datasets/open-index/hacker-news/resolve/{REVISION}/data/{a.month[:4]}/{a.month}.parquet?download=true"
 headers=subprocess.run(["curl","-fLIsS","--max-time","45",url],check=True,stdout=subprocess.PIPE,text=True).stdout
 sizes=re.findall(r"(?im)^content-length:\s*(\d+)\s*$",headers)
 if not sizes:raise SystemExit("Could not verify final file size; refusing download")
 size=int(sizes[-1])
 if size>MAX_BYTES:raise SystemExit(f"Monthly shard is {size} bytes, above the bounded {MAX_BYTES}-byte limit")
 a.output_dir.mkdir(parents=True,exist_ok=True);out=a.output_dir/f"hacker-news-{a.month}.parquet"
 if out.exists():raise SystemExit(f"Refusing to overwrite existing file: {out}")
 subprocess.run(["curl","-fL","--retry","2","--max-time","300",url,"-o",str(out)],check=True)
 if out.stat().st_size!=size:raise SystemExit(f"Downloaded size mismatch: expected {size}, got {out.stat().st_size}")
 print(f"Fetched {out} ({size} bytes) from open-index/hacker-news@{REVISION}")
if __name__=="__main__":main()

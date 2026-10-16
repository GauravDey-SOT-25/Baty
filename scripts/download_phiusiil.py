#!/usr/bin/env python3
"""Fetch the 54 MB CC BY 4.0 UCI PhiUSIIL CSV via the platform TLS stack."""
import argparse, hashlib, subprocess
from pathlib import Path
URL="https://archive.ics.uci.edu/static/public/967/data.csv"
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,default=Path("data/raw/phiusiil.csv")); a=ap.parse_args()
 a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists(): raise SystemExit(f"Refusing to overwrite existing file: {a.output}")
 subprocess.run(["curl","-fL","--retry","2","--max-time","180",URL,"-o",str(a.output)],check=True)
 digest=hashlib.sha256(a.output.read_bytes()).hexdigest(); print(f"Downloaded {a.output} ({a.output.stat().st_size} bytes; sha256 {digest})")
if __name__=="__main__": main()

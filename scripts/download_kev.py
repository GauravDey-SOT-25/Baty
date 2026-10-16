#!/usr/bin/env python3
"""Fetch the current 2 MB CISA KEV JSON with curl's platform trust store."""
import argparse, subprocess
from pathlib import Path
URL="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=Path("data/raw/cisa-kev.json"));a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists(): raise SystemExit(f"Refusing to overwrite existing file: {a.output}")
 subprocess.run(["curl","-fL","--retry","2","--max-time","60",URL,"-o",str(a.output)],check=True)
 print(f"Fetched CISA KEV snapshot to {a.output}")
if __name__=="__main__":main()

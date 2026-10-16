#!/usr/bin/env python3
"""Fetch the bounded CISA all-advisories RSS snapshot; app runtime remains offline."""
import argparse,subprocess
from pathlib import Path
URL="https://www.cisa.gov/cybersecurity-advisories/all.xml"
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=Path("data/raw/cisa-advisories.xml"));a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists():raise SystemExit(f"Refusing to overwrite existing file: {a.output}")
 subprocess.run(["curl","-fL","--retry","2","--max-time","90",URL,"-o",str(a.output)],check=True)
 print(f"Fetched CISA RSS snapshot: {a.output} ({a.output.stat().st_size} bytes)")
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Normalize a downloaded CISA KEV catalog into provenance-rich retrieval records."""
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

CATALOG_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"

def convert(raw: dict, fetched_at: str | None = None) -> list[dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    records=[]
    for item in raw.get("vulnerabilities", []):
        cve=item.get("cveID", "")
        if not cve.startswith("CVE-") or not item.get("shortDescription"):
            continue
        text=" ".join(str(item.get(k,"")) for k in ("vulnerabilityName","vendorProject","product","shortDescription","requiredAction","knownRansomwareCampaignUse","cwes"))
        records.append({"id":cve,"record_type":"known_exploited_vulnerability","title":item.get("vulnerabilityName",""),"text":text,"summary":item.get("shortDescription",""),"required_action":item.get("requiredAction",""),"vendor":item.get("vendorProject",""),"product":item.get("product",""),"published_at":item.get("dateAdded"),"due_date":item.get("dueDate"),"known_ransomware_campaign_use":item.get("knownRansomwareCampaignUse"),"source_url":f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search={cve}","advisory_urls":[u.strip() for u in str(item.get("notes","")).split(";") if u.strip().startswith("https://")],"source":"CISA Known Exploited Vulnerabilities Catalog","source_url_root":CATALOG_URL,"catalog_version":raw.get("catalogVersion"),"catalog_released_at":raw.get("dateReleased"),"fetched_at":fetched_at,"license":"U.S. government public catalog; verify source terms before redistribution"})
    return records

def main():
    p=argparse.ArgumentParser(); p.add_argument("input",type=Path,default=Path("data/raw/cisa-kev.json")); p.add_argument("--output",type=Path,default=Path("data/processed/kev.jsonl")); a=p.parse_args()
    raw=json.loads(a.input.read_text(encoding="utf-8")); records=convert(raw)
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records),encoding="utf-8"); print(json.dumps({"records":len(records),"catalog_version":raw.get("catalogVersion"),"released_at":raw.get("dateReleased"),"output":str(a.output)},indent=2))
if __name__=="__main__": main()

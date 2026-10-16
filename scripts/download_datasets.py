#!/usr/bin/env python3
"""Fetch a bounded sample through the Hugging Face datasets-server rows API.

This avoids cloning/downloading the full source shard. It requests only public rows;
never pass private user content as the dataset ID. No remote dataset code is run.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote, urlencode

ROOT = Path(__file__).resolve().parents[1]
API = "https://datasets-server.huggingface.co"
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def get_json(url):
    response = subprocess.run(["curl", "-fsS", "--max-time", "60", url], check=False,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if response.returncode:
        raise RuntimeError(response.stderr.strip() or f"Request failed ({response.returncode})")
    return json.loads(response.stdout)


def download_sample(dataset_id, config, split, limit, output):
    if not REPO_PATTERN.fullmatch(dataset_id):
        raise ValueError("dataset ID must have the form owner/name")
    output = output.resolve()
    raw_root = (ROOT / "data/raw").resolve()
    if not output.is_relative_to(raw_root):
        raise ValueError("output must be inside this project's data/raw directory")
    info = get_json(f"https://huggingface.co/api/datasets/{quote(dataset_id, safe='/')}")
    revision = info.get("sha")
    license_name = info.get("cardData", {}).get("license")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".partial")
    count = 0
    try:
        with temp.open("w", encoding="utf-8") as f:
            first_query = urlencode({"dataset": dataset_id, "config": config, "split": split,
                                     "offset": 0, "length": min(100, limit)})
            first_page = get_json(f"{API}/rows?{first_query}")
            total_rows = int(first_page.get("num_rows_total", 0))
            effective_limit = min(limit, total_rows)
            pages = (effective_limit + 99) // 100
            if total_rows <= limit:
                offsets = list(range(0, total_rows, 100))
            else:
                last_start = max(total_rows - min(100, effective_limit), 0)
                offsets = [round(index * last_start / max(pages - 1, 1)) for index in range(pages)]
            for page_index, offset in enumerate(offsets):
                length = min(100, effective_limit - count)
                if page_index == 0:
                    payload = first_page
                else:
                    query = urlencode({"dataset": dataset_id, "config": config, "split": split,
                                       "offset": offset, "length": length})
                    payload = get_json(f"{API}/rows?{query}")
                batch = payload.get("rows", [])
                if not batch:
                    continue
                for item in batch:
                    record = dict(item.get("row", {}))
                    record["_provenance"] = {"dataset_id": dataset_id, "revision": revision,
                                             "license": license_name, "config": config, "split": split,
                                             "row_idx": item.get("row_idx")}
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
            # When records were requested in evenly spaced blocks, restore source row order.
            # Their row indices are preserved in provenance for traceability.
            f.flush()
        temp.replace(output)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return {"dataset_id": dataset_id, "revision": revision, "license": license_name,
            "reported_rows": total_rows, "sampling": "evenly spaced blocks", "config": config,
            "split": split, "rows_written": count, "output": str(output)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("dataset_id")
    p.add_argument("--config", default="default")
    p.add_argument("--split", default="train")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--allow-license-review", action="store_true", help="Acknowledge reviewing the dataset license/terms")
    a = p.parse_args()
    if not a.allow_license_review:
        p.error("review the dataset license and terms, then pass --allow-license-review")
    if not 1 <= a.limit <= 5000:
        p.error("limit must be between 1 and 5000 records")
    try:
        print(json.dumps(download_sample(a.dataset_id, a.config, a.split, a.limit, a.output), indent=2))
    except Exception as exc:
        raise SystemExit(f"bounded dataset-server retrieval failed: {exc}") from exc


if __name__ == "__main__":
    main()

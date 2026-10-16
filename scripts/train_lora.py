#!/usr/bin/env python3
"""Run a local-only MLX-LM LoRA job from reviewed prepared data."""
import argparse
import json
import fcntl
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, default=ROOT / "models/Qwen2.5-1.5B-Instruct-4bit")
    p.add_argument("--data", type=Path, default=ROOT / "data/processed/curated")
    p.add_argument("--adapter", type=Path, default=ROOT / "adapters/pilot")
    p.add_argument("--config", type=Path, default=ROOT / "configs/training.yaml")
    p.add_argument("--resume-adapter-file", type=Path, help="Resume from a saved adapter weights file; optimizer state is not restored")
    p.add_argument("--run", action="store_true", help="Actually start the short run; otherwise print the command")
    a = p.parse_args()
    if not a.model.is_dir():
        raise SystemExit(f"Local model is missing at {a.model}; run scripts/download_model.py only after approving its size")
    for split in ("train.jsonl", "valid.jsonl", "test.jsonl"):
        path = a.data / split
        if not path.is_file():
            raise SystemExit(f"Required {path} is missing")
        try:
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, ValueError) as exc:
            raise SystemExit(f"Could not read valid JSONL in {path}: {exc}") from exc
        if not rows:
            raise SystemExit(f"Required split is empty: {path}")
        if any(not isinstance(row, dict) or not isinstance(row.get("messages"), list) or not row["messages"] for row in rows):
            raise SystemExit(f"Training splits must contain non-empty messages arrays: {path}")
    if a.adapter.exists() and any(a.adapter.iterdir()):
        raise SystemExit(f"Refusing to overwrite existing adapter artifacts in {a.adapter}; choose a new --adapter directory")
    command = [sys.executable, "-m", "mlx_lm", "lora", "--train", "--model", str(a.model), "--data", str(a.data),
               "--adapter-path", str(a.adapter), "--config", str(a.config)]
    if a.resume_adapter_file:
        if not a.resume_adapter_file.is_file():
            raise SystemExit(f"Resume adapter file does not exist: {a.resume_adapter_file}")
        command += ["--resume-adapter-file", str(a.resume_adapter_file)]
    if not a.run:
        print("Dry run; add --run to start training:\n" + " ".join(command))
        return
    free_gib = shutil.disk_usage(ROOT).free / (1024 ** 3)
    if free_gib < 5:
        raise SystemExit(f"Only {free_gib:.1f} GiB free; refusing to start")
    lock_path = ROOT / "logs/training.lock"
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SystemExit("Another project training run holds logs/training.lock") from exc
        with (ROOT / "logs/training-pilot.log").open("a", encoding="utf-8") as log:
            log.write("\nStarting command: " + " ".join(command) + "\n")
            log.flush()
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            raise SystemExit(f"Training exited with status {result.returncode}; inspect logs/training-pilot.log")


if __name__ == "__main__":
    main()

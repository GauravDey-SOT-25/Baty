#!/usr/bin/env python3
"""Fetch the reviewed, pinned MLX model snapshot; no implicit download in app code."""
import argparse
from pathlib import Path

REPO = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
REVISION = "8b403126fc14f14cfc99bb4cfa72ecbc129ea677"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--confirm-model-download", action="store_true", help="Explicitly approve fetching the approx. 0.81 GiB weights")
    p.add_argument("--output", type=Path, default=Path("models/Qwen2.5-1.5B-Instruct-4bit"))
    a = p.parse_args()
    if not a.confirm_model_download:
        p.error("the pinned weights are about 0.81 GiB; pass --confirm-model-download after reviewing this size")
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=REPO, revision=REVISION, local_dir=str(a.output),
                      allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model"])
    print(f"Downloaded {REPO}@{REVISION} to {a.output}")


if __name__ == "__main__":
    main()

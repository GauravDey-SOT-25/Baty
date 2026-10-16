# Local Cybersecurity AI Platform

A local-first defensive cybersecurity assistant. See [`progress.md`](progress.md) for current status and exact blockers.

## Current state

The first local application baseline works. Message and URL checks are transparent, uncalibrated local triage. The local educational model adapter is wired to load only from an existing local directory and does not auto-download. Incident search currently uses a local JSONL corpus and lexical ranking; no incident corpus has been ingested. No third-party threat-intelligence request is made.

## Environment setup

This project was verified on macOS 27, arm64, Python 3.15. The reproducible project-local setup is:

```sh
./scripts/setup_env.sh
```

The script builds SentencePiece locally with project-local CMake and pybind11. It does not install system packages. Package and platform versions are recorded in `reports/environment.md`.

## Run

```sh
.venv/bin/python -m src.api.server
```

Open `http://127.0.0.1:8765`. The server binds to loopback only and does not log request bodies.

## Test

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The current unit tests cover message indicators, URL parsing, private/local IP rejection, deterministic split preparation, duplicate handling, and empty-corpus behavior.

## Data and training

Review dataset terms before using `scripts/download_datasets.py`. It requires a bounded record limit and an explicit license-review acknowledgment. Use `scripts/prepare_phishing.py` for classification data, `scripts/prepare_data.py` for instruction data, and `scripts/audit_data.py` for schema/duplicate reporting.

The pinned Qwen2.5 4-bit model is approximately 0.81 GiB. The model downloader requires `--confirm-model-download`; the app never downloads it automatically. After a local model and audited data are available, inspect the dry-run command:

```sh
.venv/bin/python scripts/train_lora.py
```

Start a bounded run only with `--run`. Current provisional settings are in `configs/training.yaml`; the MLX-LM CLI was verified, but the model has not yet been downloaded, loaded, trained, or evaluated. Adapter checkpoints do not currently demonstrate full optimizer-state recovery.

## Privacy and safety

Submitted URLs are parsed locally and never fetched, resolved, opened, or executed. The app does not send message content to external services. HTTPS and the absence of local syntax indicators do not establish that a site is safe. This tool is not a replacement for professional incident response.

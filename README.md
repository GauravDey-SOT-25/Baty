# Local Cybersecurity AI Platform

A local-first defensive triage and learning prototype for macOS. It combines message indicators, passive URL analysis, a local Qwen model, a local character n-gram URL classifier, and local lexical retrieval. See [progress.md](progress.md) and [reports/final-evaluation.md](reports/final-evaluation.md) for current limits and evaluation.

## What works

- Message analysis returns explainable heuristic indicators without a confidence score.
- URL checking normalizes the URL, rejects localhost/private/reserved addresses and embedded credentials, and returns syntax indicators plus an uncalibrated local classifier signal. It never resolves DNS, opens the URL, fetches redirects, downloads content, or calls a threat-intelligence service.
- The local model loads from `models/Qwen2.5-1.5B-Instruct-4bit` if present. It does not auto-download. The base model is imperfect; four of six focused safety questions produced materially unsafe/wrong answers. Verify its output.
- Local security-record search indexes 1,748 CISA KEV records, 30 CISA advisory RSS summaries, and 2,581 filtered records from one bounded Hacker News monthly shard. Ranking is lexical; HN posts are unverified discussion, not authoritative evidence.
- The loopback-only API and simple web UI run on `127.0.0.1:8765`. The app sends no user content to third parties and suppresses request-body logs.

## Environment setup

Verified on macOS 27, Apple M5 arm64, 16 GiB unified memory, Python 3.15.

```sh
./scripts/setup_env.sh
```

This uses project-local dependencies. No system-wide software is required. Details are in [reports/environment.md](reports/environment.md).

## Run the app

```sh
.venv/bin/python -m src.api.server
```

Open `http://127.0.0.1:8765`.

## Test

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Model and local inference

The pinned model is approximately 0.81 GiB and was downloaded after the user approved that download. In a fresh checkout, fetch it with:

```sh
.venv/bin/python scripts/download_model.py --confirm-model-download
```

The app will not download weights automatically. To use a specific local adapter for inference, set `CYBER_ADAPTER_PATH` when starting the app. The smoke adapter created in this project did not improve the held-out safety answers and is not selected by default.

## URL classifier data and evaluation

The selected URL dataset is [UCI PhiUSIIL](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset), licensed CC BY 4.0. Its 56.9 MB source CSV is in ignored `data/raw/`; only URL text and labels are used.

```sh
.venv/bin/python scripts/download_phiusiil.py
.venv/bin/python scripts/prepare_url_dataset.py
.venv/bin/python scripts/evaluate.py data/processed/phishing --output reports/url-baseline-results.json --save-model models/url-classifier.joblib
```

The evaluation split groups by approximate registrable domain. Its high held-out score is specific to a single dated source and does not indicate expected live accuracy. The model signal is uncalibrated and never constitutes a verdict.

## Local retrieval data

CISA source snapshots can be fetched and prepared locally:

```sh
.venv/bin/python scripts/download_kev.py
.venv/bin/python scripts/prepare_kev.py
.venv/bin/python scripts/download_advisories.py
.venv/bin/python scripts/prepare_advisories.py
.venv/bin/python scripts/build_retrieval.py
```

The Hacker News rows API currently fails with an upstream `CreateCommitError`. The project uses one pinned monthly Parquet shard rather than the reported 12.4 GB full archive:

```sh
.venv/bin/python scripts/download_hn_month.py 2026-08
.venv/bin/python scripts/prepare_hn.py data/raw/hacker-news-2026-08.parquet
.venv/bin/python scripts/build_retrieval.py
```

HN item IDs, authors, timestamps, parent/child IDs, scores and source links are retained. Community content is not treated as authoritative. User-provided URLs are never fetched.

## Training smoke run and recovery

The Trendyol and Heimdall instruction samples were excluded from training after spot review found quality concerns. `data/curated/defensive_seed.jsonl` contains 36 small, project-authored defensive examples only for verifying the local MLX path; it is not a production training set or a cybersecurity benchmark.

```sh
.venv/bin/python scripts/prepare_curated.py
.venv/bin/python scripts/train_lora.py --model models/Qwen2.5-1.5B-Instruct-4bit --data data/processed/curated --adapter adapters/new-run --config configs/training.yaml
```

That command is a dry run. Add `--run` to execute. The launcher refuses to overwrite an existing adapter directory. Resume adapter weights into a new output directory with `--resume-adapter-file path/to/checkpoint_adapters.safetensors`. MLX-LM does not restore optimizer or scheduler state from adapter weights; recovery is not an exact continuation of optimization.

## Privacy and safety

The app binds to loopback. Message content and user URLs remain local. The website checker is passive and makes no DNS, TLS, redirect, or reputation request. “No threat detected” and “no suspicious indicator” do not mean a site or message is safe. The model can hallucinate; do not use it as a replacement for incident-response professionals.

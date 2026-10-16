# Project progress

Updated: 2026-10-17 (Asia/Kolkata)

## Current state

- Phase 1 inspection is complete; see `reports/environment.md`.
- A local-only web app and deterministic data tools are implemented.
- Project-local MLX-LM/Datasets/scikit-learn dependencies are installed and the LoRA CLI help has been verified.
- A 1,000-row Apache-2.0 Trendyol sample was retrieved with row provenance, audited, and split. The approved pinned 4-bit model is now downloaded locally and one generation was verified. No training checkpoints exist.
- The model download is complete after user approval. Training remains blocked on content review: spot checks found factual errors and chain-of-thought style output in the Trendyol sample.

## Completed

- Inspected macOS 27.0.1, Apple M5 arm64, 16 GiB unified memory, 377 GiB available disk at first inspection, Python 3.15, Homebrew absence, Git version, memory pressure, active processes, existing Codex project/cache folders, and installed dependencies.
- Created persistent project instructions, decisions, reports, source layout, `.gitignore`, and local setup script.
- Installed MLX 0.32.4 / mlx-metal 0.32.4, MLX-LM 0.32.2, Transformers 5.20.1, Datasets 5.1.0, scikit-learn 1.9.1 in `.venv`. SentencePiece 0.2.2 compiled locally using project-local CMake 4.4.4 and pybind11 3.1.0. No system-wide software was installed.
- Verified `mlx_lm.lora --help`; Qwen2 is listed in the MLX-LM LoRA family documentation and the installed CLI exposes batch size, sequence length, number of layers, prompt masking, checkpoint save interval, adapter resume, and gradient checkpoint options.
- Confirmed Qwen2.5-1.5B-Instruct source card: Apache-2.0, 1.54B params, 28 layers, 32,768 context. Current preferred local artifact is the pinned MLX 4-bit conversion.
- Retrieved 1,000 rows via HF datasets-server API for Trendyol revision `357544e7576607d88eaeac9b0adb07e9fd8bb2bb`; raw file `data/raw/trendyol-instructions-1000.jsonl` is ignored by Git. Sample had required fields, zero malformed rows, zero exact duplicate full rows, 998 unique prompts, and two conflicting-prompt groups (four excluded records).
- Prepared chat-formatted data with source IDs, source revision, license, exact duplicate prompt exclusion, deterministic split, and recorded escaped-newline normalization. Counts: 796 train, 100 validation, 100 test.
- Implemented loopback-only UI/API, explainable message indicators, passive URL syntax analysis, local-only no-auto-download model loader, lexical incident search over a local JSONL corpus, bounded HF rows API fetcher, data preparation/audit scripts, LoRA launch wrapper, and TF-IDF character n-gram/logistic-regression evaluator.
- Inspected phishing dataset candidate metadata and found material discrepancies: no declared license; schema differs (`label` vs card `labels`); repository split metadata 120k/20k/60k conflicts with card email/URL claims. It is not used.
- Identified the PhreshPhish CC BY 4.0 candidate as 36.6 GB with large HTML cells; no bulk download. No HN archive downloaded (card reports 12.4 GB).

## Current branch / commit

- Git baseline commit created after source review and 14 passing unit tests. Large datasets, virtual environments, models, adapters, and checkpoints remain ignored.

## Model and training state

- Candidate base: `mlx-community/Qwen2.5-1.5B-Instruct-4bit`, repo revision `8b403126fc14f14cfc99bb4cfa72ecbc129ea677`, weight file 868,628,559 bytes.
- MLX Metal GPU is available. Local model load and one generation through the app loader succeeded. Forward/backward, adapter save/load, and recovery remain unverified.
- Training config: `configs/training.yaml`, batch 1, 512 token cap, four LoRA layers, short 20-iteration pilot, periodic adapter saves.
- No training has run; no adapters or checkpoints exist; no training process is active. The data sample is not approved for training after spot review found factuality and chain-of-thought quality issues.

## Tests and commands

- `.venv/bin/python -m unittest discover -s tests -v`: 14 tests passed on 2026-10-17.
- App smoke check: `GET /api/health` returned 200; message analysis returned evidence; localhost URL was rejected. App runs with `python -m src.api.server` on `127.0.0.1:8765`.
- Synthetic evaluator smoke check: 24 generated training and 6 generated test examples passed through TF-IDF/logistic regression. These are code-path checks, not model-quality metrics.
- `mlx_lm.lora --help` succeeded. The installed CLI was not used for training.

## Next steps

1. Curate or select an appropriately reviewed instruction set before adapter training; the current sample is unsuitable based on spot review.
2. Run a tiny forward/backward/adapter save-load pilot on reviewed data, then verify checkpoint recovery.
3. Do not train on the current Trendyol sample: spot review found technical errors and chain-of-thought style content. Curate or select an appropriately reviewed instruction set before adapter training.
4. Resolve a clearly licensed, documented phishing/URL dataset and evaluate classifiers on genuinely held-out data; do not use the unresolved `cybersectony` candidate.
5. Build retrieval from selective HN/security advisories, add evidence citation checks, complete UI/API and full evaluation, and document remaining limitations.

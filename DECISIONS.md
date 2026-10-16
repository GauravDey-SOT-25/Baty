# Decisions

## 2026-10-17 — Begin with inspection and a modular baseline

- Record the actual environment before installing or downloading.
- Start with deterministic, explainable local heuristics for messages and passive URL parsing; reserve learned classification for audited, split datasets and measured baselines.
- Do not fetch submitted URLs or perform DNS/network inspection by default. This avoids SSRF and privacy risk while the application is still local and untrusted-input handling is being established.
- Treat an MLX LoRA run as unverified until the installed MLX-LM version, model architecture, training mode, CLI, and checkpoint semantics have all been checked.
- Use project-local dependencies only after confirming a compatible interpreter. Current system Python 3.15 is not presumed compatible.
- Stream/select records from Hacker News; never download its full 12.4 GB mirror by default.

## 2026-10-17 — Select bounded Trendyol sample, hold phishing candidate

- Retrieved 1,000 spaced rows from the Apache-2.0 Trendyol dataset via the HF datasets-server API rather than its full 195 MB file. Preserve raw JSONL and metadata.
- Convert literal backslash-n formatting to line breaks only in processed examples and record counts; raw examples remain unchanged.
- Exclude every exact duplicated prompt group with conflicting answers. The resulting fixed split is 796/100/100.
- Do not use `cybersectony/PhishingEmailDetectionv2.0`: repository card has no license declaration and its viewer schema/split metadata conflict with narrative class/schema claims.
- Do not download PhreshPhish wholesale: its 36.6 GB Parquet payload contains huge HTML fields despite potentially useful URL/label fields.
- Model download requires a user response because the pinned weight artifact is about 0.81 GiB and the project brief explicitly asks approval for large downloads.

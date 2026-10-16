# Final evaluation and current project state

Updated: 2026-10-17.

## Verified working

- The pinned local MLX Qwen2.5-1.5B-Instruct-4bit model loaded and generated locally. Its exact weight file is 868,628,559 bytes. The app performs no automatic model download.
- A project-authored 24/6/6 defensive seed dataset was used for an 8-iteration, 2-layer LoRA/QLoRA smoke run. MLX-LM wrote `adapters/curated-smoke/adapters.safetensors` and periodic adapter checkpoints. These large artifacts are ignored by Git.
- The smoke adapter loaded for inference. Qualitative comparison on six held-out questions found no material improvement. It is deliberately not selected by the app.
- Interruption/recovery was exercised: the 50-iteration pilot was interrupted after iteration 6, at `adapters/interruption-test/0000006_adapters.safetensors`; MLX-LM resumed from those adapter weights in a separate one-iteration run and saved a new adapter.
- Recovery restores adapter weights only. MLX-LM did not restore optimizer or scheduler state; this is not exact training-state continuation.
- The URL classifier completed a held-out evaluation on an approximate registrable-domain split. Full precision, recall, F1, confusion matrix and the major single-source generalization caveat are in `baseline-results.md` and `url-baseline-results.json`.
- Local retrieval searches 1,748 CISA KEV entries, 30 CISA advisory RSS records, and 2,581 Hacker News stories/comments from a single month. Source links and provenance are retained. HN matches are clearly marked as community discussion.
- The local UI has four tabs; the backend binds only to `127.0.0.1`, enforces JSON content type and same-origin browser requests, caps body and field sizes, and suppresses request-body logging. URL analysis never resolves, opens, or fetches submitted URLs.
- `.venv/bin/python -m unittest discover -s tests -v`: 26 tests passed, covering API routes/validation, UI script wiring and CSP, URL normalization/SSRF-oriented rejection/no DNS, dataset splitting/redaction/provenance, HN data preparation, retrieval attribution, and deterministic instruction prep.

## Important quality limits

- The base LLM failed four of six small, hand-written safety questions. The smoke adapter did not correct them. The app should not be relied on for incident-response decisions without human verification. This result is documented with exact generations in `assistant-base-review.jsonl` and `assistant-adapter-review.jsonl`.
- Trendyol and Heimdall samples were excluded from training after spot checks found reliability concerns. The adapter was trained only on 24 short project-authored examples to exercise the runtime; it is not a useful domain-specialized release.
- The URL model result is from one dated source. Its 99.55% accuracy is not a real-world claim. Registrable-domain grouping approximates common public suffixes rather than using the full Public Suffix List; unseen suffixes could permit leakage.
- The message detector is a rule baseline and has no supervised evaluation or calibrated confidence.
- Retrieval uses lexical matching, not a sentence embedding model or FAISS. The 2026-08 HN sample can be incomplete and stale. The full HN archive and other large HTML datasets were not downloaded.
- Live DNS/WHOIS/TLS/reputation checks and external threat-intelligence APIs are not implemented. Results clearly state these checks were unavailable; the app sends no user content to third parties.
- UI was verified through its CSP/script/API wiring tests and live HTTP API smoke tests. A real graphical browser test could not be run because the available CUA runtime failed to start.

## Not ready for unattended use

The app is a local prototype and defensive triage aid. The generated model can be confidently wrong; the classifier is uncalibrated; search results are not a complete incident history; and no external reputation check is performed. A human should verify technical advice and findings before acting.

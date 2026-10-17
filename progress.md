# Project progress

## 2026-10-17 — Cyber Desk UI refresh

- Reworked the local web UI into a responsive application shell with persistent tool navigation, runtime/account status, clearer typography, accessible focus states, mobile navigation, and consistent input/result styling.
- Kept the existing message, URL, assistant, OCR, local incident search, Parallel research panels, Firebase account/sync controls, and all endpoint payloads. Updated tab switching for the new workspace container and connected the header account shortcut.
- Verification: UI tests 2/2 passed; API tests 12/12 passed; served page contains the new shell and preserved feature controls; `git diff --check` passed. The server serves the updated page at `http://localhost:8765`.

## 2026-10-17 — Firebase live configuration check

- Confirmed the public Firebase project configuration authorizes `localhost`; the local app now runs at that origin for Google sign-in. Added visible Firebase error codes for diagnosing provider, auth, or database-rule failures.
- Confirmed an unauthenticated request to the Realtime Database rules endpoint is denied (HTTP 403), so no user data was read. This does not prove that the desired UID-scoped application rules are deployed.
- Firebase CLI and gcloud are not installed, and no Firebase admin session is available to inspect or change provider/rules settings. Opened the project's Authentication provider and Realtime Database Rules console pages for the signed-in project owner.
- Verification: Firebase integration tests 3/3 passed; API tests 12/12 passed; Python compilation and `git diff --check` passed. A completed Google OAuth login and authenticated database write/read remain unverified.

## 2026-10-17 — Google sign-in local host compatibility

- Checked the live Firebase public project configuration: its authorized domains include `localhost` but not `127.0.0.1`. Because Firebase checks the browser hostname, the original app URL could not complete Google sign-in while using `127.0.0.1`.
- Allowed the exact `localhost:<port>` Host header in addition to `127.0.0.1:<port>` while retaining the loopback-only bind and exact Host allowlist. Updated Firebase setup notes and added an API regression test.
- Ran `python -m unittest discover -s tests -p 'test_api.py' -v`: 12 tests passed. Python compilation and `git diff --check` passed. Restarted the local server and opened `http://localhost:8765` in the Codex browser.
- Google provider enablement and a real user OAuth consent/login have not been observed. The sign-in flow can now be attempted from the already-authorized `localhost` origin if the Google provider is enabled in the Firebase project.

## 2026-10-17 — Local OCR input for the assistant

- Added a macOS Vision OCR helper and browser upload/review flow. Recognized text can be explicitly inserted into the assistant's existing text prompt; this adds image text preprocessing, not visual inference or retraining of Qwen.
- Added local API validation: image signatures are checked, uploads are capped at 4 MiB, Vision rejects images over 24 megapixels, temporary files are owner-only and removed after OCR, and the Swift executable is built into ignored `work/local-ocr/` on first use.
- Modal remains opt-in. The image stays local; when the user chooses Modal, the question including any inserted OCR text is sent there. No live requests or API costs were used for this change.
- Swift Vision/ImageIO framework typechecking and optimized helper compilation succeeded. Python source compilation (`py_compile`) and `git diff --check` succeeded. Node.js is unavailable in this environment, so frontend JavaScript syntax checks were not run; no formal test suite was run for this feature. Restarted the pre-existing local server; `/ocr.js` returned HTTP 200, health reported local runtime available, and malformed OCR input was rejected with HTTP 400.

## 2026-10-17 — Prepared authenticated Modal inference preview

- Added `deploy/modal_app.py` as a separate remote CPU-only Qwen inference service. It uses public `Qwen/Qwen2.5-1.5B-Instruct` at pinned revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, caches weights in a named Modal Volume, requires proxy auth, caps request/generation sizes and max containers, and logs no prompt content.
- It intentionally excludes the local MLX model, LoRA adapter, CISA/HN corpus, training/evaluation data, user state, and `.env`; local user requests would leave the laptop if sent to the endpoint. This is only an inference preview, not a full app migration or production deployment.
- Installed Modal CLI 1.6.2 in ignored `work/modal-cli-venv`; source import and deploy CLI help passed. `modal token info` found no configured Modal authentication. `modal setup` has opened the account authentication flow and is waiting for completion; no deployment, model download, cloud request, or volume creation has occurred.
- Local verification: 82 tests run, 79 passed, 3 optional live tests skipped; compileall, `git diff --check`, and `pip check` passed.

## 2026-10-17 — Local API resource limits

- Added a bounded 32-worker HTTP server, 15-second client socket timeout, strict single Host/Content-Length handling, rejected Transfer-Encoding, fixed 32 KiB body ceiling, and loopback-client API request limits (12/minute assistant, 60/minute incident search, 120/minute other API). This is not authentication and does not permit remote exposure.
- Health now checks model config, tokenizer and safetensors presence instead of directory existence. Added API regressions for incomplete model directories, rate-limit responses, transfer encoding and worker configuration.
- Verification: `.venv/bin/python -m unittest discover -s tests -q` ran 78 tests, 75 passed, 3 optional billable live tests skipped; compileall, `git diff --check`, and `pip check` passed. No live service request, training, weight changes, or commits.

## 2026-10-17 — Retrieval evaluation and readiness continuation

- Added `docs/evaluation.md`, an offline 25-case CISA KEV/advisory retrieval benchmark, evaluator, and prompt-overlap audit across the local 796/100/100 instruction splits. The original 40-example evaluation dataset remains unchanged. No prompt overlaps met the exact/0.80 3-gram Jaccard threshold; this does not rule out paraphrase leakage.
- Added a 0.60 minimum query coverage condition after the full suite revealed that “Cisco security vulnerabilities” still matched on “Cisco” alone. Also restored source labels from recognized CISA/HN record types when source metadata is absent; no publisher is inferred from arbitrary URLs.
- Reproduced benchmark: retrieval P/R/F1 0.944/1.000/0.971 (17 TP, 1 strict FP); negative abstention 8/8; source URL attribution 17/17; missing-CVE wrapper abstention 1/1. The one false positive is a second PAN-OS injection KEV record; label judgment remains for independent review.
- Diagnosis remains: raw Qwen QA 2/8 and LoRA QA 1/8 by subjective rubric; wrapper 8/8 due mostly to deterministic guardrails; message FPR 87.5%, URL FPR 75% on eight benign examples each. No basis for fine-tuning or production claims.
- Final verification: `.venv/bin/python -m unittest discover -s tests -q` ran 74 tests, 71 passed, 3 optional billable live tests skipped; compileall, `git diff --check`, and `pip check` passed. No live Parallel calls, training, weight changes, or commits.

Updated: 2026-10-17 (Asia/Kolkata)

## 2026-10-17 — Comfest main site integration

- The extracted `../Comfest - 26/index.html` now serves as the local app homepage. The previous Cyber Desk UI and its full Parallel/Firebase workflows remain available at `/workspace`.
- Embedded the existing local URL check, message analysis, Qwen Q&A, local record search, OCR, and private trust-note tools directly into the Comfest homepage. Provider-backed web research remains explicitly user-triggered in the secondary workspace.
- Removed external font/video dependencies from the Comfest hero; updated misleading prototype marketing copy and added route/static asset checks. No model/training artifacts or credentials changed and no live providers were contacted.
- Verification: `.venv/bin/python -m unittest discover -s tests -q` ran 113 tests (110 passed, 3 optional live tests skipped); `.venv/bin/python -m compileall -q src tests scripts` and `git diff --check` passed. Live checks returned HTTP 200 for `/`, `/workspace`, the main CSS/JS, and the local hero image; health reported local model/runtime available. An HTML audit found 60 unique IDs and no missing referenced images. No live provider request, model/data/credential change, or commit was made.

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

## 2026-10-17 completion update

- Downloaded the pinned MLX Qwen2.5-1.5B-Instruct 4-bit model after the user approved it; exact weight size 868,628,559 bytes. Local inference verified.
- Built a loopback-only local app with message triage, passive URL analysis, local incident retrieval, and a learning assistant. Submitted URLs are never fetched or resolved.
- Created a local retrieval corpus from CISA KEV/advisories and one pinned August 2026 Hacker News shard; each source retains provenance. HN remains anecdotal.
- Built a documented URL classifier baseline on the licensed UCI PhiUSIIL dataset with a grouped train/validation/test split. Test accuracy 99.55%, macro F1 99.48%; these are single-dataset results and not production guarantees.
- Ran an 8-iteration LoRA smoke training on 36 manually written defensive examples and tested resume from a saved adapter. The adapter did not materially improve held-out answers and remains disabled in the app.
- Replaced generated summaries of retrieved records with deterministic source-field answers. Explicit CVE queries now retain only records naming that CVE, preventing unrelated lexical matches from being presented as its answer. Added deterministic defensive responses for prompt injection, unsafe URL opening, HTTPS trust assumptions, weak message signals, and evidence destruction.
- Latest verification: `.venv/bin/python -m unittest discover -s tests -q` passed 29 tests. An actual local query for CVE-2026-102764 returned only the matching CISA KEV record and its source link.
- Known limits: the base model can still produce unsafe or inaccurate free-form answers for other questions. The message heuristic is not a calibrated detector; URL scores are not a safe verdict; retrieval is lexical and snapshot-based. Do not rely on this app for autonomous response or production security decisions. Browser GUI automation could not be verified in this environment.

## 2026-10-17 — Web research integration review and verification

- Verified `b7aa8d6` exists on branch `main`. The local model and ignored adapter/checkpoint artifacts remain present. Existing working-tree research changes from the shared workspace were inspected and preserved; Antigravity is running, but no model training or app server process was found.
- Confirmed no Firebase implementation and no `PARALLEL_API_KEY` configured. No live Parallel request was made.
- Reviewed the pre-existing research module and corrected contract/security defects: Search no longer sends unsupported `max_results`; task polling is non-blocking and reads the documented separate `/result` resource; queued task state is mapped; Monitor create uses `event_stream`/frequency/settings and cancellation uses the documented POST route; Monitor Events are surfaced on demand.
- Added structured public-record enrichment using the documented Task API JSON schema and per-field citation basis. Input accepts only explicitly named public record fields; private message content is rejected.
- Added per-client research route rate limits, URL input checks, shared local saved-task visibility, and explicit UI disclosure about submitted fields and possible provider charges. Firebase was not introduced; local task/monitor history remains shared because identity/auth is not configured.
- Fixed the CSP violation from inline research tab handlers and removed HTML injection sinks from provider/user text display.
- Corrected research task storage root so ignored JSON data is stored in this project’s `data/`, not the parent directory.
- Latest verification: `.venv/bin/python -m unittest discover -s tests -v` passed 47 tests; `git diff --check` and Python compile checks passed. An in-process loopback server test confirmed no-key local Search fallback and status.
- Remaining capability boundaries: provider-side URL DNS/redirect protections cannot be independently verified from this app; dedicated Parallel beta FindAll is not wired (Search offers report discovery); there is no Firebase/authenticated multi-user ownership; no live provider API test was run. Keep the app loopback-only. No files were committed so the existing shared working-tree changes are preserved for coordination.

## 2026-10-17 — Research security and live-test readiness

- Reconfirmed 47 baseline tests, clean `git diff --check`, Python compile success, branch `main`, no configured `PARALLEL_API_KEY`, and no local app server or model training process. Antigravity remained active; shared changes were preserved.
- Added SSRF regression coverage for private IPv4/IPv6, IPv4-mapped IPv6, legacy numeric IPv4 spellings, percent-encoded hosts, malformed ports, and oversized URLs. The local guard rejects ambiguous numeric IP hosts; this does not validate provider-side DNS or redirects.
- Research task and monitor JSON now save by atomic replacement with mode `0600` on POSIX. Automatic expiration and account deletion are not implemented; data remains until manually removed.
- Added a separate billable live-check suite gated by both `PARALLEL_API_KEY` and `PARALLEL_LIVE_TESTS=1`. It covers Search, a public CISA Extract target, and Task create/status. The suite is intentionally not run without credentials and deliberate opt-in.
- Documentation states that Firebase/authentication and verified ownership are absent; this is still an unauthenticated loopback-only prototype with shared local records. No model artifacts were touched.
- Final verification: `.venv/bin/python -m unittest discover -s tests -q` ran 56 tests (53 passed, 3 live provider tests skipped); explicit live-test discovery without credentials skipped all 3. `git diff --check` and `.venv/bin/python -m compileall -q src tests` passed.
- Rechecked current official Parallel Search, Extract, Task Run create/status/result, Monitor create/events/cancel, and pricing docs. Request shapes match the adapter. Current published pricing is variable by API processor/operation; the README links the official pricing page. No live request was made because the key is absent.
- The working tree remains uncommitted and includes all prior shared research implementation changes plus this milestone's focused URL, persistence, tests, and documentation updates. No reset/clean/checkout or model artifact operation was used.

## 2026-10-17 — Project health, model check, and evaluation baseline

- Current baseline: 59 tests run, 56 passed, 3 opt-in live tests skipped. Python compilation and `git diff --check` passed. The README startup command launched the app; `/api/health` returned `ok` and research status showed local mode/no key. The temporary local server was stopped.
- Local base model was verified at `models/Qwen2.5-1.5B-Instruct-4bit` (repo `mlx-community/Qwen2.5-1.5B-Instruct-4bit`, pinned revision `8b403126fc14f14cfc99bb4cfa72ecbc129ea677`, 868,628,559 bytes). MLX 0.32.4 / MLX-LM 0.32.2 generated a response with adapter loading disabled. The default app adapter path `adapters/best` has no adapter file; four smoke/recovery adapter directories remain present.
- Training evidence in `logs/training-pilot.log` records the curated LoRA smoke run completing iteration 8/8, plus a one-iteration adapter-weight recovery run. The separate interruption run stopped at iteration 9/50. This is a completed smoke fine-tune, not a useful cybersecurity model; the adapter is not selected by default and prior held-out review found no material benefit.
- Added the fixed, project-authored, evaluation-only 40-item suite `data/evaluation/cyber_eval_v1.jsonl` plus runner `scripts/evaluate_cyber_eval.py`. It includes messages, URL strings, Q&A rubrics; URL text is never resolved/fetched and no evaluation case is used for training.
- Recorded diagnostic metrics in `reports/cyber-eval-v1.json`: message-rule F1 69.6%, FPR 87.5%; URL model/static guard F1 72.7%, FPR 75.0%; base Q&A 2/8 correct and app wrapper 6/8 by single-pass manual review (`reports/cyber-eval-v1-review.json`). Two app failures come from irrelevant lexical retrieval matches. Small synthetic set; not production estimates.
- No Parallel key or `.env` is configured. `.env` is ignored; `.env.example` is placeholder-only. SDK packages are not installed; current adapter uses standard-library REST. Official docs were rechecked; no request format changed. No live Search or other paid API call was made because both key configuration and explicit live-test approval are still gated.
- Fine-tuning is not recommended next: current errors need stronger abstention/retrieval controls and a broader reviewed evaluation first. No training or artifact changes were made.

## 2026-10-17 — Secure Parallel configuration and CSP-safe frontend links

- Verified key compromise handling: the previously exposed key is treated as compromised and never recovered, reused, or logged. `.gitignore` strictly ignores `.env`. `.env.example` contains only `PARALLEL_API_KEY=replace_with_your_key`.
- Pure stdlib configuration loader (`src/research/config.py`) securely parses `.env` without third-party dependencies, prevents credential leakage, and handles missing keys gracefully by falling back to local corpus.
- Upgraded `frontend/research.js` to render all public source URLs (search results, extraction outputs, deep research citations, monitor event sources, and enrichment reports) as clickable DOM links (`<a>`) with `target="_blank"`, `rel="noopener noreferrer"`, and protocol safety checks (`https://` / `http://`). Zero `innerHTML` is used, preserving strict Content Security Policy (CSP).
- Added regression test `test_research_links_are_safe_and_csp_compliant` in `tests/test_ui.py`. Full test suite now contains 57 tests: 54 passed in 3.5s, 3 billable live tests skipped pending replacement key configuration.
- `git diff --check` and Python compilation (`compileall`) passed with zero errors. No live billable requests made.

## 2026-10-17 — Retrieval relevance and evidence-aware abstention

- Reproduced the 40-example offline evaluation before changing behavior; message and URL results matched the saved baseline (message P/R/F1 53.3%/100%/69.6%, FPR 87.5%, accuracy 56.3%; URL 57.1%/100%/72.7%, FPR 75.0%, accuracy 62.5%). No URL was resolved/fetched and no live Parallel request was made.
- Replaced substring term counting with Unicode-normalized tokenization, field-weighted/corpus-rarity lexical scoring and a minimum relevance threshold. Weak matches now return no records. Retained IDs, URLs, source and date attribution.
- Added explicit answer-basis labels for local records, defensive guardrails, missing-evidence abstentions, and general unverified model responses. Current/product-specific evidence requests with no local result abstain. The evaluator now stores this basis.
- Added regressions for weak single-word matches, exact-CVE/source attribution, current-claim abstention, and source-free general education.
- Post-change same-set evaluation retained message and URL metrics unchanged. Manual QA rubric scores: raw base model 2/8; wrapper 8/8. The pre-change reproduction already scored 8/8 in the existing shared working tree; the saved report's wrapper 6/8 predates those guardrails, so this milestone has no measured QA-score gain. Results and this discrepancy are documented in `reports/cyber-eval-v1-after.json`, `reports/cyber-eval-v1-after-review.json`, and `reports/final-evaluation.md`.
- Final verification: `.venv/bin/python -m unittest discover -s tests -q` passed 63 tests, 3 opt-in live tests skipped; `.venv/bin/python -m compileall -q src tests scripts` passed; `git diff --check` passed. One suite attempt overlapped model evaluation and timed out; the sequential rerun passed.
- No model weights, datasets, training artifacts, external API calls, or commits were changed/made.

## 2026-10-17 — User-requested Trendyol fine-tune

- Verified the M5 (16 GiB), local MLX 0.32.4 / MLX-LM 0.32.2 environment, the already installed pinned Qwen2.5-1.5B-Instruct 4-bit conversion, and the local Trendyol sample/splits. The official full-precision Qwen repo was not downloaded; the model family was already present as the local MLX conversion.
- Fixed the chat-data audit helper, which had not been reading `messages` arrays correctly. True audit results for prepared train/valid/test: 25/4/1 reasoning phrases and 57/8/9 placeholder phrases. Training-copy preparation excluded 95 unique train rows (33 reasoning-artifact matches, 57 placeholder matches, 10 harmful-action prompt matches with overlap) and retained 701; valid/test remained unchanged. Manifest records source SHA-256 and exclusions.
- Completed local LoRA training: 701 steps, batch 1, 2 layers, rank 8, 512-token cap, 0.659M parameters; adapter saved under `adapters/trendyol-m5-experiment`. MLX test run completed on the 100-row held-out split.
- Comparable test loss/perplexity: base 3.119 / 22.615; adapter 1.809 / 6.105. The adapter loaded successfully for paired inference. The small QA rubric check scored raw base 2/8 and adapter 1/8; the adapter invented a patch version and incorrectly treated HTTPS/certificate as legitimacy proof. Subjective review is not independent. Keep the adapter disabled.
- Documentation/results: `reports/trendyol-m5-training.md`, `reports/trendyol-m5-qa-comparison-256.json`, `reports/trendyol-m5-qa-review.json`, `logs/trendyol-m5-training.log`.

## 2026-10-17 — Deployment readiness hardening

- Local assistant UI now surfaces model/runtime and adapter state and lets users explicitly include local record evidence; generic questions default to model inference, while explicit CVE and current/product-specific claims still retrieve or abstain.
- Added an MLX repetition penalty (1.08, 128-token context). A local smoke answer became less repetitive; factuality is still unverified.
- Ran the 40-example fixed evaluation to a new report. Classifier metrics stayed unchanged (message FPR 87.5%, URL FPR 75%); the existing guardrail wrapper matched 8/8 rubric expectations on this small, subjective QA subset. Raw base Q&A remains error-prone, and the Trendyol adapter remains disabled.
- Verification: 65 tests passed, 3 optional live tests skipped; Python compilation and diff check passed. No live calls, training, weight changes, or commits.
- Readiness remains limited to supervised localhost demos; not ready for production security decisions. See `reports/deployment-readiness.md`.
- Additional production-hardening review against current NIST SSDF / OWASP ASVS / OWASP GenAI references found and fixed a DNS-rebinding Host validation gap. Server construction now enforces 127.0.0.1-only binding; 2 regression tests added. Dependency `pip check` is clean; pip-audit is unavailable in the existing environment.
- Follow-up dependency audit: isolated `pip-audit 2.10.1` scans of `requirements.txt` and the local `.venv` reported no known vulnerabilities; `pip check` passed. This is not a guarantee or a full supply-chain attestation.


## 2026-10-17 — Modal post preparation

- Added `deploy/post_to_modal.sh` to check that the project-local Modal SDK exists and the CLI is signed in (credential output is suppressed), then deploy the protected preview.
- Modal now creates `cyber-qwen-hf-cache` on first deployment. The local machine's model, adapter, data, and `.env` remain excluded; only public model weights are fetched by the remote container after deployment.
- Dependency resolver dry run passed for Linux x86_64 / CPython 3.12 with pinned Torch 2.14.1, Transformers 5.20.1 and FastAPI 0.143.3; no package artifacts were downloaded.
- Modal authentication became available. Deployed the protected CPU preview and verified an authenticated health response plus one benign model inference. A temporary proxy token was deleted after testing.
- Observation: first health/startup took 37.7 seconds; the canary used 30.6 seconds of CPU inference and hit its 96-token cap before completing. It returned HTTP 200 and the unverified-answer marker.
- First image build tried to pull CUDA dependencies despite CPU configuration; aborted before saving, then switched to official CPU-only PyTorch wheel. Successful image used no CUDA packages.
- Final verification: 86 tests ran; 83 passed and 3 optional live tests skipped. Python compileall, shell syntax, `git diff --check`, and `pip check` passed.


## 2026-10-17 — Firebase sign-in and optional assistant backup

- Added Firebase JS SDK web client wiring for Google sign-in/out and Realtime Database, plus a hidden-by-default Account & sync panel. Local app functions remain available while signed out.
- Cloud writes are unchecked by default and require sign-in plus user opt-in. Only future Learning assistant question/answer/answer-basis exchanges are stored in the signed-in user's history. Other user-provided content is excluded. Added per-user delete action and rules that deny root access, scope reads/writes to matching Firebase UID, validate field bounds and cap history at 200 entries.
- Updated server CSP and static module route, README privacy/setup summary, `docs/firebase-auth-and-sync.md`, and static/HTTP regression tests.
- Firebase Console Google provider, authorized domains, live RTDB availability/rules, and sign-in flow could not be inspected or verified here. Firebase CLI is absent; no remote rules were deployed. Do not use cloud sync until the Console steps are complete and reviewed.
- No model, training data, weights, adapters, or Modal deployment were changed. No external login, Firebase write, live Parallel request, or API-cost action was made.


## 2026-10-17 — Firebase-authenticated Modal inference

- Added a distinct unchecked UI option for cloud Qwen inference. The normal local model remains the default. Cloud question submission sends only the question and Firebase ID token to the loopback API; local retrieval is not attached. The existing separate checkbox controls whether assistant Q&A is also copied into RTDB.
- The loopback API relays to the fixed Modal URL and keeps the Modal Proxy Token in ignored owner-only `.env` (`0600`). Created dedicated token `cyber-qwen-firebase-local-relay`; secret values are not logged, printed, or added to Git.
- Modal keeps edge proxy authentication and additionally verifies the Firebase JWT signature with Google's Firebase certs, audience/project, issuer, UID, Google sign-in provider, and verified-email claim. Rate limit: 3 valid requests per UID per minute. No Firebase Admin/service-account key is used.
- Deployed `cyber-qwen-modal-preview` with pinned `google-auth==2.62.0`; image packages include the local `deploy` source explicitly. A first build attempt with the optional `google-auth[requests]` extra failed dependency resolution against Modal's CPU package index; removing the extra allowed a successful build.
- Live checks: Modal `/health` returned HTTP 200 with model revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`; the final deployed endpoint returned HTTP 401 for an invalid Firebase token. The loopback relay was also exercised end-to-end and propagated that 401 using verified TLS. No valid user token was available here, so Google sign-in and successful authenticated generation remain unverified. Firebase Console Google-provider/domain setup is still required.
- Final verification: 94 tests passed, 3 optional live tests skipped; Python compilation, JavaScript syntax, `git diff --check`, and `pip check` passed.
- No model weights, adapters, training data, or RTDB rules were changed.
## 2026-10-17 — Parallel Responses quick-answer workflow

- Added an opt-in Quick answer research tab backed by Parallel Responses (`POST /v1/responses`) using the documented Bearer API key header and selectable low/medium/high reasoning effort.
- Added citation annotation parsing, URL scheme filtering and deduplication; rendered answers and provider annotations with text nodes/safe links. Disclosed that question text is sent to Parallel and may incur charges; no live provider request was made.
- Added local service validation and a 12-per-minute endpoint-specific rate limit. Timeout is 120 seconds, matching provider guidance for high-effort requests.
- Added mocked provider/service tests and UI contract assertions. Covered in the full 102-test offline suite below; no live Parallel call was made.


## 2026-10-17 — Parallel-style research landing and FindAll

- Reworked the default screen into a responsive security research landing/playground modeled on Parallel's product structure while keeping Cyber Desk branding and the separate local AI/security tools.
- Added the sixth Parallel workflow, FindAll: objective-to-schema ingestion, editable criteria, user-started Preview/Base/Core/Pro run, status polling, candidate snapshots, and safely rendered source links. Added local input checks and per-client rate limits.
- The Responses API quick-answer panel is also present with low/medium/high effort and cited source annotations. Live provider actions remain explicit; no billable request was made.
- Official API contracts reviewed from Parallel documentation on 2026-10-17. Verification: full suite ran 102 tests (99 passed, 3 optional live tests skipped); Python compileall, HTML parsing with 95 unique IDs, and `git diff --check` passed. Node/Bun/Deno are unavailable, so standalone JavaScript syntax checking could not run. Local health/UI/research status endpoints returned HTTP 200; local Responses and FindAll requests returned the expected missing-key message without making an external call. No Parallel key is configured and no live request was made.

## 2026-10-17 — Responsive layouts across screen sizes

- Added a separate responsive stylesheet for the landing page and in-app tools, with fluid wide-screen sizing and layout changes for tablet, phone, and narrow 280px viewports.
- Kept the tool navigation available as a sticky, horizontally scrollable touch bar on smaller screens; reflowed research controls/cards; enabled safe text wrapping and bounded result panes; increased touch target sizing and visible keyboard focus.
- Added a same-origin stylesheet route, consistent with the app's CSP. Verification: Python compilation and `git diff --check` passed; `/responsive.css` and `/` both returned HTTP 200 from the restarted local server. Responsive breakpoints cover 280px and larger, plus reduced-motion preferences.

## 2026-10-17 — Responsive layout follow-up

- Diagnosed why the prior responsive pass still felt fixed: it depended mainly on viewport breakpoints, retained a global 280px minimum width, and forced the landing headline onto a line that can exceed a narrow phone's content area.
- Reworked `frontend/responsive.css` to use intrinsic fluid grids and a content-width container query for the workspace, removed the page minimum width, adjusted the mobile headline to wrap naturally, and made long inputs, result panes, cards, and research tabs shrink or scroll within their own bounds.
- Headless Chrome exposed a desktop landing bug: the hidden sidebar left its first grid column reserved, squeezing the landing page into a narrow strip. Made the landing shell block-level at all viewport widths.
- Verified with Chrome DevTools at 17 landing widths from 240px through 1920px and all six workspace views at nine widths from 240px through 1920px: document and body widths matched each viewport with no horizontal page overflow. Screenshot-reviewed landing at 320px, 768px and 1440px, plus assistant/research views at 320px, 768px and 1440px. The local app serves the current files with HTTP 200 and `Cache-Control: no-store`; `git diff --check` passes.

## 2026-10-17 — Unified workspace views with the Overview visual style

- Applied the Overview's warm neutral canvas, restrained borders, editorial heading scale, rounded panels, form fields, and dark primary actions to all six tool views while retaining Cyber Desk branding and existing workflows.
- Changed compact navigation to wrap below 1,100px and removed the duplicate Account & sync shortcut from the page header. This fixes hidden/clipped navigation links at phone and mid-size desktop widths.
- Verified the landing view and all six tool views in headless Google Chrome using Chrome DevTools Protocol across 12 viewport widths (240, 280, 320, 390, 600, 768, 900, 1,024, 1,100, 1,200, 1,440, and 1,920px): 84 combinations, no page/document horizontal overflow, all tool sections inside viewport bounds, and correct active nav state. Reviewed screenshots at 320, 1,024, and 1,440px (`/tmp/cyberdesk-verified-*.png`). No project test suite was run for this styling-only change.

## 2026-10-17 — Parallel API key configured locally

- Saved the user-provided Parallel key in the Git-ignored `.env` file, preserving existing entries and retaining owner-only mode `0600`. The key is not in tracked source, browser code, or logs.
- Restarted the local app. `GET /api/research/status` reports provider `parallel`, `api_key_configured: true`, `is_available: true`, and mode `live-web`.
- No live Parallel request was made; verification used only the local status endpoint and did not incur provider usage.

## 2026-10-17 — Comfest URL Trust prototype integration

- Added a URL Trust workspace with a local domain-hash lookup, a user-maintained persistent ledger, record update/revocation, and source-neutral status labels.
- Added optional TLS certificate observation with explicit UI consent, public-DNS-address checks, direct-IP connection on HTTPS port 443, certificate validation and fingerprint output. The inspector sends no HTTP request or follows redirects.
- Added optional Google Safe Browsing and VirusTotal domain-root checks. They require per-check UI consent and locally supplied environment keys; submitted URL paths and query strings are stripped. No provider request was made.
- Reviewed the archive and excluded its embedded provider credentials, permissive network backend, fabricated blockchain/oracle demo data, unreviewed deploy scripts, and unlicensed illustrations. The original archive/extraction and existing dirty project work remain intact. See `docs/comfest-url-trust-integration.md`.
- Final verification: `.venv/bin/python -m unittest discover -s tests -q` ran 113 tests (110 passed, 3 optional live tests skipped); Python `compileall` and `git diff --check` passed; the HTML parsed with 112 unique IDs and both trust assets linked. Node is unavailable here, so standalone JavaScript syntax checking could not run. Local status, records, static asset, and passive inspection endpoints returned HTTP 200; no public TLS or reputation check, Parallel call, training, or model/data change was made.
- No model weights, training artifacts, or existing datasets were modified; no files were committed.

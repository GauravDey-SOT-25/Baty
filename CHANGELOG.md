# Changelog

## 2026-10-17 — Add the Baty browser extension

- Added a standalone Chrome/Edge Manifest V3 extension under `extension/` for manual suspicious-message/URL analysis through the configured Modal endpoint.
- Added optional, off-by-default active-site checking with explicit permissions, URL-only disclosure, current-result display, and timeout/error reporting. No browser install or live Modal request was performed.

## 2026-10-17 — Vercel hosted-preview preparation

- Added a Vercel static build allowlist for the Baty landing page, Trust Ledger page, and hosted assistant UI; the local model, datasets, adapters, `.env`, research backend, and legacy demo backend are not included.
- Added a same-origin Node function that forwards only Google-authenticated questions to the fixed protected Modal inference endpoint, keeps Modal credentials in server environment variables, caps input, and avoids storing questions or answers.
- Added a separate hosted assistant page and a clear unavailable page for the local Parallel research workspace. Hosted landing-page controls that require local APIs now show as unavailable instead of issuing failed requests.
- Added Vercel setup notes. Deployment remains pending Vercel account authentication, Vercel environment variables, and Firebase Authorized Domains configuration; no public deployment was created.

## 2026-10-17 — Comfest main homepage and local AI integration

- Moved the Comfest homepage to repository-root `index.html` for GitHub Pages and loopback `/` and kept the previous Cyber Desk app at `/workspace`.
- Embedded the existing local URL analyzer, message analyzer, Qwen assistant, local record search, OCR, and user-maintained trust registry in the Comfest homepage. Linked to the existing provider-backed research workspace separately.
- Replaced stale blockchain, live-scan, and “coming soon” claims with descriptions of the actual connected tools and their limits. Removed external hero video/font requests so the site styling and hero use local assets and system fonts.
- Added API route/asset regression coverage. Verification: 113 tests ran (110 passed, 3 optional live tests skipped), Python compilation and `git diff --check` passed; `/`, `/workspace`, Comfest CSS/JS, and the hero asset returned HTTP 200. The homepage parsed with 60 unique IDs and no missing local image assets. No live provider request, model weight/adapter/data change, credential change, or commit was made.

## 2026-10-17

- Integrated the Comfest URL Trust workflow into the existing app as a local user-maintained domain ledger, explicit TLS certificate observation, and per-check opt-in domain-root reputation lookup. No blockchain connection or external reputation lookup is claimed by default. Reviewed the archive and documented why its embedded credentials, unsafe Flask URL fetches, and simulated blockchain/oracle features were not reused. Verification: 113 tests ran (110 passed, 3 optional live tests skipped), Python compilation and `git diff --check` passed; no live provider request was made.

- Refreshed the local app into a responsive Cyber Desk workspace with persistent tool navigation, local model status, account shortcut, and cohesive styling across analysis, assistant/OCR, research, and account views.
- Added Firebase failure-code details to sign-in and database-sync status messages; live Firebase setup screens were opened for provider/rules review.
- Made the local app accept the Firebase-authorized `localhost` browser origin while keeping its listener bound to loopback; documented the live Firebase authorized-domain mismatch for `127.0.0.1` and added a regression test.
- Added optional local image text extraction to the Learning assistant using native macOS Vision. The UI accepts bounded PNG, JPEG, GIF, WebP, and HEIC images, displays OCR text for review, and inserts it into the text prompt only after user action. No image is uploaded to Modal; if Modal is selected, its disclosure clarifies that the prompt (including inserted OCR text) is transmitted.
- Added a loopback `/api/ocr` endpoint, request bounds, temporary-file cleanup, and an ignored local Swift helper build cache. No model, weights, training artifacts, or Python dependencies changed.

## 2026-10-17

- Added Firebase Google sign-in and explicit opt-in Realtime Database backup of assistant Q&A, UID-scoped database rules, bounded history, account UI, and setup/privacy instructions. No Firebase Console settings or remote rules were changed; those require operator setup. Added local static and HTTP integration regression coverage.
- Connected Firebase Google identity to the Modal inference preview. The local API relays the short-lived Firebase ID token and question while keeping a dedicated Modal Proxy Token in ignored owner-only `.env`; Modal verifies signed token claims and enforces 3 requests/minute per UID. Added an opt-in cloud-model toggle; local inference remains the default. Modal deployment health returned HTTP 200 and an invalid Firebase token was rejected with HTTP 401. The local server-to-Modal relay was also verified with an invalid token returning HTTP 401. A valid Google sign-in flow remains unverified because Firebase Console/browser access is unavailable.

- Deployed the protected Modal CPU inference preview using public Qwen2.5-1.5B-Instruct at a pinned Hugging Face revision. Local MLX weights, adapter, corpus, evaluation/training data and `.env` were not included. Modal created a persistent remote model-cache Volume and fetched the public weights on first request.
- Fixed a first-build issue that selected CUDA dependencies by pinning `torch==2.14.1+cpu`; successful build used the CPU wheel. Fixed FastAPI's request parsing after the initial smoke test returned 422.
- Verified authenticated health (HTTP 200) and one benign inference (HTTP 200; 30.6-second model execution; answer truncated by 96-token cap and marked unverified). `modal curl` did not attach proxy credentials; temporary proxy token was deleted after testing.
- Added one-command deploy helper, cost/data-flow/usage notes and persistent-volume cleanup guidance. The preview is not the full application and is not production-ready.
- Verification after deployment corrections: 86 tests ran (83 passed, 3 optional live tests skipped); Python compileall, shell syntax, `git diff --check`, and `pip check` passed.

- Hardened the loopback API against local resource exhaustion and ambiguous HTTP framing: fixed maximum workers, connection timeout, body size limit, transfer-encoding rejection, and per-endpoint local rate limits. Health no longer reports a model available from a directory-only check.
- Verification after API hardening: 78 tests run (75 passed, 3 optional live tests skipped); compileall, `git diff --check`, and `pip check` passed.

- Added a reproducible offline 25-query retrieval evaluation with CISA source provenance and a local evaluation/training prompt-overlap audit. Documented metrics, scoring rubric, human-review needs and limitations.
- Tightened lexical retrieval to reject low query-coverage matches, restored source labels from recognized local record types, and added regression coverage. Current retrieval metrics are in `reports/cyber-retrieval-v1.json`; they remain diagnostic and authored.
- Full verification: 74 tests run (71 passed, 3 optional live tests skipped), compileall, `git diff --check`, and `pip check` passed. No live Parallel call, training, weight update, or commit.

- Improved local record retrieval with Unicode normalization, token-based field-weighted lexical ranking, rare-term weighting, and a minimum relevance threshold. Search results retain source attribution and expose the lexical relevance score; weak matches now return no records.
- Added explicit answer-basis labeling in the assistant wrapper, an abstention path for current/product-specific claims with no local evidence, and instructions to label source-free model answers as general unverified education. Added retrieval and abstention/source-attribution regression tests. No model, data, or training artifacts were changed.

- Established the local project, environment notes, baseline source layout, and persistent project instructions.
- Implemented loopback-only app/API, message triage, passive URL analysis, local retrieval, and a learning assistant.
- Downloaded and verified local inference for the pinned 4-bit Qwen2.5-1.5B model after explicit user approval.
- Added provenance-preserving CISA KEV/advisory and filtered Hacker News retrieval data. The Hacker News corpus is a single pinned monthly shard and is treated as anecdotal.
- Built and evaluated a character n-gram URL classifier using UCI PhiUSIIL with domain-grouped splits; documented limitations and source license.
- Audited candidate instruction data, excluded unsuitable external instruction samples from training, and ran a small LoRA smoke experiment on manually authored examples. The adapter did not materially improve held-out responses and is disabled.
- Grounded retrieved answers in local record fields, restricted explicit CVE queries to exact-CVE records, and added deterministic responses for several defensive safety cases.
- Latest verification: 29 unit tests pass. Local model generation was verified; generated answers remain fallible and the app is a local research prototype, not an autonomous security decision system.

## 2026-10-17 — Web research integration

- Integrated the pre-existing research work with current Parallel Search, Extract, Task Run, Monitor, Monitor Events and structured Task API enrichment schemas.
- Corrected unsupported request fields, task result polling, Monitor creation/cancellation, and the project-local research task storage location.
- Added explicit enrichment for public security records with a constrained output schema and preserved per-field source citations.
- Added manual Monitor event checks, saved task report viewing, public-data and possible-cost disclosures, URL screening, and local per-client rate limits.
- Fixed inline event handlers that violated CSP and replaced provider/user-text `innerHTML` insertion with safe text/DOM rendering.
- Added mocked integration and local loopback route tests. Latest suite result: 47 passing tests. No Parallel key was configured; no paid/live API calls were made.
- No Firebase/auth system exists, so local research history is shared; the dedicated beta FindAll workflow and provider-side DNS/redirect verification remain unavailable.

## 2026-10-17 — Research security and validation readiness

- Hardened Extract URL filtering against legacy numeric IPv4 spellings and percent-encoded hostnames; added regression cases for private IPv4/IPv6 edge addresses, mapped IPv6, malformed authorities, and length limits.
- Changed research task/monitor persistence to atomic JSON replacement with owner-only POSIX file permissions.
- Added a separate live Parallel Search/Extract/Task suite that is skipped unless explicitly enabled with `PARALLEL_LIVE_TESTS=1` and a configured API key.
- Documented local-only identity boundary, indefinite file retention, setup/run commands, live test costs, and provider-side redirect/DNS limitations.

## 2026-10-17 — Local model and evaluation verification

- Re-ran project tests, compilation, diff checks, and README server startup/health check; current suite has 59 tests, 56 passing and 3 billable live tests skipped.
- Verified local MLX model metadata, exact path and weight size, performed a base-model generation, and confirmed no default adapter is loaded. Inspected smoke training logs and retained adapters without modifying artifacts.
- Added a 40-example offline evaluation-only suite and runner covering phishing/benign messages, suspicious/benign URL strings, and cautious cybersecurity Q&A. Saved raw results and manual QA rubric scores separately.
- Recorded high false-positive rates for message and URL heuristics and QA weaknesses in both raw base output and app retrieval behavior. Deferred fine-tuning pending retrieval/abstention improvements and better-reviewed evaluation data.
- Confirmed no replacement Parallel key or `.env` is configured. No live request was made; documented local setup and retained the one-request approval gate.

## 2026-10-17 — Bounded Trendyol LoRA experiment

- Fixed `audit_instruction_quality.py` to read the actual `messages` structure in prepared chat data; the earlier audit had incorrectly reported all rows as missing.
- Prepared a filtered copy of the existing Trendyol training split (701 retained / 95 excluded) and ran a 701-step local MLX LoRA experiment on the existing Qwen2.5-1.5B-Instruct 4-bit conversion. Existing base weights and adapter folders were untouched.
- Evaluated on the untouched 100-row Trendyol test split: base loss 3.119 vs adapter loss 1.809. On eight separate QA prompts, a single-pass rubric review scored base 2/8 and adapter 1/8; unsupported patch detail and unsafe HTTPS claims were observed. The adapter remains an isolated experiment and is not enabled by default. Details: `reports/trendyol-m5-training.md`.

## 2026-10-17 — Deployment readiness hardening

- Added model/runtime/adapter status reporting to the local UI and an opt-in checkbox for retrieval so ordinary education questions can reach local MLX inference without unrelated lexical matches overriding it. CVE and current/product-specific questions still require evidence or abstain.
- Added a bounded repetition penalty after a local base-model run repeated its answer. This is a decoding improvement only, not a factuality improvement.
- Kept the Trendyol adapter disabled after the saved QA review found it worse than base. Re-ran the fixed 40-example offline suite and documented metrics, limitations, and production gates in `reports/deployment-readiness.md` and `reports/cyber-eval-readiness.json`.
- Restricted HTTP Host headers to the loopback origin and made `create_server` refuse all binds except `127.0.0.1`, closing a DNS-rebinding gap in the local browser boundary. Added regression tests.
- Audited pinned requirements and the installed project environment with `pip-audit 2.10.1` in an ignored scratch venv; no known vulnerabilities were reported. `pip check` also passed.
## 2026-10-17

- Added a Parallel Responses quick-answer tab with effort selection, citations, opt-in disclosure, local validation and endpoint rate limiting.
- Verified via mocked tests only; no live Parallel request or billable usage was made.


## 2026-10-17

- Added a Cyber Desk landing/playground inspired by Parallel's tool layout and linked the six research workflows to their usable panels.
- Added beta FindAll objective ingestion, editable matching conditions, generator selection, asynchronous status/result polling and citation links. No live provider requests were made.

## 2026-10-17

- Added responsive breakpoints for desktop, tablet, and small mobile screens across the landing page and security/research workspace, including sticky mobile navigation and overflow handling.
- Follow-up: replaced fixed-width assumptions with fluid sizing, intrinsic card grids, workspace container queries, and a naturally wrapping narrow-screen hero heading.
- Browser viewport checks found and fixed a desktop landing issue where the hidden sidebar still reserved a grid track. Rechecked the landing at 17 widths (240–1920px) and six workspace views at nine widths with no horizontal page overflow.
- Unified all tool-view styling with the Overview's neutral palette, editorial typography, bordered panels, and dark primary actions. Wrapped navigation below 1,100px and removed the duplicate Account & sync header action. Verified 84 landing/tool viewport combinations from 240px to 1,920px with no page overflow.

## 2026-10-17

- Configured the user-provided Parallel API key in the ignored local `.env` file with mode `0600`, restarted the local app, and verified its provider status as live-web. No live Parallel request was made.

## 2026-10-17

- Re-aligned the root homepage with the supplied Comfest visual source by restoring its original variable-font stack and preserving its original layout, motion, and artwork. Kept the integrated AI workspace and tool navigation.
- Fixed root-relative poster and WebGL hero artwork resolution, and allowed the source font host through the local and Vercel Content Security Policies.

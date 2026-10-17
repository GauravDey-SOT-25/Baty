# Decisions

## Comfest as the application homepage

- Serve the extracted `Comfest - 26/index.html` at `/` because the user identified that folder's index as the main homepage. Keep the previous full Cyber Desk application at `/workspace` so its Parallel research and Firebase account features remain reachable.
- Connect the Comfest page to existing local API endpoints for passive URL analysis, message analysis, local-model Q&A, local retrieval, OCR, and the user-maintained trust registry. Keep external TLS/reputation requests individually opt-in and web research on its separately disclosed workspace.
- Keep the Comfest static route restricted to the known app resources and files beneath its `assets/` directory; do not expose the archive's backend sources or embedded credentials through a generic static-file route.
- Remove remote marketing fonts and video references from the Comfest homepage to keep its first render local and compatible with the loopback server's content-security policy.

## 2026-10-17 — Keep Modal preview separate and authenticated

- Use Modal only for an inference observation preview, not a cloud migration of local classification/retrieval/user state. Run the public Qwen2.5-1.5B-Instruct base model on CPU from a pinned Hugging Face revision because local MLX weights are Apple-specific; do not transfer the local model, adapter, corpus, training splits, or `.env`.
- Require Modal Proxy Token authentication at the web-function edge, one maximum container, scale-to-zero, bounded HTTP body and generation size, and no prompt logging. Disclose that any submitted question leaves the laptop and is processed by Modal.
- Do not deploy until the user's Modal CLI authentication is complete. Keep GPU disabled for the first preview to avoid GPU billing; check live workspace billing and current pricing before use.

## 2026-10-17 — Bound local API request resources

- Keep the unauthenticated API loopback-only. Add conservative request-size, socket-timeout, worker-concurrency, and request-rate limits to reduce local resource-exhaustion risks; explicitly do not treat these as authentication or public-deployment controls.
- Report model availability only when basic model configuration, tokenizer, and safetensors files exist. This is a file-presence check, not a full model-load health check.

## 2026-10-17 — Separate retrieval evaluation and lexical leakage audit

- Keep the 40-example baseline byte-identical and use a distinct authored retrieval benchmark pinned to local CISA KEV/advisory records. Store source IDs, URLs, dates, snapshot/license notes and dataset/corpus hashes; never fetch URLs during scoring.
- Count every non-target result as a strict false positive pending independent relevance adjudication, even if it may be useful related context. Report retrieval, Q&A rubric, and classifier measures separately.
- Audit exact and 3-gram near-duplicate prompts against local instruction splits, but treat a clean lexical audit as limited evidence only; it cannot establish semantic split independence.
- Do not fine-tune from this work. The adapter currently underperforms base on the small QA rubric and the retrieval set does not measure generated-answer correctness.

## 2026-10-17 — Relevance threshold and evidence-aware answers

- Score local documents with normalized token sets, corpus rarity, and title/vendor/product/identifier/summary/body field weights. Require a minimum score before returning evidence; preserve source URL, dates, IDs, and provenance. Treat the score as lexical ranking, never semantic confidence.
- Answer current or product-specific claims only when relevant local evidence exists; otherwise state the evidence gap. Label source-free model output as general knowledge that has not been verified against current sources. Keep ordinary defensive education available.
- Compare changes against the fixed 40-example evaluation-only set. Do not train on it or use it as a production-quality claim; require independent review and a larger held-out set before deployment.

## 2026-10-17 — Integrate the Comfest URL Trust prototype as an honest local capability

- Port the useful URL trust workflow into the existing loopback app: private user-maintained records, explicit TLS certificate observation, and optional reputation lookups.
- Keep passive registry lookup local. TLS DNS/connection and reputation provider calls require separate in-app opt-ins; reputation checks send only the normalized domain root and use local environment keys.
- Do not import the archive's embedded provider credentials, permissive Flask backend, fake validator/chain telemetry, or contract deployment flow. Report blockchain as disconnected until a separately reviewed, actually deployed ledger exists.
- Keep the user-supplied archive and extracted source untouched; document the disposition of each archive component and retain no unlicensed marketing assets or duplicate Git history in the app.

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

## 2026-10-17 — Approved local model and defensive evaluation

- The user explicitly approved the pinned 868,628,559-byte model download. Downloaded the specified revision and verified local MLX inference.
- Use UCI PhiUSIIL (CC BY 4.0) for the URL-only baseline, exclude the unresolved-license phishing email candidate, and avoid downloading the 36.6 GB HTML-heavy PhreshPhish dataset.
- Keep one pinned Hacker News monthly shard for local retrieval rather than mirroring the full archive; treat community material as unverified and preserve source attribution.
- Do not train on the sampled external instruction datasets after spot review found factual errors and chain-of-thought style outputs. Use a small manually written defensive dataset only to exercise the LoRA pipeline; leave its adapter disabled because held-out quality did not materially improve.
- For evidence-backed answers, use local source fields directly and never let free-form generation invent details from retrieval. Explicit CVE requests must match records naming that CVE; otherwise report that the local snapshot has no match.
- Maintain a local-only posture: no submitted URL fetching, DNS resolution, automatic model download, or autonomous remediation.

## 2026-10-17 — Keep web research provider opt-in and local-first

- Use the verified Parallel REST API shapes behind `ResearchProvider`; read `PARALLEL_API_KEY` only from the server environment. Do not make live calls during tests or development unless a key is deliberately configured and the user has authorized the provider use.
- Preserve local fallbacks for Search/Deep Research; Extract and structured enrichment must state clearly when live access is unavailable. A source hit or missing report is never a safety verdict.
- Send only the public query/URL/record fields explicitly submitted for a research action. Never forward the complete private message. Enrichment uses a fixed public security-record field allowlist and JSON output schema.
- Keep provider-controlled text out of HTML sinks, preserve citations as plain displayed URLs, use manual Monitor event checks, and apply conservative local route rate limits because provider activity may be billable.
- Do not introduce a parallel authentication system while Firebase is absent. Keep research history local/shared and the server loopback-only until authenticated identity and user-owned persistence are implemented.
- Search acts as the current report-discovery equivalent. Defer Parallel's beta FindAll structured-entity workflow until its full request lifecycle is specifically integrated.

## 2026-10-17 — Research data protection and live verification

- Keep this app as an unauthenticated, loopback-only local prototype for this milestone; do not imply Firebase, UID verification, or per-user isolation exists. Do not expose it publicly.
- Write local research task and monitor data atomically with POSIX owner-only permissions. Retain records until manually removed; automatic retention/deletion is deferred.
- Keep provider integration checks in a separate opt-in suite gated by both `PARALLEL_API_KEY` and `PARALLEL_LIVE_TESTS=1`, because task/search/extract requests may incur charges. Never run them as part of routine offline tests.
- Reject ambiguous numeric IP host spellings and percent-encoded hostnames locally. This is a defense-in-depth input filter only; provider-side DNS resolution, rebinding defenses, and redirect validation remain unverified.

## 2026-10-17 — Evaluation before any new fine-tuning

- Keep the Qwen base model and existing smoke adapters unchanged. The existing 8-iteration LoRA run completed, but prior review showed no material held-out improvement and the adapter is not the default inference path.
- Treat `cyber_eval_v1` as a small evaluation-only, project-authored synthetic set. Do not use it for training. Its metrics are diagnostic because sample size is small and examples may align with the rule baseline.
- Do not start another fine-tune until retrieval/abstention behavior is improved and a broader expert-reviewed test set demonstrates a clear, measurable target for training.
- Do not make the gated live Parallel Search request until a replacement key is configured locally and the user explicitly approves that one request. Never use or reveal the previously exposed key.

## 2026-10-17 — Isolate the requested Trendyol training run

- User authorized a bounded local training experiment after an earlier hold. Use only the existing 1,000-row sample and fixed train split; do not download the full 53k-row dataset under the hackathon time constraint.
- Exclude automated reasoning artifacts, placeholder responses, and explicit harmful-action prompts from the temporary training copy. Keep original raw/split data intact, record transformations/hashes, and preserve the fixed validation/test splits.
- Use the already installed 4-bit MLX conversion of Qwen2.5-1.5B-Instruct on M5; place the adapter in a new experiment directory. Do not make it the application default based on token-loss alone; the paired QA review found regressions.

## 2026-10-17 — Keep deployment local and supervised

- The app's production boundary remains single-user localhost. Reject DNS-rebinding Host headers and refuse non-loopback binds; do not expose this service publicly without a redesigned authenticated deployment architecture.
- Keep the Trendyol adapter disabled because its QA review regressed. Lower dataset test loss does not establish security-answer quality.
- Treat generated model content as unverified. The current local model is only eligible for supervised demonstration until independent evaluation, classifier calibration, dependency security scanning, and operational review are complete.


## 2026-10-17 — Modal deployment remains explicit

- Use the protected CPU inference preview only after the user completes Modal CLI login. A local helper can deploy after login, but this preparation task does not create cloud resources or download weights.
- Create the remote model-cache Volume on deployment, keep it separate from the local model cache, and delete it only through an intentional user action because it persists and may incur storage charges.
- Modal preview remains a general-knowledge raw-base-model endpoint; never describe it as full application deployment or production cybersecurity decision support.


## 2026-10-17 — Add opt-in Firebase account and assistant backup

- Implement Google sign-in and Realtime Database backup for future assistant Q&A only. Keep local analysis usable without sign-in; require explicit opt-in before writes. Do not sync message triage, sender details, URLs, incident searches, or web-research activity.
- Scope database access to the authenticated user's UID, deny root access, bound record lengths, and cap saved assistant history at 200 entries per user. User may explicitly delete their own cloud history.
- Keep this separate from the loopback-only API and Modal preview. Firebase Console provider/domain configuration and remote database-rule deployment remain operator setup steps; do not claim these external settings were completed without verification.


## 2026-10-17 — Protect Modal inference with Firebase Google identity

- Keep Modal Proxy Token authentication at the edge and add Firebase Google ID-token verification inside the model API. Never place Modal credentials in browser code; relay through the loopback-only local server using a dedicated owner-only local secret file.
- Keep cloud model use an explicit opt-in; retain local inference as default. Send only the question and short-lived Firebase ID token to Modal; no retrieval evidence is attached. Database backup remains a separate consent control.
- Verify Firebase token signature and project/issuer/provider/email claims; apply a per-UID request limit. Do not add Firebase Admin service-account credentials.

## 2026-10-17 — Local image OCR

- Keep Qwen as a text model. Add OCR as a separate local preprocessing path using macOS Vision via a small Swift helper, with no OCR model download, external OCR service, or model-weight changes.
- Bound uploads to 4 MiB and decoded images to 24 megapixels; accept common raster formats, delete temporary image files after processing, and let the user review extracted text before adding it to a question.
- If the user separately chooses Modal, disclose that the resulting question including OCR text is sent, while the source image is not. Treat OCR output as untrusted input.
- For Firebase Google sign-in, use `localhost` because live project configuration currently authorizes it; permit this exact Host alias while keeping the server bound only to `127.0.0.1`. Do not claim login success until an actual OAuth flow completes.
## Parallel Responses integration

- Expose the Responses API as an explicit Quick answer workflow separate from the local Qwen assistant. The user's question is sent to Parallel only after the user submits the form, and the UI warns about third-party disclosure and possible billing.
- Keep citation links to provider annotations and clearly label them as unverified. Never automatically open URLs. Allow low/medium/high effort while applying the local research rate limit and a 120-second upstream timeout.
- Do not make a live request as an implementation test; use mocked transport tests to avoid cost and data disclosure.


## Parallel-style UI and FindAll

- Present the web-research capabilities in a workspace inspired by Parallel's product organization while retaining Cyber Desk branding and preserving local analysis boundaries.
- Keep FindAll explicitly opt-in, default to a preview run, make the suggested conditions editable before starting, rate-limit create calls locally, and render provider text safely. Keep FindAll beta and cite the current official API contract.
- Do not make a live API request during implementation or tests. Keep local model inference distinct from Parallel's hosted Responses API.

## Responsive layout

- Keep the landing and tool views usable from 280px-wide phones to large desktop screens. Collapse the sidebar into a touch-scrollable sticky navigation bar on narrow viewports, and let content grids/forms reflow without horizontal page overflow.
- Keep responsive overrides in a same-origin stylesheet served by the loopback API; honor reduced-motion preferences and visible keyboard focus.
- Prefer content-driven container queries and intrinsic `auto-fit` grids for workspace panels; use viewport breakpoints only for structural navigation changes. Do not impose a global minimum page width or keep forced headline line breaks on narrow screens.
- When the landing mode hides the workspace sidebar, collapse the app shell to one block at every width so an empty grid track cannot narrow the visible landing page.

## Unified workspace page styling

- Use the same light neutral background, restrained cards, typography, and dark action buttons across Overview and all tool views; keep Cyber Desk identity and the tool-specific content intact.
- Below 1,100px, stack the workspace brand and navigation and let navigation items wrap so every destination remains visible without clipping. Hide the redundant account shortcut from the page header because Account & sync is already in navigation.
- Verify the responsive behavior with browser viewport checks across the landing page and each tool view; no API calls are needed for style verification.

## Parallel API credential storage

- Keep `PARALLEL_API_KEY` in the Git-ignored, owner-only project `.env` file. Do not expose it in frontend code, tracked configuration, application responses, or logs.
- After changing the credential, restart the local server because the research provider is cached at startup. Verify configuration through the local status endpoint; do not make a live provider request just to validate that the key is present.

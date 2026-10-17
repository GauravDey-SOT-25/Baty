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
- The existing local UI remains loopback-only at `127.0.0.1`; the Web Research section now adds Search/discovery, Extract, Deep Research, Monitors, report history and structured record enrichment. Its backend validates JSON and input sizes, applies same-origin browser checks, rate-limits research routes, and suppresses request-body logs.
- `.venv/bin/python -m unittest discover -s tests -q`: 56 tests ran after hardening (53 passed, 3 live tests skipped by default).

## Important quality limits

- The base LLM failed four of six small, hand-written safety questions. The smoke adapter did not correct them. The app should not be relied on for incident-response decisions without human verification. This result is documented with exact generations in `assistant-base-review.jsonl` and `assistant-adapter-review.jsonl`.
- Trendyol and Heimdall samples were excluded from training after spot checks found reliability concerns. The adapter was trained only on 24 short project-authored examples to exercise the runtime; it is not a useful domain-specialized release.
- The URL model result is from one dated source. Its 99.55% accuracy is not a real-world claim. Registrable-domain grouping approximates common public suffixes rather than using the full Public Suffix List; unseen suffixes could permit leakage.
- The message detector is a rule baseline and has no supervised evaluation or calibrated confidence.
- Retrieval uses lexical matching, not a sentence embedding model or FAISS. The 2026-08 HN sample can be incomplete and stale. The full HN archive and other large HTML datasets were not downloaded.
- The Parallel provider adapter follows the current documented Search, Extract, Task, Monitor and Monitor Events contracts; local mocked tests passed. `PARALLEL_API_KEY` is not configured, and no live provider request or paid operation was performed. Without credentials, Search and Deep Research use local data/model fallback; Extract and structured enrichment report that live provider functionality is unavailable; local monitors do not poll.
- Search is the app's report-discovery equivalent; the distinct beta FindAll structured-entity API is not implemented. There is no Firebase integration or authenticated multi-user identity. Research history/monitors are shared across local callers, and the app must remain loopback-only.
- Extract URLs are checked locally for HTTPS, credentials, private/reserved address literals, metadata and internal hostnames. Page retrieval and redirects happen in the provider, so the app cannot independently verify provider-side DNS/redirect controls. Never treat these checks as a guarantee that third-party fetch behavior is safe.
- UI changes were verified by CSP/script/API tests and an in-process HTTP server; a graphical browser walkthrough was not run.

## 2026-10-17 milestone security and integration status

- Re-ran the pre-change baseline: 47 tests passed; `git diff --check` and `compileall` passed.
- No `PARALLEL_API_KEY` was configured. No live Parallel requests were made. A separate `tests/test_parallel_live.py` is opt-in with both the key and `PARALLEL_LIVE_TESTS=1`; it covers Search, public CISA Extract, and Task create/status and may incur provider charges. It was not run.
- Hardened local Extract URL checks to reject legacy numeric IPv4 spellings and percent-encoded hostnames, in addition to private/reserved IPv4/IPv6 literals, credentials, non-HTTPS schemes, and known internal names. Added edge-case regression tests. Provider-side DNS rebinding and redirect behavior remain outside this application's verification boundary.
- Research JSON persistence now uses atomic replacement and owner-only `0600` file permissions on POSIX. No automatic retention or account deletion flow exists; local history remains until the corresponding JSON files are removed.
- No Firebase project/auth configuration exists. Authentication and verified UID enforcement were not implemented. The app remains an unauthenticated, loopback-only single-user prototype; `owner_uid` is metadata and not a security boundary.
- Ordinary tests use mocks; no real invalid-credential, provider timeout/rate-limit, or live provider failure was induced. Those error paths are mock-tested where applicable. No provider-side URL inspection or DNS/redirect security test was performed, and no graphical manual UI walkthrough was run.
- Final verification: `.venv/bin/python -m unittest discover -s tests -q` ran 56 tests: 53 passed and the three opt-in live provider tests were skipped. Running the separate live test discovery command without a key also skipped all three as designed. `git diff --check` and `.venv/bin/python -m compileall -q src tests` passed.
- No model downloads, training, or changes to model weights/adapters/checkpoints were made.

## 2026-10-17 project health and local model verification

- Health: final `.venv/bin/python -m unittest discover -s tests -q` ran 59 tests (56 passed, 3 opt-in live tests skipped). `.venv/bin/python -m compileall -q src tests scripts` and `git diff --check` passed. Starting with `.venv/bin/python -m src.api.server` succeeded; `/api/health` returned `{"status":"ok","mode":"local-only"}` and research status reported provider `local`, no key. Server was stopped after the check.
- Base model: `mlx-community/Qwen2.5-1.5B-Instruct-4bit`, pinned repository revision `8b403126fc14f14cfc99bb4cfa72ecbc129ea677`, local path `models/Qwen2.5-1.5B-Instruct-4bit`, 868,628,559-byte safetensors file. Local metadata identifies `qwen2` / `Qwen2ForCausalLM`; packed weight `.scales`/`.biases` tensors corroborate the 4-bit MLX conversion although the HF `config.json` reports `bfloat16` and no `quantization_config`. Runtime is MLX 0.32.4 / MLX-LM 0.32.2. A fresh `answer_locally()` generation succeeded with adapter loading disabled. The application does not call a remote model for assistant inference.
- Adapter/training: four adapter artifact directories exist (`curated-smoke`, `interruption-resume`, `interruption-test`, `recovery-test`). The eight-iteration `curated-smoke` LoRA run reached 8/8 and saved adapter weights; a separate recovery run completed one iteration after loading those weights. The 50-iteration interruption run stopped at iteration 9/50. This is genuine pipeline smoke fine-tuning, not a validated cybersecurity model. `CYBER_ADAPTER_PATH` defaults to absent `adapters/best`, so the application does not load any of these adapters by default. Existing review found no material improvement from the smoke adapter.
- Offline evaluation-only set: 40 project-authored cases (16 messages, 16 URL strings, 8 Q&A prompts) with provenance/rubrics; no training/validation split is applicable because these examples are used only for evaluation. No URLs were resolved or fetched. Message rules: precision 53.3%, recall 100%, F1 69.6%, false-positive rate 87.5%, accuracy 56.3% (8 TP, 1 TN, 7 FP, 0 FN). URL model plus static guard: precision 57.1%, recall 100%, F1 72.7%, false-positive rate 75.0%, accuracy 62.5% (8 TP, 2 TN, 6 FP, 0 FN). The very high false-positive rates show the small synthetic set is only diagnostic; the URLs are not representative live samples.
- QA review, 8 examples: base model passed 2/8 (25%) against explicit rubrics. The app's deterministic safeguards/retrieval wrapper passed 6/8 (75%); it failed two ambiguous questions by returning unrelated lexical records. Scores are a single-pass, non-independent manual review, not a formal benchmark. Raw generations and exact rubrics are in `reports/cyber-eval-v1.json`; scores tied to that artifact hash are in `reports/cyber-eval-v1-review.json`.
- Fine-tuning recommendation: do not fine-tune now. The current base has serious safety/correctness failures, but an eight-step adapter did not materially improve the previous held-out review and this new small evaluation does not establish a training target or generalization. Prioritize improving the app's retrieval/abstention behavior and expanding a reviewed evaluation before considering another LoRA run.
- Parallel: no `.env` file or `PARALLEL_API_KEY` process variable is configured; `.env` is Git-ignored and `.env.example` contains only a placeholder. The `parallel-web`/`parallel` SDK packages are not installed; the existing client uses standard-library `urllib`. Current official Search, Extract, Task Run, Monitor, and pricing pages were checked; request formats were not changed. No live request was made because the replacement key is absent and this prompt requires explicit approval for the one live Search.
- GUI manual test was not completed because the CUA runtime did not start. The startup/health and research-status requests above were verified over loopback HTTP.

## Not ready for unattended use

The app is a local prototype and defensive triage aid. The generated model can be confidently wrong; the classifier is uncalibrated; search results are not a complete incident history; and no external reputation check is performed. A human should verify technical advice and findings before acting.
# Retrieval and abstention follow-up — 2026-10-17

Ran the same 40-example, evaluation-only suite with the local base model and application wrapper. Raw results are in `cyber-eval-v1-after.json`; the separate single-pass QA rubric review is in `cyber-eval-v1-after-review.json`. No submitted URL was resolved or fetched, and no live Parallel request was made.

| Task | N | Precision | Recall | F1 | False-positive rate | Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Message rules | 16 | 53.3% | 100.0% | 69.6% | 87.5% | 56.3% |
| URL classifier + static guard | 16 | 57.1% | 100.0% | 72.7% | 75.0% | 62.5% |

The saved earlier report has identical message and URL metrics. The QA raw base model scored 2/8 (25%) and the application wrapper scored 8/8 (100%) on this review. However, the pre-change reproduction already scored 8/8 in the shared working tree because the defensive QA guardrails were present before this retrieval change. The saved `cyber-eval-v1-review.json` (6/8) predates those guardrails. Thus no QA score increase is attributable to this milestone. The review is subjective and not independently replicated.

The new search threshold, field weighting, and source-free answer basis are covered by regression tests. This small synthetic suite does not establish general improvement. Obtain independent review and evaluate on a larger, held-out, realistically sampled dataset before production use. Existing high message/URL false-positive rates remain unresolved.

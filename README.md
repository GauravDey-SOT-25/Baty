# Local Cybersecurity AI Platform

## Local OCR input

The Learning assistant can extract text from PNG, JPEG, GIF, WebP, and HEIC images with macOS Vision. OCR is local preprocessing for the existing text model, not visual model inference. The loopback API accepts images up to 4 MiB and 24 megapixels; extracted text is shown for review and is added to a question only when selected. No OCR service, model download, or model weight change is used. If you then select the Modal model, the question including inserted OCR text is sent to Modal, while the image itself remains local.

A local-first defensive triage and learning prototype for macOS. It combines message indicators, passive URL analysis, a local Qwen model, a local character n-gram URL classifier, and local lexical retrieval. See [progress.md](progress.md) and [reports/final-evaluation.md](reports/final-evaluation.md) for current limits and evaluation.

## What works

- Message analysis returns explainable heuristic indicators without a confidence score.
- URL checking normalizes the URL, rejects localhost/private/reserved addresses and embedded credentials, and returns syntax indicators plus an uncalibrated local classifier signal. It never resolves DNS, opens the URL, fetches redirects, downloads content, or calls a threat-intelligence service.
- The optional **URL Trust** workspace stores user-maintained domain notes in a private local JSON ledger. Passive lookup is local-only. TLS inspection requires a separate checkbox and performs a bounded HTTPS handshake to a public host on port 443 without requesting page content or following redirects. Reputation lookups are off by default; when explicitly selected, they send only the domain root to configured Google Safe Browsing and/or VirusTotal keys. These checks are not a blockchain, a safety verdict, or proof of ownership. See [docs/comfest-url-trust-integration.md](docs/comfest-url-trust-integration.md) for the imported prototype review and feature mapping.
- The local model loads from `models/Qwen2.5-1.5B-Instruct-4bit` if present. It does not auto-download. The base model is imperfect; four of six focused safety questions produced materially unsafe/wrong answers. Verify its output.
- Local security-record search indexes 1,748 CISA KEV records, 30 CISA advisory RSS summaries, and 2,581 filtered records from one bounded Hacker News monthly shard. Ranking is lexical; HN posts are unverified discussion, not authoritative evidence.
- The loopback-only API and simple web UI run on `127.0.0.1:8765`. The app sends no user content to third parties by default and suppresses request-body logs. The local HTTP server rejects ambiguous request framing, enforces a 32 KiB request-body cap, uses a 15-second socket timeout, bounds active worker threads, and rate-limits local API work. These controls reduce accidental resource exhaustion; they do not provide user authentication or make this safe to expose on a network.

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

The main homepage at `/` is the repository-root `index.html`, and loads its Comfest styles, scripts, and images from `Comfest - 26/`. It includes local URL/message analysis, Q&A, OCR, records search, and private trust notes embedded in the page. The previous Cyber Desk workspace remains at `/workspace`; use it for the complete Parallel research and Firebase account workflows.

## Web research and intelligence

The Web Research area extends the local app with provider-backed Search/discovery, Extract, asynchronous Deep Research, daily Monitors with on-demand event checks, and schema-based enrichment of a public security record. It uses a provider abstraction; no Parallel SDK or additional dependency is needed. The request and response shapes were checked against the current [Parallel Search](https://docs.parallel.ai/api-reference/search/search), [Extract](https://docs.parallel.ai/api-reference/extract/extract), [Task Run](https://docs.parallel.ai/api-reference/tasks/create-task-run), [Monitor](https://docs.parallel.ai/api-reference/monitor/create-monitor), [Monitor Events](https://docs.parallel.ai/api-reference/monitor/list-monitor-events), and [FindAll](https://docs.parallel.ai/api-reference/findall/create-findall-run) documentation.

To enable live research, supply `PARALLEL_API_KEY` in the environment before starting the app. The key stays server-side and is never returned by the API. Parallel's [current pricing](https://parallel.ai/pricing) lists Search at about $0.001–$0.005 per request for 10 results, Extract at about $0.001 per request, Task runs at about $0.005–$2.40, and Monitor at about $0.003–$0.01; actual cost depends on operation and processor and can change. The UI explains which submitted public query, URL, or record fields leave the machine. Do not submit a private message or confidential incident content. The app does not call the provider when the key is absent; no live API call was made during development.

For local setup, copy `.env.example` to `.env`, restrict it with `chmod 600 .env`, edit the key only in a local editor, then export it before starting the app:

```sh
cp .env.example .env
chmod 600 .env
# Set PARALLEL_API_KEY in .env using a local editor; never paste it into source or chat.
set -a
source .env
set +a
.venv/bin/python -m src.api.server
```

Without a key, Search uses the existing local CISA/Hacker News corpus, Deep Research uses the local assistant and corpus, and monitors are stored locally but do not poll the web. Extract and structured enrichment clearly report that live provider functionality is unavailable. Search provides discovery of relevant public reports; the provider's separate beta FindAll structured-entity workflow is not implemented.

Extract input is restricted to public HTTPS URL syntax and rejects credentials, local/private/reserved IP literals, and known metadata/internal hostnames. The app delegates fetching to Parallel and does not follow redirects itself; provider-side DNS/redirect behavior is outside this local validator. Retrieved content remains untrusted. Search/enrichment results preserve source URLs and dates where supplied; validate citations and claims before acting.

Research requests have per-loopback-client rate limits. The optional Firebase account feature provides Google sign-in and opt-in cloud backup for future Learning assistant Q&A only; it does not sync message text, sender details, URLs, incident searches, or research activity. Research task history and monitors remain shared by local callers on the same machine. Do not expose the development server beyond loopback. Firebase Console provider/domain setup and database-rule deployment are required before account sync works; see [docs/firebase-auth-and-sync.md](docs/firebase-auth-and-sync.md). Research task results are stored in ignored local `data/research_tasks.json`; monitor state is stored in `data/research_monitors.json`.

To configure optional URL reputation lookups, add `GOOGLE_SAFE_BROWSING_API_KEY` and/or `VIRUSTOTAL_API_KEY` to the ignored local `.env` file. No bundled prototype credentials are reused. The checkboxes in **URL Trust** remain off by default and each selected request sends only `https://<normalized-domain>/`; provider quotas, terms, and retention policies apply. TLS inspection separately resolves and connects to the chosen hostname only after you select it. Neither capability runs during ordinary passive URL syntax analysis.

## Test

```sh
.venv/bin/python -m unittest discover -s tests -v
```

## Model and local inference

The pinned model is approximately 0.81 GiB and was downloaded after the user approved that download. In a fresh checkout, fetch it with:

```sh
.venv/bin/python scripts/download_model.py --confirm-model-download
```

The app will not download weights automatically. The Trendyol adapter is an isolated experiment and must not be enabled for deployment: its same-source test loss was lower, but its small cybersecurity QA review scored worse than the base model (1/8 vs. 2/8) and found unsafe/unsupported claims. Keep the default unadapted base model selected unless a separately reviewed evaluation clears an adapter. The app page reports whether model files are present and whether an adapter is enabled.

### Modal cloud inference preview

The Modal CPU inference preview in [deploy/modal_app.py](deploy/modal_app.py) accepts only verified Google sign-ins from Firebase Authentication and remains protected by Modal Proxy Token at the edge. The local server keeps that Modal token out of browser code and relays Firebase ID tokens to Modal for verification. In the Learning assistant panel, choose **Use the Modal cloud model** to send a question; this is separate from the optional Firebase Q&A backup checkbox. Questions leave the laptop and are processed by Modal. The service does not package the local MLX weights, adapter, corpus, training data, or `.env`. It is not the full application and is not production-ready for security decisions. Setup, billing, limitations, and cleanup are documented in [deploy/README-modal.md](deploy/README-modal.md).

### Vercel hosted preview

The repository includes a limited Vercel deployment configuration in [vercel.json](vercel.json) and setup notes in [deploy/README-vercel.md](deploy/README-vercel.md). It serves the public Baty/Comfest pages and a separately authenticated Modal assistant. It does not host local MLX inference, OCR, local records or trust notes, classifiers, or Parallel research. Deployment still requires a Vercel project, server-side Modal environment variables, and the Vercel hostname in Firebase Authentication's Authorized domains; no Vercel deployment has been verified from this workspace.

Open `http://127.0.0.1:8765` and choose **Ask local AI**, or open `http://127.0.0.1:8765/workspace` and choose **Learning assistant**. General questions go to local MLX inference by default; select **Include relevant local security records** to add local retrieval. Explicit CVE and current/product-specific questions still use local evidence or abstain. Generated answers remain unverified and require human review; this prototype is not ready for production security decisions.

## URL classifier data and evaluation

The selected URL dataset is [UCI PhiUSIIL](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset), licensed CC BY 4.0. Its 56.9 MB source CSV is in ignored `data/raw/`; only URL text and labels are used.

```sh
.venv/bin/python scripts/download_phiusiil.py
.venv/bin/python scripts/prepare_url_dataset.py
.venv/bin/python scripts/evaluate.py data/processed/phishing --output reports/url-baseline-results.json --save-model models/url-classifier.joblib
```

The evaluation split groups by approximate registrable domain. Its high held-out score is specific to a single dated source and does not indicate expected live accuracy. The model signal is uncalibrated and never constitutes a verdict.

### Small offline product evaluation

Run `.venv/bin/python scripts/evaluate_cyber_eval.py` to evaluate the local message rules, URL model/static checks, and base model plus app Q&A wrapper against the fixed project-authored evaluation-only examples in `data/evaluation/cyber_eval_v1.jsonl`. It writes `reports/cyber-eval-v1.json`. No URLs are resolved or fetched; the suite is not training data. QA scores need manual review against the stored rubrics; the result file preserves raw answers for inspection. These small synthetic results are diagnostic and not production estimates.

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

After the initial quality review, a later user request authorized a bounded Trendyol experiment. A filtered 701-row copy of the existing 1,000-row sample was used for one local LoRA run; the prepared validation/test splits were retained separately. The adapter lives in `adapters/trendyol-m5-experiment` and is not enabled by default. The sample still contains unverified facts and the adapter produced unsupported security claims, so do not rely on it for security decisions. See `reports/trendyol-m5-training.md`.

`data/curated/defensive_seed.jsonl` contains 36 small, project-authored defensive examples used earlier only to verify the local MLX path; it is not a production training set or cybersecurity benchmark.

```sh
.venv/bin/python scripts/prepare_curated.py
.venv/bin/python scripts/train_lora.py --model models/Qwen2.5-1.5B-Instruct-4bit --data data/processed/curated --adapter adapters/new-run --config configs/training.yaml
```

That command is a dry run. Add `--run` to execute. The launcher refuses to overwrite an existing adapter directory. Resume adapter weights into a new output directory with `--resume-adapter-file path/to/checkpoint_adapters.safetensors`. MLX-LM does not restore optimizer or scheduler state from adapter weights; recovery is not an exact continuation of optimization.

The Trendyol experiment can be reproduced from the already prepared sample with `.venv/bin/python scripts/prepare_trendyol_finetune.py`, followed by the exact command recorded in `reports/trendyol-m5-training.md`. The preparation script refuses to overwrite a non-empty filtered directory.

## Privacy and safety

The app binds to loopback. Message content and user URLs remain local. The website checker is passive and makes no DNS, TLS, redirect, or reputation request. “No threat detected” and “no suspicious indicator” do not mean a site or message is safe. The model can hallucinate; do not use it as a replacement for incident-response professionals.

### Research validation and data boundary

The research workspace includes Parallel Search, Extract, Responses, Task, Monitor, and the beta FindAll discovery flow. Responses and FindAll are optional external calls: only submit public questions/criteria that you are comfortable sending to Parallel, and check the provider's current pricing before use. The FindAll integration defaults to Preview and asks you to review the generated criteria before starting a run. API credentials remain server-side in `PARALLEL_API_KEY`.


Run offline tests with `.venv/bin/python -m unittest discover -s tests -v`. Optional live Parallel checks are separate and can incur charges; configure `PARALLEL_API_KEY`, then explicitly run `PARALLEL_LIVE_TESTS=1 .venv/bin/python -m unittest discover -s tests -p 'test_parallel_live.py' -v`. No live call is made by the normal suite. Research JSON is stored locally with owner-only file permissions and persists until manually removed. Firebase Google sign-in supports opt-in assistant-history backup and authenticates optional Modal inference after Firebase Console setup; local research records still have no Firebase identity, automatic retention, or per-user isolation. Keep the app on loopback. Local URL checks reject known private and ambiguous numeric hosts, but cannot verify provider DNS resolution or redirect behavior.

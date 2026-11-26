# Baty: Local-First Cybersecurity Assistant

**Live preview:** [baty-mu.vercel.app](https://baty-mu.vercel.app/)

Baty is a defensive triage and learning prototype. Run the full application locally on macOS, or open the limited hosted preview from a browser on any device.

## Choose how to use Baty

### Hosted preview

The [live site](https://baty-mu.vercel.app/) serves the public Baty pages. It does not run the local MLX model, URL or message classifiers, OCR, local security-record search, URL Trust notes, or Parallel research. Its optional authenticated assistant sends questions to the configured Modal service; Firebase and Modal setup are required for that feature. See [Vercel deployment notes](deploy/README-vercel.md).

### Full local application

The local app runs its API on `127.0.0.1:8765` and keeps user content on the machine by default. It includes the local analysis and data features described below.

## Local setup

Create the project environment:

```sh
./scripts/setup_env.sh
```

Download the pinned local model when you want to use local AI. This is a separate, approximately 0.81 GiB download; model weights are not fetched automatically:

```sh
.venv/bin/python scripts/download_model.py --confirm-model-download
```

Start the app:

```sh
.venv/bin/python -m src.api.server
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765) for the main Baty page. The `/workspace` page contains the research and account workflows. Do not expose the local development server to a network. Environment details are recorded in [reports/environment.md](reports/environment.md).

## What the local app includes

- **Message analysis:** explainable heuristic indicators; it does not produce a calibrated confidence score.
- **URL analysis:** syntax checks and an uncalibrated local classifier signal. The passive check does not resolve DNS, open the URL, follow redirects, fetch page content, or contact threat-intelligence services.
- **Learning assistant:** local Qwen inference and optional lexical retrieval from local security records. Model output can be wrong or unsafe; review it before acting.
- **Image OCR:** macOS Vision extracts text locally from supported image formats. Text is shown for review and added to a question only when selected. OCR is not visual model inference.
- **URL Trust:** private, user-maintained domain notes stored in a local JSON ledger. Optional TLS inspection makes a bounded HTTPS connection only after selection. Optional Safe Browsing or VirusTotal checks send the normalized domain root only after selection. These are not safety verdicts or proof of ownership. See [the URL Trust review](docs/comfest-url-trust-integration.md).
- **Web Research:** optional Parallel Search, Extract, asynchronous research tasks, monitors, and public-record enrichment. The provider is not called without a configured key. See [Firebase and sync setup](docs/firebase-auth-and-sync.md) for the separate optional account and Q&A backup flow.
- **Browser extension:** a Chrome/Edge Manifest V3 extension in [`extension/`](extension/). Manual analysis runs only after clicking Analyze. Optional active-site checks are off by default and send a cleaned page URL to the configured Modal function when enabled.

## Optional integrations and privacy

Baty treats messages, URLs, and retrieved records as untrusted input. Submitted URLs are not automatically opened. User content is not sent to external services by default.

Some features send data externally only after configuration and user selection:

- **Parallel research:** set `PARALLEL_API_KEY` in a local `.env` file. Only submit public material you are comfortable sending to Parallel; the UI identifies the fields sent. Check [current pricing](https://parallel.ai/pricing) before use. Without a key, available research falls back to local records and the local assistant. See the [Parallel API documentation](https://docs.parallel.ai/).
- **URL reputation:** set `GOOGLE_SAFE_BROWSING_API_KEY` and/or `VIRUSTOTAL_API_KEY` in the ignored local `.env` file. Each selected lookup sends only the normalized domain root. Provider terms, quotas, and retention policies apply.
- **Firebase account and backup:** Google sign-in and Q&A backup require Firebase Console setup and deployed database rules. Backup is opt-in and applies to Learning assistant Q&A; it does not sync message text, sender details, URLs, searches, or research activity.
- **Modal assistant:** questions leave the device and are processed by Vercel and Modal. The hosted assistant requires server-side `MODAL_PROXY_KEY` and `MODAL_PROXY_SECRET` settings plus the Vercel hostname in Firebase Authorized domains. See [Modal deployment notes](deploy/README-modal.md).

Never commit API keys, `.env` files, personalized extension profiles, model weights, adapters, checkpoints, or generated datasets.

## Local evaluation and data workflows

Run the offline test suite with:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Run the small, project-authored offline product evaluation with:

```sh
.venv/bin/python scripts/evaluate_cyber_eval.py
```

It writes `reports/cyber-eval-v1.json`. The synthetic examples are diagnostic, not a production estimate; inspect the raw answers and rubrics. No user URLs are fetched.

### URL classifier dataset

The URL dataset is [UCI PhiUSIIL](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset), licensed CC BY 4.0. The source CSV is downloaded into ignored `data/raw/`; only URL text and labels are used.

```sh
.venv/bin/python scripts/download_phiusiil.py
.venv/bin/python scripts/prepare_url_dataset.py
.venv/bin/python scripts/evaluate.py data/processed/phishing --output reports/url-baseline-results.json --save-model models/url-classifier.joblib
```

The evaluation groups rows by approximate registrable domain. A high held-out score on this dated source does not predict live accuracy; the classifier output is uncalibrated and is not a verdict.

### Local security-record search

Fetch and prepare CISA records and build the lexical index with:

```sh
.venv/bin/python scripts/download_kev.py
.venv/bin/python scripts/prepare_kev.py
.venv/bin/python scripts/download_advisories.py
.venv/bin/python scripts/prepare_advisories.py
.venv/bin/python scripts/build_retrieval.py
```

For a bounded Hacker News sample, download a single monthly shard and rebuild the index:

```sh
.venv/bin/python scripts/download_hn_month.py 2026-08
.venv/bin/python scripts/prepare_hn.py data/raw/hacker-news-2026-08.parquet
.venv/bin/python scripts/build_retrieval.py
```

Hacker News content is community discussion, not authoritative evidence. Source identifiers, timestamps, and links are retained where available.

### Training experiments

`data/curated/defensive_seed.jsonl` is a small project-authored smoke-test set, not a production training set. The Trendyol adapter is an isolated experiment and is not enabled by default: its small cybersecurity QA review scored below the base model and found unsupported claims. Keep the base model unless a separately reviewed evaluation clears another adapter. See [the training report](reports/trendyol-m5-training.md).

The following training command is a dry run; add `--run` to execute it. Use a new output directory for each run:

```sh
.venv/bin/python scripts/prepare_curated.py
.venv/bin/python scripts/train_lora.py --model models/Qwen2.5-1.5B-Instruct-4bit --data data/processed/curated --adapter adapters/new-run --config configs/training.yaml
```

## Safety limits

This is a prototype, not a production security decision system. “No threat detected” and “no suspicious indicator” do not establish that a site or message is safe. Verify model answers and research citations. Keep the local API bound to loopback. Optional provider-side URL fetching and DNS behavior are outside Baty's local passive URL checks.

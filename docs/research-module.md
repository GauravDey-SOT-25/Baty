# Web Research and Intelligence Subsystem

## Overview

The Web Research and Intelligence module adds defensive, threat-grounded external intelligence capabilities to the local cybersecurity AI platform. It is modeled on the multi-step research, extraction, monitoring, and enrichment patterns available through [Parallel.ai](https://platform.parallel.ai/), adapted strictly for cybersecurity use-cases and respecting local-first, privacy, and defensive boundaries.

---

## 1. Architecture

```
                   Browser / Client
                          │
                          ▼
            src/api/server.py (ThreadingHTTPServer)
                          │
             ┌────────────┴────────────┐
             │ Research Subsystem API  │
             └────────────┬────────────┘
                          │
                          ▼
             src/research/service.py
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
src/research/ssrf_guard  src/research/task_store  src/research/provider
 (SSRF validation)        (local JSON cache)       (Abstract Provider)
                                                     │
                                 ┌───────────────────┴───────────────────┐
                                 │                                       │
                                 ▼                                       ▼
                     ParallelProvider                   LocalFallbackProvider
                  (src/research/parallel_client)       (src/research/local_fallback)
                                 │                                       │
                                 ▼                                       ▼
                       api.parallel.ai                     Local incident corpus + Qwen LLM
```

### Module Responsibilities

- **`src/research/provider.py`**: Declares standard dataclass schemas (`SearchResult`, `ExtractResult`, `ResearchTaskRecord`, `MonitorRecord`) and the abstract `ResearchProvider` contract.
- **`src/research/parallel_client.py`**: Communicates with Parallel.ai (`/v1/search`, `/v1/extract`, `/v1/tasks/runs`, `/v1/monitors`) using Python standard library `urllib` only (zero extra runtime dependencies). Enforces response size caps, request timeouts, and error normalization.
- **`src/research/local_fallback.py`**: Default zero-configuration provider when `PARALLEL_API_KEY` is not present. Searches local CISA KEV and advisories snapshots, executes local Qwen model generation, and operates fully offline.
- **`src/research/ssrf_guard.py`**: Validates URLs before any outbound extraction request. Rejects non-HTTPS schemes, credentials in URLs, loopback/private/link-local IPv4/IPv6 addresses, cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`), and internal domains.
- **`src/research/task_store.py`**: Thread-safe persistent JSON store (`data/research_tasks.json` and `data/research_monitors.json`) tracking tasks and monitors across restarts. It stores an optional `owner_uid` for future integration, but there is no Firebase authentication and current API routes do not provide an authenticated identity; local history is shared.
- **`src/research/service.py`**: Top-level entry point enforcing input bounds and provider dispatch. Research rate limits are enforced in `src/api/server.py`; prompt-injection pattern rejection currently applies to Deep Research task questions only.
- **`frontend/research.js`**: Vanilla JS frontend matching strict CSP rules (`script-src 'self'`, no inline `onclick`, no `innerHTML`, zero dependencies).

---

## 2. Configuration & API Keys

### Environment Variables

Configuration is read from process environment variables. The app does not load `.env` automatically; `.env.example` is a template only.

| Variable | Description | Default |
|---|---|---|
| `PARALLEL_API_KEY` | API key from [platform.parallel.ai](https://platform.parallel.ai) | *None* (runs in `local-only` mode) |
| `CYBER_MODEL_PATH` | Path to local quantized Qwen model weights | `models/Qwen2.5-1.5B-Instruct-4bit` |
| `CYBER_DATA_PATH` | Storage location for research tasks and incident data | `data/` |

### Setting Up `.env`

For a shell-based setup, copy the template and explicitly export it before starting the app:

```sh
cp .env.example .env
set -a
source .env
set +a
.venv/bin/python -m src.api.server
```

Keep `.env` private and never commit it.

The ordinary test suite is offline. A separate live test module is available
only by explicit opt-in, and creates billable Search, Extract, and Task API
requests:

```sh
set -a
source .env
set +a
PARALLEL_LIVE_TESTS=1 .venv/bin/python -m unittest discover -s tests -p 'test_parallel_live.py' -v
```

The live suite stays skipped unless both `PARALLEL_API_KEY` and
`PARALLEL_LIVE_TESTS=1` are set. Task tests may incur processor-dependent
charges; inspect current provider pricing and account quotas before opting in.
Never paste the API key into source code, issue reports, or chat logs.

If `PARALLEL_API_KEY` is omitted or empty, the entire application starts in `local-only` mode without errors. Unrelated features (message triage, URL syntax inspector, incident search, local learning assistant) remain fully functional.

---

## 3. Features & Usage

### A. Web Search (`POST /api/research/search`)
- Accepts a natural language `query` and optional `search_queries` keywords.
- When live mode is active, queries Parallel's search engine for LLM-optimized excerpts with source citations and publication dates.
- In local mode, searches local CISA KEV and Hacker News corpus via lexical BM25.

### B. Web Content Extraction (`POST /api/research/extract`)
- Accepts a list of up to 20 public HTTPS URLs and an optional `objective`.
- `src/research/ssrf_guard.py` rejects non-HTTPS URLs, credentials, known internal names, non-global IP literals, and ambiguous numeric host forms.
- Rejects plain HTTP to avoid leaking cleartext tokens or headers.
- Truncates individual pages at 50,000 characters to prevent memory exhaustion on Apple Silicon unified memory.

### C. Deep Research Tasks (`POST /api/research/tasks` & `GET /api/research/tasks/{id}`)
- Initiates long-running multi-step research runs.
- Tasks are tracked asynchronously with persistent UUIDs.
- Polling endpoint (`GET /api/research/tasks/{id}`) returns real status (`pending`, `running`, `completed`, `failed`) and cited findings.
- Local fallback uses the local Qwen model and CISA incident records to synthesize a defensive report. Its free-form answer may be inaccurate; returned local citations are lexical matches.

### D. Security Monitoring (`POST /api/research/monitors` & `GET /api/research/monitors`)
- Allows users to register ongoing monitors for software packages, CVEs, or attack campaigns.
- In live mode, creates Parallel `event_stream` monitors with a daily frequency. The UI retrieves recent events only when the user presses **Check for updates**; this app does not run inbound webhooks or push alerts.
- In local mode, tracks configured monitors without polling and states that live scheduled monitoring is unavailable.

### E. Structured Security Record Enrichment (`POST /api/research/enrich`)
- Enriches public vulnerability or advisory records with verified web evidence.
- Accepts strictly public schema fields (`id`, `title`, `vendor`, `product`, `version`, `description`, `source_url`).
- Rejects non-public information, private IP URLs, and unapproved field names.
- Returns schema-validated fields (`affected_products`, `cve_ids`, `severity`, `exploitation_status`, `mitigations`, `vendor_advisory_url`) with citation trails.

---

## 4. Security & Privacy Controls

1. **User-triggered provider calls**: Provider requests happen only after a user submits a Web Research action. The submitted query, URL, or explicitly entered public report fields are sent to the configured provider; do not submit private messages or confidential incident details.
2. **Untrusted content**: Provider results are rendered as text and should be treated as untrusted. The local model prompt labels retrieved records as untrusted, but instruction-pattern rejection is limited and is not a general prompt-injection guarantee.
3. **URL screening limits**: The local validator blocks non-HTTPS URLs, credentials, known local/private/reserved IP literals, ambiguous numeric IP spellings, and common metadata/internal hostnames. Fetching and redirects occur at the provider; this app cannot verify provider-side DNS resolution or redirect protections. DNS rebinding and redirect-to-private-host behavior were not tested against Parallel; local syntax checks are not proof the destination is safe.
4. **Content Security Policy (CSP)**: The frontend uses same-origin scripts, no inline handlers, and no `innerHTML` insertion for provider data.
5. **Rate limiting**: In-memory per-IP limits apply to research routes as a modest cost-control measure; they are not authentication and localhost clients share the same loopback IP.
6. **No secret leaks**: The API key is read from process environment and is never returned in API responses or request logs. There is no authentication or multi-user authorization; keep the server bound to loopback.
7. **Local storage and retention**: Research JSON files are written atomically with owner-only (`0600`) file permissions on supported POSIX filesystems. Data persists indefinitely until manually removed from `data/research_tasks.json` and `data/research_monitors.json`; there is no automatic retention or account-level delete flow. Back up or remove these files deliberately, and do not expose the machine account to untrusted local users.
8. **Identity boundary**: Firebase is not configured or implemented. The current local prototype has no verified user identity, so task and monitor ownership is not enforced by the HTTP API; records are shared among local callers. `owner_uid` is reserved metadata only and must not be treated as a security control. Do not expose this service publicly.

---

## 5. Testing

Run all offline unit and mocked integration tests:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Provider behavior is verified using mocked responses and the local fallback. `tests/test_parallel_live.py` is separate and skipped by default; run it only with explicit `PARALLEL_LIVE_TESTS=1` and a configured key because its Search, Extract, and Task checks may incur charges. No live API test was run for this milestone because no key was configured. Provider-side URL screening, DNS resolution, and redirect safety cannot be independently verified here.

### Local startup

From the project root:

```sh
.venv/bin/python -m src.api.server
```

The development server binds to `127.0.0.1:8765`. Keep it on loopback; authentication is not implemented.


## Parallel-style workspace additions

The home screen provides a security-focused playground for Search, Responses, Extract, Task, FindAll, and Monitor. Live calls are explicit user actions. Submitted questions, URLs, objectives, and selected public record fields are sent to Parallel when its API key is configured; calls can incur charges. The local model, message checker, passive URL parser, OCR, and local record search remain separate.

- Responses uses `POST /v1/responses`, `model: "parallel"`, `reasoning.effort` (`low`, `medium`, `high`), the Bearer API-key header, and a 120-second timeout. Citation URLs and titles are read from `url_citation` annotations.
- FindAll uses the documented beta paths `/v1beta/findall/ingest`, `/v1beta/findall/runs`, status retrieval, and `/result`. The UI shows the suggested schema for user review and defaults to `preview` before allowing a run.
- Official API references: [Responses quickstart](https://docs.parallel.ai/responses-api/responses-quickstart), [Responses citations](https://docs.parallel.ai/responses-api/features/citations), and [FindAll quickstart](https://docs.parallel.ai/findall-api/findall-quickstart). FindAll remains beta and its contract can change.
- No live requests are used in the ordinary tests. Do not paste private incident content into live research workflows.

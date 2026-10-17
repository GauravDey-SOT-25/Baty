# Local model deployment readiness

**Status: not ready for production security decisions. Suitable only for a local, supervised hackathon demonstration.** The app remains bound to `127.0.0.1`; it must not be exposed publicly.

## Changes in this readiness pass

- Added a local assistant status indicator backed by the health endpoint. It reports whether the model directory and MLX runtime are present and whether an adapter is enabled.
- Hardened the loopback HTTP boundary: only requests with the expected `127.0.0.1:<port>` Host are accepted, cross-origin POSTs remain rejected, and the server refuses non-loopback binds. This blocks the DNS-rebinding case where an attacker-controlled Host and Origin previously matched each other.
- Bounded local request handling: 32 concurrent HTTP workers by default, 15-second socket timeout, strict `Content-Length`/no `Transfer-Encoding` framing, a 32 KiB body cap, and per-client API rate limits (assistant 12/minute; incident search 60/minute; other local APIs 120/minute). These are resource controls, not identity or access control. Model health now reports available only when config, tokenizer, and at least one safetensors file are present.
- Added an opt-in checkbox for local security-record retrieval. General defensive education can now reach local inference without unrelated lexical records taking over the response. Explicit CVE and current/product-specific requests still require local evidence or abstain.
- Added a bounded MLX repetition penalty (1.08 over a 128-token context). In a local smoke request, this reduced repeated nonce explanations to one concise answer. This is a decoding adjustment, not evidence of better factual accuracy.
- The running demo uses the unadapted 4-bit Qwen base model. The Trendyol LoRA adapter remains in its experiment directory and is not selected.

## Evidence and limitations

- The existing Trendyol test split shows lower token loss for the adapter (1.809 vs. 3.119 base), but the split is small and from the same source. This measures imitation of that dataset, not security correctness.
- The saved eight-question subjective QA review scored raw base 2/8 and the adapter 1/8. The adapter made an unsafe HTTPS claim and invented a patch date. These results do not support enabling it.
- In the fixed 40-example evaluation run saved as `cyber-eval-readiness.json`, message metrics remain precision 0.533, recall 1.0, F1 0.696, false-positive rate 0.875, accuracy 0.563; URL metrics remain precision 0.571, recall 1.0, F1 0.727, false-positive rate 0.75, accuracy 0.625. These classifier results are not changed by the assistant work.
- The eight current app-wrapper answers match the existing deterministic guardrail behavior and the same single-pass rubric review scored 8/8. This is a tiny project-authored set, the review was not independent, and it does not establish general QA reliability. Direct raw base-model outputs still contain unsafe or unsupported claims.
- The current local generation smoke answer was plausible but unverified. Answers marked `general_model_knowledge_unverified` must not be treated as advice for incident response or production changes.
- Parallel live requests were not made. No model was retrained, no weights changed, and no external API cost was incurred in this readiness pass.

## Retrieval evaluation and diagnostics (2026-10-17)

- Added an offline 25-query retrieval evaluation from pinned IDs in the local CISA KEV/advisory snapshot, with authored queries, source IDs/URLs/dates/license notes and SHA-256 hashes. It is separate from and did not change the fixed 40-example baseline.
- Same-corpus retrieval result: micro precision 0.944 (17 TP / 1 FP), recall 1.000, F1 0.971; 8/8 ambiguous/negative queries abstained; source URL attribution 17/17; the one missing-CVE wrapper case abstained. Exact-CVE and advisory subsets scored 1.000; relevant paraphrases had precision 0.889 / recall 1.000. The extra result is a second Palo Alto PAN-OS injection record for a PAN-OS code-injection query. It may be useful related context, but strict target labels count it as a false positive; independent review should decide whether to broaden that label.
- These are authored diagnostic cases over one local corpus snapshot, not independent or representative measurements. No contradictory-source pair or sufficiently broad QA factuality set is included. `docs/evaluation.md` documents metrics, provenance, reviewer rubric and reproduction commands.
- A local exact/near-duplicate prompt audit compared both evaluation files against existing train/validation/test user prompts (796/100/100): no exact or >=0.80 3-gram Jaccard matches. This cannot rule out paraphrase or answer leakage.
- Error diagnosis: retrieval abstains on broad/common queries and matches selected exact identifiers, but domain paraphrases need independent relevance judgments. Raw model unsupported-claim and HTTPS/patch-version failures remain model limitations. Wrapper performance is largely deterministic guardrails and is not evidence of model improvement. Message and URL false positives remain separate classifier problems (87.5% and 75%, respectively) and this work does not reduce them.
- LoRA is not justified now: the existing adapter had a worse subjective QA result than base (1/8 vs 2/8), and this retrieval benchmark does not evaluate model generation. Improve/review data and establish a larger held-out answer benchmark before any further tuning.

## Modal observation preview (2026-10-17)

- Prepared a separate protected Modal CPU inference preview in `deploy/modal_app.py`; this is not deployment of the full application. It uses the public base model at a pinned Hugging Face revision and a persistent Modal cache volume. It sends only request prompts to Modal when the user calls it and excludes local model files, adapters, local corpus, training/evaluation data, and `.env`.
- Modal's current public Web Functions require explicit proxy-auth configuration to avoid public unauthenticated access; the preview sets `requires_proxy_auth=True`. It caps request bodies and tokens, limits to one container, and scales down. GPU is disabled; cloud CPU/memory and persistent storage may still be billed.
- At the time of initial preparation, Modal CLI 1.6.2 was installed in the ignored local `work/modal-cli-venv` but no profile was authenticated, so no remote app or cache existed. Authentication later became available and the subsequent deployment and smoke-test results are recorded below.
- Even after deployment, this preview would expose only raw-model inference, without local retrieval/classifiers or a user-facing UI. Model answer quality and the full application's production blockers remain unresolved.

### Ready-to-post preparation update (2026-10-17)

- Added `deploy/post_to_modal.sh`: one-command deploy after Modal CLI login, with the auth check's output suppressed so tokens/profile details are not printed. The script deploys the preview only; it does not package local project data.
- The Modal model-cache Volume now uses `create_if_missing=True`, so the cloud-side cache is provisioned during deployment rather than requiring a separate manual setup command.
- The initial PyPI resolver dry run passed for the pinned package versions but surfaced that the generic PyTorch wheel brought CUDA libraries; the actual Modal build exposed this. The subsequent build used `torch==2.14.1+cpu` from the official PyTorch CPU index and completed without CUDA packages.
- Deployed the authenticated preview as `cyber-qwen-modal-preview` at `https://gauravdey2020--cyber-qwen-modal-preview-inference-api.us-east.modal.run`; dashboard: `https://modal.com/apps/gauravdey2020/main/deployed/cyber-qwen-modal-preview`.
- The first image attempt selected the default CUDA-enabled PyTorch wheel and began pulling multi-gigabyte CUDA dependencies. I aborted that build before the image was saved, then pinned the official CPU-only `torch==2.14.1+cpu` wheel. The successful CPU image downloaded a 187.2 MB Torch wheel and no CUDA packages.
- Modal created and mounted the named persistent cache Volume on first health request, fetched the pinned public Hugging Face model revision, and reported the model loaded on CPU. The first health request took 37.7 seconds; a later authenticated health request returned HTTP 200.
- An authenticated benign software-signature canary returned HTTP 200 and `answer_basis=general_model_knowledge_unverified`. Modal logged 30.6 seconds of model execution (46.3 seconds total endpoint duration); the answer reached the 96-token cap mid-response. This shows the API path works, not that the answer is complete or factually dependable.
- Modal CLI `modal curl` returned “missing credentials for proxy authorization”. A temporary Modal Proxy Token was created for the smoke test and deleted immediately after; users need their own Proxy Token to invoke the protected endpoint. See `deploy/README-modal.md` for safe local CLI use.
- The deployment is an inference-only, protected cloud preview, not the full application or production security service. The model, cache and active inference are remote; requests sent to the endpoint are processed by Modal. The local UI, adapter, retrieval corpus and classifiers remain local and are not included. The earlier production-readiness assessment is unchanged. Final local verification after deployment fixes: `.venv/bin/python -m unittest discover -s tests -q` ran 86 tests (83 passed, 3 optional live tests skipped); `.venv/bin/python -m compileall -q src tests scripts deploy`, `sh -n deploy/post_to_modal.sh`, `git diff --check`, and `.venv/bin/python -m pip check` all passed.

## Verification

- `.venv/bin/python -m unittest discover -s tests -q`: 78 tests run, 75 passed and 3 optional live tests skipped.
- `.venv/bin/python -m compileall -q src tests scripts`: passed.
- `git diff --check`: passed.
- `.venv/bin/python -m pip check`: passed (`No broken requirements found`).
- API hardening regression tests cover rejected transfer encoding, API throttling, incomplete model files, and positive bounded-worker configuration.
- `.venv/bin/python -m pip check`: passed. `pip-audit 2.10.1` ran in an ignored scratch virtual environment against both `requirements.txt` and `.venv/lib/python3.15/site-packages`; both scans reported “No known vulnerabilities found.” This is an advisory database result, not a guarantee that dependencies are secure.
- Local HTTP health and assistant inference were verified on loopback with the base model; no URL was opened or resolved.

## Gate before production

Do not deploy this model for autonomous or high-impact security decisions. Before reconsidering, obtain an independent cybersecurity review of a larger held-out benchmark with adversarial and ordinary defensive questions, measure unsupported-claim and abstention rates, reduce classifier false positives, and validate operational security for the intended deployment boundary. Do not re-enable the adapter unless it passes those gates.

## External security references

- [NIST SP 800-218 SSDF](https://csrc.nist.gov/pubs/sp/800/218/final) for secure development and release practices.
- [OWASP ASVS 5.0.0](https://owasp.org/projects/asvs) for web application security verification.
- [OWASP GenAI Security Project, 2025 Top 10](https://genai.owasp.org/resource/owasp-top-10-for-large-language-model-applications-2025/) for prompt injection, unbounded consumption, supply-chain, and overreliance risks.

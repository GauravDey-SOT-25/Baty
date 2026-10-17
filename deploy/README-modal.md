# Modal inference preview

**Current deployment:** `cyber-qwen-modal-preview` is deployed and authenticated at [the Modal dashboard](https://modal.com/apps/gauravdey2020/main/deployed/cyber-qwen-modal-preview). Its endpoint is `https://gauravdey2020--cyber-qwen-modal-preview-inference-api.us-east.modal.run`. Health and one benign inference were verified on 2026-10-17. This endpoint is a cloud service; requests leave your laptop and are processed by Modal.

This is a **separate, authenticated cloud inference preview** for observing Modal, not a cloud migration of the local-first application. Firebase Google sign-in ID tokens are signature-verified in the Modal app, restricted to project `baty-ac397`, and checked for the expected issuer, Google provider, and verified-email claims. Each UID is limited to 3 inference requests per minute. The Modal Proxy Token remains required at the edge as a second security layer. It runs the public, Apache-2.0 Qwen2.5-1.5B-Instruct base model on Modal CPU workers. It uses the CPU-only PyTorch wheel, not CUDA libraries. It does not use the local MLX weights, the Trendyol adapter, local CISA/Hacker News corpus, classifier data, training data, `.env`, or any other local user data. The base model is fetched by the remote container from the pinned official Hugging Face revision and cached in a persistent Modal Volume.

The protected API accepts a verified Firebase Google ID token plus a question and returns an **unverified model answer**. The request is processed by Modal cloud infrastructure. Send only non-sensitive canary questions; never send private messages, URLs, incident details, credentials, or customer data. No public browser UI is included, so proxy credentials stay out of JavaScript.

## Modal behavior to observe

- First request can have a cold start while the CPU container starts and the pinned model downloads into the Volume.
- Later requests can reuse the cached weights; the single-container cap limits horizontal scaling and the 120-second scaledown window avoids keeping an idle worker warm indefinitely.
- Modal provides deployment state, container logs and resource metrics in its dashboard/CLI. The code logs model startup only and never prints request text.
- This is CPU-only to avoid GPU billing during the preview. The current pricing page lists CPU at `$0.0000131` per physical core-second and memory at `$0.00000222` per GiB-second; the configured 4 CPU cores and 16 GiB would be about `$0.0000879/second` while active, before credits or other charges. The current Starter plan advertises `$30/month` in compute credits, but account eligibility and billing must be checked in the Modal dashboard. The model cache Volume persists and should be deleted manually if no longer wanted; deletion can have billing delay. Pricing changes, so check the [Modal pricing page](https://modal.com/pricing) first.

## Deploy after Modal account setup

The Modal CLI 1.6.2 is installed in the ignored local environment `work/modal-cli-venv`. From the project root, sign in once and deploy:

```sh
work/modal-cli-venv/bin/python -m modal setup
deploy/post_to_modal.sh
```

The deploy command creates the persistent `cyber-qwen-hf-cache` volume on Modal if it does not exist. It does not copy or upload the local model cache. The first remote container downloads the pinned public model revision into that cloud volume. Review your Modal account budget and data handling before deploying.

The endpoint requires a Modal Proxy Token at the platform edge and a valid Firebase Google ID token in `Authorization: Bearer …`. Do not remove `requires_proxy_auth=True` or make this preview unauthenticated. The local app keeps the Modal Proxy Token server-side and sends only the Firebase ID token from its sign-in session. Modal CLI `modal curl` did not attach credentials during the smoke test, so use a Proxy Token created in your Modal workspace. The temporary smoke-test token was deleted immediately afterward. Create your own token with:

```sh
work/modal-cli-venv/bin/python -m modal workspace proxy-tokens create --name cyber-qwen-client
```

Store the one-time `Modal-Key` and `Modal-Secret` securely. In Bash, set `MODAL_PROXY_KEY` and `MODAL_PROXY_SECRET` in the current shell, then use:

```sh
URL='https://gauravdey2020--cyber-qwen-modal-preview-inference-api.us-east.modal.run'
printf 'header = "Modal-Key: %s"\nheader = "Modal-Secret: %s"\n' "$MODAL_PROXY_KEY" "$MODAL_PROXY_SECRET" | \
  curl --silent --show-error --config - "$URL/health"
unset MODAL_PROXY_KEY MODAL_PROXY_SECRET
```

Use the local app's Learning assistant to test inference: sign in with Google, select **Use the Modal cloud model**, and submit a harmless, non-sensitive question. This route requires both the Firebase ID token and Modal Proxy Token and has a per-user rate limit. The API rejects direct requests lacking a valid Google Firebase ID token.

Use `work/modal-cli-venv/bin/python -m modal app logs cyber-qwen-modal-preview` to view logs and `work/modal-cli-venv/bin/python -m modal app dashboard cyber-qwen-modal-preview` to open deployment metrics. Never paste proxy credentials into chat, JavaScript, or public places. `modal app stop cyber-qwen-modal-preview` stops the deployed app; it does **not** remove the persistent model cache volume. Delete `cyber-qwen-hf-cache` separately only when you intentionally want to remove the cloud cache.

## Local app integration

The local UI can call Modal only through the loopback API. A dedicated Modal Proxy Token is configured in the ignored project `.env` as `MODAL_PROXY_KEY` and `MODAL_PROXY_SECRET`; keep the file owner-only (`chmod 600 .env`). The integration never puts these Modal credentials into browser JavaScript. The local account panel uses Firebase Google sign-in; when the cloud model toggle is selected, the browser forwards its short-lived Firebase ID token and question to the loopback API, which relays both to the fixed Modal endpoint. If the optional database-backup checkbox is off, the Q&A is not saved to Realtime Database.

Complete the Firebase Console provider and authorized-domain setup in [the Firebase integration guide](../docs/firebase-auth-and-sync.md). The Modal API verifies the token signature with Google's published Firebase certificates and validates project, issuer, UID, Google provider, and verified-email claims. It does not use a Firebase Admin service-account key. A Firebase ID token can remain valid until expiry if an account is disabled or its session is revoked; this preview does not perform Firebase Admin revocation checks.

## Scope and release gate

This preview is not production cybersecurity deployment. It now authenticates end users through Firebase Google sign-in, but has no per-user persistence, local retrieval, message/URL classifiers, sustained abuse monitoring, independent model validation, or hosted copy of the existing UI. It uses the raw base model; it does not deploy or test the LoRA adapter. Treat the answers as unverified. Review Modal account budget and data handling before making real requests. The app source is in `deploy/modal_app.py`; no local model, dataset, or private environment file is packaged by the image definition.

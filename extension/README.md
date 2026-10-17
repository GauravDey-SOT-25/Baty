# Baty browser extension

A small Manifest V3 popup for submitting a pasted suspicious message or URL to the deployed Cyber-Qwen Modal app. Manual text is sent only after clicking **Analyze with Cyber-Qwen**. Optional **Auto-check the active site** mode checks the active HTTP/HTTPS tab when you visit or switch pages. It sends only the page URL, with credentials, query strings, and fragments removed; it never reads page contents. Auto-check is off until enabled, and can be switched off any time.

## Load in Chrome or Edge

1. Open `chrome://extensions` (or `edge://extensions`).
2. Turn on **Developer mode**.
3. Choose **Load unpacked** and select this `extension` folder.
4. Open the extension and click **Analyze with Cyber-Qwen**, or enable **Auto-check the active site** once to check active pages automatically.

The function endpoint is prefilled as `https://gauravdey2020--cyber-qwen-modal-preview-inference-api.us-east.modal.run/api/assistant`. Change it under **Connect Modal function** if the deployment URL changes. If you paste only the function root URL, the extension adds `/api/assistant`, the route served by this deployment. The extension asks for access to the configured endpoint host. Auto-check also asks for permission to read active-tab URLs. The service worker posts `{ "question": "..." }` and accepts a response containing `answer`, `response`, `output`, `text`, or `message`.

If the function returns a different schema, update the request/response handling in `background.js`. The UI reports connectivity failures instead of generating a fake analysis.

### Modal returns 401

The deployed `inference_api` keeps `requires_proxy_auth=True`, so Modal Proxy Token authentication protects the handler. The handler accepts `{ "question": "..." }` and returns an `answer` field.

For a private hackathon demo, this extension accepts a combined Proxy Token in **Connect Modal function** as `wk-<id>.ws-<secret>`. Create one at **Modal Settings → Proxy Tokens**; if prompted to scope it, allow the `main` environment. It sends the ID and secret in Modal's `Modal-Key` and `Modal-Secret` headers. The deployed handler uses Modal Proxy auth and does not require a separate Firebase sign-in. The `ak-` / `as-` API tokens are different credentials and cannot authenticate a web-function request. The extension stores the proxy token in local extension storage, which is inspectable on this browser; do not publish or share a build containing it. For a production extension, put the token behind a server-side proxy instead.

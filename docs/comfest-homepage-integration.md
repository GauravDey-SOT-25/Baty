# Comfest homepage integration

Updated 2026-10-17.

## Entry points

- `http://127.0.0.1:8765/` serves the repository-root `index.html` as the main site; Comfest styles, scripts, images, and secondary pages remain in `Comfest - 26/`.
- `http://127.0.0.1:8765/workspace` serves the previous Cyber Desk UI, retaining the full Parallel research and Firebase account workflows.
- Both pages use the same loopback API. The Comfest page loads its own styles and scripts from the extracted site folder, while reusing the existing local trust-registry browser client.

## Tools embedded on the main page

- Passive URL syntax inspection (`POST /api/url`); no URL resolution or fetch.
- Local message analysis (`POST /api/message`).
- Local Qwen question answering with optional local-record retrieval (`POST /api/assistant`).
- Search of the installed local records snapshot (`POST /api/incidents`).
- Local OCR for user-selected images (`POST /api/ocr`); image bytes go only to the loopback server. The extracted text is shown before the user chooses to insert it into a question.
- Private user-maintained trust notes. Passive registry lookups are local. TLS handshakes and domain-root reputation checks remain separately selected and off by default.
- A link to `/workspace` keeps provider-backed Parallel research available with its existing disclosure and explicit submit action.

The Comfest hero and type styles now use local assets and system font fallbacks. User-provided URLs are never automatically opened. No provider request, model change, training, credential reuse, or deployment was part of this integration. The historical blockchain prototype remains a separate archive page and is explicitly labeled disconnected from the running app.

## Verification

Run the full offline project suite with `.venv/bin/python -m unittest discover -s tests -q`, Python compilation with `.venv/bin/python -m compileall -q src tests scripts`, and `git diff --check`. `tests/test_api.py` verifies that `/` serves Comfest, `/workspace` serves the former application UI, and the Comfest styles/scripts and hero asset are served by the loopback backend.

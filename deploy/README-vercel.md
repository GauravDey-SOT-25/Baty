# Vercel hosted preview

This configuration deploys a **limited hosted preview**, not the laptop application. It serves the Comfest/Baty pages, blockchain prototype page, and a Google-authenticated Qwen assistant proxied through the existing Modal inference endpoint. It does not deploy MLX, local model weights/adapters, local security records, URL/message classifiers, OCR, local trust storage, or the Parallel research backend.

## Vercel project configuration

1. Import `GauravDey-SOT-25/Baty` from GitHub, or open the already-created project.
2. Keep the repository root as the Root Directory (`.`) and select **Other** as the framework. Do not select Services; this app uses a static build and one Node function.
3. Use the build command and output directory in the checked-in `vercel.json`: `node scripts/build-vercel.mjs` and `dist/vercel`.
4. Add these project environment variables for Production and Preview. Use a dedicated Modal Proxy Token for Vercel; copy the key and secret directly from the Modal dashboard into Vercel's encrypted Environment Variables form. Do not put them in Git, browser code, or chat.
   - `MODAL_PROXY_KEY`
   - `MODAL_PROXY_SECRET`
5. Deploy. After the Vercel URL exists, add its hostname (for example, `baty.vercel.app`) to Firebase Authentication's Authorized domains and ensure Google sign-in is enabled. The hosted assistant otherwise shows a clear Firebase authorization error.
6. Redeploy after changing environment variables. Test the landing page, `/blockchain.html`, `/assistant.html`, the unauthenticated API rejection, and sign-in/inference after Firebase and Modal configuration.

## Data flow and limits

- `/api/modal/assistant` accepts POST only, validates a short question and bearer token, sends only the question plus Firebase ID token to the fixed Modal URL, and keeps Modal proxy credentials server-side.
- Modal verifies the Firebase token and applies its per-user rate limit. This Vercel route does not persist questions or answers.
- The hosted assistant has general model knowledge only. It has no retrieval or live research, and every response is labeled unverified.
- Do not submit private incident information, credentials, or personal data. The question leaves the browser and is processed by Vercel and Modal.
- URL/message checks, local records, OCR, trust notes, and research controls are disabled or clearly unavailable on the hosted page; use the local app for those features.
- Vercel Hobby function duration is capped at 300 seconds, and first Modal startup can be cold. Inference can time out during provider or platform incidents.
- Firebase client configuration in `assistant.js` is public browser configuration. Access control relies on Firebase Authentication and Modal's server-side token verification; never put Modal keys in that file.

## Deployment status in this workspace

The deploy configuration is prepared, but this workspace has no Vercel CLI session or `VERCEL_TOKEN`. Therefore no Vercel deployment has been created from here. Vercel account authentication, the two encrypted Modal environment variables, and Firebase Authorized Domains must be configured before the preview can answer questions. See [Modal deployment notes](README-modal.md) for endpoint and cost details.

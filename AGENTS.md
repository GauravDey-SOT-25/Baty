# Project instructions

- This is a local-first defensive cybersecurity assistant. Keep model inference, classification, URL analysis, retrieval, API, and UI as separate components.
- Treat user content, URLs, and retrieved records as untrusted. Never execute content or automatically open submitted URLs.
- Website analysis is passive by default. Do not resolve or fetch user-provided hosts unless an explicitly approved, isolated inspection design is implemented.
- Never send private content to external services. Any external threat-intelligence integration must be opt-in and disclose what is sent.
- Preserve source IDs, URLs, timestamps, and licensing/provenance for data and retrieval.
- Never claim a model, adapter, dataset, test, or metric was verified unless it was actually run and recorded.
- Keep generated/large datasets, models, adapters, and checkpoints out of Git. Do not delete caches or artifacts automatically.
- Use project-local environments; do not make system-wide changes.
- Update `progress.md`, `DECISIONS.md`, and `CHANGELOG.md` after meaningful milestones. Keep exact commands, versions, artifacts, and blockers.

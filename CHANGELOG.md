# Changelog

## 2026-10-17

- Established the local project, environment notes, baseline source layout, and persistent project instructions.
- Implemented loopback-only app/API, message triage, passive URL analysis, local retrieval, and a learning assistant.
- Downloaded and verified local inference for the pinned 4-bit Qwen2.5-1.5B model after explicit user approval.
- Added provenance-preserving CISA KEV/advisory and filtered Hacker News retrieval data. The Hacker News corpus is a single pinned monthly shard and is treated as anecdotal.
- Built and evaluated a character n-gram URL classifier using UCI PhiUSIIL with domain-grouped splits; documented limitations and source license.
- Audited candidate instruction data, excluded unsuitable external instruction samples from training, and ran a small LoRA smoke experiment on manually authored examples. The adapter did not materially improve held-out responses and is disabled.
- Grounded retrieved answers in local record fields, restricted explicit CVE queries to exact-CVE records, and added deterministic responses for several defensive safety cases.
- Latest verification: 29 unit tests pass. Local model generation was verified; generated answers remain fallible and the app is a local research prototype, not an autonomous security decision system.

# Dataset audit

Updated: 2026-10-17. Dataset records are stored locally under ignored `data/raw/` and `data/processed/`; none are committed to Git.

## Instruction-tuning candidates

### Trendyol cybersecurity instruction dataset

- Apache-2.0; pinned revision `357544e7576607d88eaeac9b0adb07e9fd8bb2bb`.
- A bounded, evenly spaced 1,000-row sample had no malformed or exact duplicate rows, but 998 unique prompts included two conflicting-answer prompt groups (four records excluded).
- Automated flagging found internal-reasoning style phrases in 30/1,000 sampled assistant answers and placeholder language in 3. Six manually inspected examples included apparent factual errors, confused PtT/PtH terminology, and one answer written in internal reasoning style. Do not use this sample for fine-tuning.
- The sample remains in ignored local raw/processed files for provenance. The fixed 796/100/100 split is not used for training.

### Heimdall defensive cybersecurity dataset

- Apache-2.0; pinned revision `c731f81fa7c263fc94515564a81b29652a885d28`.
- Retrieved 500 evenly spaced training rows through the Hugging Face datasets-server. Schema: system/user/assistant plus provenance; no missing fields or exact duplicate rows in this sample.
- Twelve evenly spaced rows were spot checked. The content is long, specialized and answer plausibility could not be consistently verified from the examples alone. Do not use this sample for fine-tuning until broader expert review.

### Project-authored training smoke set

- A manually authored set of 36 brief defensive answers was split by topic into 24 train, 6 validation and 6 held-out test examples. It was used only to verify MLX-LM training, adapter saving/loading and recovery. It is not a cybersecurity knowledge benchmark and is far smaller than a production training corpus.

## URL classifier dataset

### UCI PhiUSIIL Phishing URL (Website)

- [UCI dataset 967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset), CC BY 4.0; last updated 2024-05-12. Dataset reports 235,795 URL/website rows and labels `1=legitimate`, `0=phishing`.
- Downloaded the official 56,854,345-byte CSV. Only the raw URL and label were used. Webpage-derived features were not used.
- URL query parameter values are replaced with `REDACTED`; fragments are removed. After this normalization and exact deduplication, 234,457 unique records remained; no malformed/missing rows or duplicate-label conflicts were observed.
- Splits: 188,138 train / 26,281 validation / 20,038 test. Group split by an approximate registrable-domain function and no group overlap. The suffix list covers common multi-label suffixes; it is not a complete Public Suffix List, so some domain leakage remains possible for unusual suffixes.
- One internal held-out result is recorded in `url-baseline-results.json`. It is a single-source, dated dataset result and should not be interpreted as expected real-world performance. The data distribution may make this task easier than live, out-of-distribution URLs.

## Retrieval sources

### CISA Known Exploited Vulnerabilities and advisories

- Downloaded the CISA KEV JSON snapshot released 2026-10-16 (1,748 records) and the CISA cybersecurity advisories RSS snapshot (30 entries).
- Records preserve CVE IDs, dates, actions, titles, publisher links and feed release timestamps. The feed summaries are normalized as text; the app does not fetch links from records.
- Source pages: [CISA KEV catalog](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) and [CISA cybersecurity advisories](https://www.cisa.gov/cybersecurity-advisories).

### Hacker News community records

- The dataset card declares ODC-By 1.0 and states original authors retain rights in submitted content. The full archive is reported as about 12.4 GB; it was not downloaded.
- The HF datasets-server currently returns a `CreateCommitError` for both `default` and `today` rows. To make progress without the full archive, one pinned monthly Parquet shard was downloaded: August 2026, 103,240,376 bytes, with 265,364 rows.
- A lexical filter selected 2,581 records (235 stories, 2,346 comments). The pipeline retains author, item ID, timestamp, score, parent/child IDs and HN item URL. The outbound story URL is recorded but never fetched.
- These are community discussions and are marked as unverified. Local retrieval returns short snippets with attribution; no redistribution is intended.

## Excluded candidates

- `cybersectony/PhishingEmailDetectionv2.0`: no license declaration and card/schema/split metadata conflict. Not downloaded.
- PhreshPhish: CC BY 4.0 with anti-phishing-research-only statement, but the Parquet data is 36.6 GB and contains large HTML. Not downloaded.
- Other mirrors with unverified upstream rights were not selected.

## Reproducibility

See `scripts/download_phiusiil.py`, `scripts/prepare_url_dataset.py`, `scripts/download_kev.py`, `scripts/download_advisories.py`, `scripts/download_hn_month.py`, `scripts/prepare_kev.py`, `scripts/prepare_advisories.py`, `scripts/prepare_hn.py`, and `scripts/build_retrieval.py`. All externally sourced data remains ignored by Git.

Machine-readable counts and hashes are in `dataset-statistics.json`.

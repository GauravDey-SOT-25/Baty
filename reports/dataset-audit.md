# Dataset audit status

Date: 2026-10-17. This is repository-card discovery, not a sample-level audit. No dataset was downloaded.

## Trendyol cybersecurity instruction dataset

- Hugging Face card exists and declares Apache-2.0.
- Card reports 53,202 English examples and `system`, `user`, `assistant` columns. The viewer showed 53.2k rows; detailed card claims include 90/5/5 splits, but the viewer displayed a single `train` split. This discrepancy must be resolved by inspecting repository files before relying on card split claims.
- Card includes its own responsible-use/limitations sections. Samples, duplicates, malformed records, answer quality, and unsafe/inaccurate content have not been examined.
- Candidate for a small audited subset only after sample inspection.

## PhishingEmailDetectionv2.0

- Hugging Face card exists; it describes English `content` and `labels`, with labels `legitimate_email`, `phishing_email`, `legitimate_url`, `phishing_url`.
- Card reports 200,000 records: 22,644 email and 177,356 URL samples.
- A license declaration was not visible in the reviewed page output. Do not use for training or redistribution until license/terms are established.
- URL and email rows must be separated. Card-reported balance, dates, duplicates, leakage, missing values, and actual label semantics are not independently confirmed.

## Hacker News mirror

- Card declares ODC-By 1.0; it also says original posts/comments retain the respective authors' rights.
- Card reports a 12.4 GB archive. No full download will be performed. Future ingestion should use bounded streaming/selective retrieval and retain item IDs, parent IDs, time, score, URL, and provenance where available.
- Community anecdotes are not authoritative and need corroboration.

## Pipeline

- [`scripts/download_datasets.py`](../scripts/download_datasets.py) streams a bounded sample and requires an explicit license-review acknowledgment.
- [`scripts/prepare_data.py`](../scripts/prepare_data.py) normalizes instruction records, removes exact duplicates, and writes deterministic train/valid/test splits for at least ten records.
- [`scripts/audit_data.py`](../scripts/audit_data.py) reports schema, missing cells, labels, and exact duplicate count for local JSONL/CSV.
- Bounded sample files and statistics were generated later (see findings below). Near-duplicate, time-based, and source-based leakage checks remain to be implemented before any serious evaluation.

## Sources

- [Trendyol dataset card](https://huggingface.co/datasets/Trendyol/Trendyol-Cybersecurity-Instruction-Tuning-Dataset)
- [PhishingEmailDetectionv2.0 card](https://huggingface.co/datasets/cybersectony/PhishingEmailDetectionv2.0)
- [Hacker News dataset card](https://huggingface.co/datasets/open-index/hacker-news)

## Bounded sample findings (2026-10-17)

- Retrieved 1,000 evenly spaced rows from Trendyol revision `357544e7576607d88eaeac9b0adb07e9fd8bb2bb` through the dataset-server API, preserving row indices and revision metadata. This avoided downloading its single 195 MB source file.
- In the sample, all required fields were populated, with no malformed or exact duplicate full rows. There were 998 unique user prompts; two prompt groups had conflicting assistant answers (four records), so all four were excluded from the prepared split.
- Many fields contained literal `\\n` sequences where formatted line breaks appear intended. The untouched raw file is preserved. The processed copy converts only these sequences to line breaks and records the count for each record.
- A keyword scan found occurrences of terms such as `exploit`, `evasion`, `credential theft`, and `ransomware`. These are review flags, not unsafe labels. The corpus itself uses defensive framing, but the technical accuracy of its answers has not been verified.
- Prepared split counts after duplicate-prompt conflict exclusion: 796 train, 100 validation, 100 test. The test split is held out; it has not been used for training or evaluation.
- For the phishing dataset, the repository API reports `content`/`label` and 120k/20k/60k train/validation/test rows, while the dataset card claims `content`/`labels` and 22,644 email plus 177,356 URL rows. The repository has no explicit license field. Three viewer samples were URLs with integer labels. It is blocked pending license resolution and schema/distribution audit.

## Alternatives discovered

- `phreshphish/phreshphish` declares CC BY 4.0 and an anti-phishing-research-only use condition. The HF dataset-server reports 666,315 rows and 36,576,373,578 Parquet bytes, with eight fields including raw HTML. One sampled HTML cell was over 500 KB. It is not suitable to download wholesale on this machine; selective URL/label extraction requires a method that does not transfer full HTML.
- `alperozyyurt/phishurl-dataset` is tagged `other` with unresolved source licensing; its card explicitly says not to assume an open license.
- `flwrlabs/fed-phishing-urls` declares Apache-2.0 and reports URL/label/client_id schema, but it derives from another source with no license and from the ealvaradob dataset. It is not selected until source redistribution rights are resolved.
- `ealvaradob/phishing-dataset` declares Apache-2.0; its URL-only JSON is 73,157,496 bytes and its card documents multiple upstream Kaggle/Mendeley sources. It remains a candidate with source-rights and temporal quality caveats; no content has been downloaded.

Machine-readable counts and caveats are in [`dataset-statistics.json`](dataset-statistics.json) and [`trendyol-sample-audit.json`](trendyol-sample-audit.json).

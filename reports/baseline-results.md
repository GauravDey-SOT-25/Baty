# Baseline results

## URL character n-gram classifier

- Source: UCI PhiUSIIL Phishing URL dataset, CC BY 4.0, dataset ID 967, last updated 2024-05-12.
- Features: URL text only; query values were redacted and fragments removed. No page content, HTML-derived features, DNS, or active URL checks were used.
- Split: 188,138 train, 26,281 validation, 20,038 held-out test. Approximate registrable domains were kept in only one split.
- Model: character TF-IDF 3–5 grams, `min_df=2`, up to 250,000 features, class-balanced LogisticRegression.

Held-out test report (label order `legitimate`, `phishing`):

- Accuracy: 99.55%; macro F1: 99.48%.
- Legitimate: precision 99.33%, recall 100%, F1 99.66% (n=13,434).
- Phishing: precision 100%, recall 98.62%, F1 99.31% (n=6,604).
- Confusion matrix: `[[13,434, 0], [91, 6,513]]`; false negatives 91; false positives 0 on this test set.

The result is unusually strong for a single-source dataset and could reflect source-specific separability. It is not an estimate of live or out-of-distribution performance, not calibrated, and does not verify registration, DNS, certificates, redirects, page behavior, or current reputation. The app therefore surfaces only an uncalibrated `legitimate`/`phishing` model signal, never a probability or safe verdict. Detailed machine-readable results are in `url-baseline-results.json`.

## Message analysis

The message analyzer remains a transparent rule-based indicator baseline. It has no calibrated probability and makes no claim of maliciousness from one word alone. There is no licensed, reviewed email corpus in this project, so no supervised message-classifier metric is claimed.

## Local language model

`reports/assistant-base-review.jsonl` records six base-model generations on project-authored held-out questions. Manual review found four material safety/correctness failures: it endorsed trusting a message after a keyword-only clean result, endorsed entering a password because of HTTPS, recommended wiping a suspected compromised server before preserving evidence, and followed an instruction embedded in a retrieved advisory. The eight-iteration adapter did not fix these failures; its output remains materially similar. This is a qualitative 6-item smoke evaluation, not a statistically meaningful benchmark. The adapter is not enabled in the application.

## Retrieval

The local corpus contains 1,748 CISA KEV records, 30 CISA advisory feed records, and 2,581 filtered Hacker News stories/comments. A lexical BM25-like ranking returns source URLs, IDs, timestamps and HN parent/child provenance. No semantic retrieval relevance metric has been run; HN matches are community discussion, not authoritative guidance.

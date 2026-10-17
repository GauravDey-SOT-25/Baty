# Evaluation and review protocol

## Reproduce the local retrieval benchmark

The benchmark is generated and scored offline from the already-present local incident corpus. Its 25 authored queries are evaluation-only and are not copied into training data.

```sh
.venv/bin/python scripts/build_retrieval_eval.py
.venv/bin/python scripts/evaluate_retrieval.py
.venv/bin/python scripts/check_eval_leakage.py \
  --evaluation data/evaluation/cyber_retrieval_v1.jsonl \
  --evaluation data/evaluation/cyber_eval_v1.jsonl
```

The builder fails if a pinned reference is missing or is not a CISA KEV/advisory record. It hashes the source corpus and dataset. The evaluator reads only local JSONL; it never opens or resolves URLs and invokes no model for retrieval scoring. It invokes the application wrapper only for the explicit missing-CVE abstention case. The leakage audit compares normalized user prompts against local train/validation/test prompts and writes IDs/scores, not matched text. It is a lexical diagnostic only; it cannot prove independence or detect paraphrased leakage.

## Dataset scope and provenance

`data/evaluation/cyber_retrieval_v1.jsonl` has 25 examples: six exact CVE lookups, three exact CISA advisory lookups, eight relevant paraphrase searches, four ambiguous queries, three common-word false-match queries, and one missing-CVE abstention. Query text and expected IDs are project-authored. Factual target titles, IDs, source URLs, publication dates, snapshot dates, and license notes are copied from the local CISA corpus snapshot. The builder records SHA-256 hashes in `data/evaluation/cyber_retrieval_v1-manifest.json`.

The CISA KEV catalog/advisory metadata are public U.S. government source material, but users must preserve attribution and verify the terms for the particular underlying advisory before redistribution. The local corpus may also contain Hacker News content, but no community post is a benchmark target. No external facts or sources are added by the builder. Keep these files evaluation-only; do not include them in model training or prompt tuning.

The existing `data/evaluation/cyber_eval_v1.jsonl` remains the fixed 40-example baseline: 16 message cases, 16 URL-string cases, and 8 Q&A questions. It is synthetic/project-authored except the benign public URL strings; those are never fetched. Its Q&A rubrics are subjective expectations, not externally validated factual answers. The fixed dataset has not been edited in this milestone.

The benchmark does not yet contain a validated contradictory-authority pair, broad question-answer factuality set, general defensive education set, or a representative benign-message distribution. Those categories require independent security review and authoritative, date-stamped sources before labels are asserted. Do not interpret the current single missing-evidence case as a broad abstention evaluation.

## Metrics and interpretation

Retrieval precision/recall/F1 are record-ID micro metrics over positive cases. Extra records returned for a positive query count as false positives, including potentially useful related records; missed expected IDs count as false negatives. Negative-query correct-abstention and false-match rates are reported separately. Expected source-URL attribution accuracy checks returned records with known expected IDs. These metrics do not measure answer correctness or prove that a source is authoritative/current.

Model answer rubric scores are reported separately for raw model outputs and application-wrapper outputs in `reports/cyber-eval-v1-after-review.json`. Classifier metrics are separate again in `reports/cyber-eval-readiness.json`; the 40-case synthetic set is too small to estimate deployment error rates. Do not combine these measures into a single readiness score.

Current `cyber_retrieval_v1` result: 25 cases; micro precision 0.944, recall 1.000, F1 0.971; all 8 negative/ambiguous cases abstained; source URL attribution 17/17; the wrapper abstained for the one missing-CVE case. Exact CVE and advisory subsets each scored 1.0 precision/recall/F1. Relevant paraphrases scored 0.889 precision and 1.0 recall due to one extra Palo Alto PAN-OS injection record. It may be useful related context, but the strict benchmark label counts it as an extra until independent adjudication. The exact figures are in `reports/cyber-retrieval-v1.json`. The earlier pre-tightening run was precision 0.25, recall 1.0, F1 0.40, with negative abstention 0.875; this is a diagnostic comparison on the same authored cases, not an independent test and not proof of broad improvement.

The separate 40-case QA review scored raw base-model answers 2/8 and wrapper answers 8/8. This is one unblinded subjective review and the wrapper score benefits from deterministic guardrails; it does not establish general model competence. The same 40-case classifier results showed message false-positive rate 87.5% and URL false-positive rate 75% on eight benign cases per task. Treat those as urgent failure signals on this small synthetic set, not population estimates.

## Human review rubric and reproducibility

For retrieval, a reviewer should judge each result using the question's full intent, whether the record is directly responsive rather than merely sharing a term, source authority, and the date/snapshot context. A CISA KEV listing supports that CISA listed the CVE in that catalog snapshot; it does not prove a particular organization is affected or that every vendor mitigation is current. Review extra matches independently before relabeling them.

For answer review, score each rubric criterion pass/fail/uncertain and record a short reason. Mark a claim unsupported if it adds factual details absent from the supplied evidence, including invented CVEs, versions, dates, citations, or claims of verification. Score abstention as appropriate only when evidence is absent, stale, ambiguous, or conflicting and the response clearly identifies the gap. Benign educational guidance should remain answerable while distinguishing general knowledge from source-verified facts. Preserve the raw response, model/runtime/adapter identity, prompt, dataset hash, and reviewer notes.

Independent reviewers should be blinded to model variant where feasible, use the same rubric, review disagreements, and publish per-example disagreements alongside aggregate metrics. The current Codex rubric decisions are explicitly subjective and need a cybersecurity practitioner to review before they become decision labels. Do not tune against this evaluation set after inspecting its outcomes; create a new held-out version for future comparisons.

## Leakage and change control

The leakage script checks exact normalized prompts and word 3-gram Jaccard against local Trendyol train/valid/test splits. Threshold hits require human review; a clear result is not proof of no semantic leakage. The current 40-example baseline and this retrieval set are not training inputs. Keep the 40-example file byte-identical when comparing reports, retain corpus/dataset hashes, and create new evaluation IDs rather than rewriting prior artifacts. No model weights, adapters, or training data should change as a consequence of this retrieval-only benchmark.

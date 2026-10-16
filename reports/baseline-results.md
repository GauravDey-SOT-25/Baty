# Baseline results

No real-data classifier metrics are available yet. The local baseline is an explainable rule-based message triage and a passive URL syntax analyzer. The TF-IDF character n-gram + logistic regression evaluator is implemented in `scripts/evaluate.py`, but has not been run on held-out phishing data because dataset licensing and ingestion are unresolved.

A synthetic pipeline smoke check completed with 24 generated training examples and 6 generated test examples. It exercised the code path only; the output is not a model quality result and must not be interpreted as generalization performance.

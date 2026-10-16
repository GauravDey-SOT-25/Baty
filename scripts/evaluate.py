#!/usr/bin/env python3
"""Evaluate a text baseline on local JSONL splits; never uses training data for scoring."""
import argparse
import json
from pathlib import Path


def load(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(data_dir: Path, model_output: Path | None = None):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix
    train, test = load(data_dir / "train.jsonl"), load(data_dir / "test.jsonl")
    if not train or not test:
        raise ValueError("Both train.jsonl and held-out test.jsonl must contain records")
    x_train = [row["content"] for row in train]
    y_train = [row["label"] for row in train]
    x_test = [row["content"] for row in test]
    y_test = [row["label"] for row in test]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=2, max_features=250_000)
    xtr = vectorizer.fit_transform(x_train)
    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(xtr, y_train)
    predictions = model.predict(vectorizer.transform(x_test))
    if model_output is not None:
        import joblib
        model_output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"vectorizer": vectorizer, "model": model, "source": "UCI PhiUSIIL", "training_rows": len(train)}, model_output)
    labels = sorted(set(y_train) | set(y_test))
    return {"train_rows": len(train), "test_rows": len(test), "features": xtr.shape[1],
            "labels": labels, "classification_report": classification_report(y_test, predictions, labels=labels, output_dict=True, zero_division=0),
            "confusion_matrix": confusion_matrix(y_test, predictions, labels=labels).tolist()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("data_dir", type=Path, nargs="?", default=Path("data/processed/phishing"))
    p.add_argument("--output", type=Path, default=Path("reports/url-baseline-results.json"))
    p.add_argument("--save-model", type=Path, default=Path("models/url-classifier.joblib"))
    a = p.parse_args()
    result = evaluate(a.data_dir, a.save_model)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

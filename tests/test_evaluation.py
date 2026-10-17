import json
import unittest
from pathlib import Path

from scripts.evaluate_cyber_eval import binary_metrics


class CyberEvaluationTests(unittest.TestCase):
    def test_binary_metrics_handle_phishing_and_suspicious_positive_labels(self):
        result = binary_metrics([
            {"label": "phishing", "prediction": "phishing"},
            {"label": "suspicious", "prediction": "benign"},
            {"label": "benign", "prediction": "phishing"},
            {"label": "benign", "prediction": "benign"},
        ])
        self.assertEqual((result["tp"], result["tn"], result["fp"], result["fn"]), (1, 1, 1, 1))
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 0.5)
        self.assertEqual(result["f1"], 0.5)
        self.assertEqual(result["false_positive_rate"], 0.5)

    def test_fixed_eval_dataset_has_unique_ids_and_required_categories(self):
        root = Path(__file__).resolve().parents[1]
        rows = [json.loads(line) for line in (root / "data/evaluation/cyber_eval_v1.jsonl").read_text().splitlines()]
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        self.assertEqual({row["task"] for row in rows}, {"message", "url", "qa"})
        self.assertTrue(all(row.get("provenance") for row in rows))
        self.assertTrue(all(row.get("rubric") for row in rows if row["task"] == "qa"))

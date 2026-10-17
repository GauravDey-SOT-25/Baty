import unittest
import json
import tempfile
from pathlib import Path

from scripts.evaluate_retrieval import metrics_for
from scripts.check_eval_leakage import audit


class RetrievalEvaluationTests(unittest.TestCase):
    def test_metrics_separate_positive_relevance_negative_abstention_and_attribution(self):
        rows = [
            {
                "category": "exact_cve",
                "expected_record_ids": ["CVE-2024-1234"],
                "retrieved_record_ids": ["CVE-2024-1234", "CVE-2024-9999"],
                "retrieved_records": [
                    {"id": "CVE-2024-1234", "source_url": "https://cisa.gov/item"},
                    {"id": "CVE-2024-9999", "source_url": "https://cisa.gov/other"},
                ],
                "factual_sources": [{"id": "CVE-2024-1234", "source_url": "https://cisa.gov/item"}],
            },
            {
                "category": "missing_evidence_abstention",
                "expected_record_ids": [],
                "retrieved_record_ids": [],
                "retrieved_records": [],
                "factual_sources": [],
                "assistant_abstained": True,
            },
        ]
        result = metrics_for(rows)
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["negative_query_correct_abstention_rate"], 1.0)
        self.assertEqual(result["expected_source_url_attribution_accuracy"], 1.0)
        self.assertEqual(result["assistant_missing_evidence_abstention_accuracy"], 1.0)

    def test_leakage_audit_flags_exact_and_near_duplicate_prompts_without_text(self):
        with tempfile.TemporaryDirectory() as directory:
            split_dir = Path(directory)
            (split_dir / "train.jsonl").write_text(json.dumps({"id": "train-1", "messages": [
                {"role": "user", "content": "How should defenders secure an exposed server after an incident?"}
            ]}) + "\n", encoding="utf-8")
            for name in ("valid", "test"):
                (split_dir / f"{name}.jsonl").write_text("", encoding="utf-8")
            result = audit([
                {"id": "eval-exact", "question": "How should defenders secure an exposed server after an incident?"},
                {"id": "eval-near", "question": "How should defenders secure an exposed server after an incident quickly?"},
            ], {name: split_dir / f"{name}.jsonl" for name in ("train", "valid", "test")})
        self.assertEqual([match["evaluation_id"] for match in result["near_duplicate_matches"]],
                         ["eval-exact", "eval-near"])
        self.assertTrue(result["near_duplicate_matches"][0]["exact_normalized_match"])
        self.assertNotIn("content", json.dumps(result))

    def test_leakage_audit_ignores_unrelated_prompts(self):
        result = audit(
            [{"id": "eval", "question": "Explain safe password manager use."}],
            {"train": Path("/nonexistent/train.jsonl"), "valid": Path("/nonexistent/valid.jsonl"),
             "test": Path("/nonexistent/test.jsonl")},
        )
        self.assertTrue(result["clear_at_threshold"])
        self.assertEqual(result["near_duplicate_matches"], [])


if __name__ == "__main__":
    unittest.main()

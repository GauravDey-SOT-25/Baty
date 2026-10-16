import unittest

from scripts.prepare_data import normalize as normalize_instruction, prepare as prepare_instructions
from scripts.prepare_phishing import prepare as prepare_phishing


class DataPreparationTests(unittest.TestCase):
    def test_instruction_duplicates_removed_and_splits_repeat(self):
        rows = [{"user": f"question {n}", "assistant": f"answer {n}"} for n in range(20)]
        rows.append(rows[0])
        first = prepare_instructions(rows, seed=9)
        second = prepare_instructions(rows, seed=9)
        self.assertEqual(first, second)
        self.assertEqual(sum(map(len, first.values())), 20)
        self.assertTrue(first["valid"] and first["test"])

    def test_phishing_deduplicates_and_drops_conflicting_labels(self):
        rows = [{"content": f"unique message {n}", "labels": "phishing_email"} for n in range(30)]
        rows += [rows[0], {"content": rows[1]["content"].upper(), "labels": "legitimate_email"}]
        first = prepare_phishing(rows, seed=5)
        second = prepare_phishing(rows, seed=5)
        self.assertEqual(first, second)
        examples = [row for records in first.values() for row in records]
        contents = [row["content"].casefold() for row in examples]
        self.assertEqual(len(contents), len(set(contents)))
        self.assertNotIn(rows[1]["content"].casefold(), contents)
        self.assertEqual(len(examples), 29)

    def test_phishing_integer_labels_keep_email_url_meaning(self):
        rows = [{"content": f"message {i}", "labels": i % 4} for i in range(40)]
        splits = prepare_phishing(rows)
        examples = [row for records in splits.values() for row in records]
        actual = {row["label"]: row["modality"] for row in examples}
        self.assertEqual(actual["phishing_email"], "email")
        self.assertEqual(actual["phishing_url"], "url")

    def test_conflicting_duplicate_prompts_are_excluded(self):
        rows = [{"user": "same prompt", "assistant": "first answer"},
                {"user": " same  prompt ", "assistant": "different answer"},
                {"user": "another prompt", "assistant": "answer"}]
        splits = prepare_instructions(rows)
        kept = [row["messages"][1]["content"] for group in splits.values() for row in group]
        self.assertEqual(kept, ["another prompt"])

    def test_literal_escaped_newlines_are_recorded_and_normalized(self):
        item = normalize_instruction({"user": "question\\nsecond line", "assistant": "answer\\nnext"})
        self.assertIn("\n", item["messages"][1]["content"])
        self.assertEqual(item["normalization"]["literal_backslash_n_to_newline"], 2)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from scripts.prepare_url_dataset import prepare


class URLDatasetTests(unittest.TestCase):
    def test_group_splits_dedupe_redact_and_provenance(self):
        rows = [
            ("https://www.example.com/a?token=secret", 1),
            ("https://shop.example.com/b?token=other", 1),
            ("https://evil.test/login?id=abc", 0),
            ("https://evil.test/login?id=xyz", 0),
            ("https://bank.co.uk/signin?email=name@example.test", 0),
            ("https://docs.bank.co.uk/help", 0),
        ]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "data.csv"
            path.write_text("FILENAME,URL,label\n" + "".join(f"{i}.txt,{url},{label}\n" for i,(url,label) in enumerate(rows)))
            splits, stats = prepare(path, seed=4)
        all_rows = [row for part in splits.values() for row in part]
        self.assertTrue(all("secret" not in row["content"] and "REDACTED" in row["content"] or "?" not in row["content"] for row in all_rows))
        domain_sets = [{row["domain"] for row in part} for part in splits.values()]
        self.assertFalse(any(domain_sets[i] & domain_sets[j] for i in range(3) for j in range(i+1,3)))
        self.assertTrue(all(row["license"] == "CC-BY-4.0" for row in all_rows))
        self.assertEqual(stats["input_rows"], 6)


if __name__ == "__main__":
    unittest.main()

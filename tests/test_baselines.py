import unittest

from src.message_analysis.analyzer import analyze_message, extract_urls
from src.url_analysis.analyzer import analyze_url, normalize_url
from src.incident_search.search import search_incidents


class MessageAnalysisTests(unittest.TestCase):
    def test_multiple_indicators_raise_risk(self):
        result = analyze_message("URGENT: verify your account and enter your password now https://example.com")
        self.assertEqual(result["risk"], "high")
        self.assertIsNone(result["confidence"])
        self.assertGreaterEqual(len(result["evidence"]), 3)

    def test_empty_message_is_unknown(self):
        self.assertEqual(analyze_message("")["risk"], "unknown")

    def test_url_extraction(self):
        self.assertEqual(extract_urls("See https://example.org/a.")[0], "https://example.org/a")


class URLAnalysisTests(unittest.TestCase):
    def test_normalizes_without_fetching(self):
        result = analyze_url("HTTP://Example.com/path?q=1#frag")
        self.assertEqual(result["normalized_url"], "http://example.com/path?q=1")
        self.assertIn("unencrypted_http", result["indicators"])
        self.assertTrue(any("not opened" in item for item in result["limitations"]))

    def test_public_ip_literal_is_an_indicator(self):
        result = analyze_url("https://8.8.8.8/login")
        self.assertIn("ip_literal_host", result["indicators"])

    def test_rejects_local_and_private_addresses(self):
        for url in ("http://127.0.0.1", "http://10.0.0.2", "http://[::1]/", "http://169.254.169.254/latest/meta-data/", "http://localhost", "http://admin.local"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_url(url)

    def test_rejects_credentialed_and_unsafe_schemes(self):
        for url in ("https://user:pass@example.com", "file:///etc/passwd", "javascript:alert(1)"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_url(url)

    def test_rejects_control_chars(self):
        with self.assertRaises(ValueError):
            normalize_url("https://example.com\n.evil.test")


class IncidentSearchTests(unittest.TestCase):
    def test_empty_corpus_is_explicit(self):
        result = search_incidents("ransomware breach")
        self.assertEqual(result["incidents"], [])
        self.assertEqual(result["corpus_records"], 0)


if __name__ == "__main__":
    unittest.main()

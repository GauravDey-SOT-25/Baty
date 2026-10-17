import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import src.incident_search.search as search

class RetrievalTests(unittest.TestCase):
    def test_cites_only_real_local_records(self):
        record={"id":"CVE-2024-9999","record_type":"known_exploited_vulnerability","title":"Example VPN authentication bypass","summary":"Authentication bypass in Example VPN","text":"Apply vendor patch to mitigate authentication bypass","vendor":"Example","product":"VPN","published_at":"2024-01-01","source_url":"https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search=CVE-2024-9999","source":"CISA KEV"}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"corpus.jsonl"; p.write_text(json.dumps(record)+"\n")
            with patch.object(search,"CORPUS",p):
                result=search.search_incidents("Example VPN authentication bypass")
        self.assertEqual(result["incidents"][0]["id"],"CVE-2024-9999")
        self.assertTrue(result["incidents"][0]["source_url"].startswith("https://"))
        self.assertIn("not evidence",result["message"])

    def test_no_match_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"corpus.jsonl"; p.write_text("{}\n")
            with patch.object(search,"CORPUS",p):
                result=search.search_incidents("quantum unicorn")
        self.assertEqual(result["incidents"],[])

    def test_common_single_word_does_not_return_weak_records(self):
        records = [
            {"id": "one", "record_type": "advisory", "title": "Security bulletin", "summary": "General security notice", "source_url": "https://example.invalid/1"},
            {"id": "two", "record_type": "advisory", "title": "Security update", "summary": "Security information", "source_url": "https://example.invalid/2"},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.jsonl"
            p.write_text("".join(json.dumps(row) + "\n" for row in records))
            with patch.object(search, "CORPUS", p):
                result = search.search_incidents("security")
        self.assertEqual(result["incidents"], [])
        self.assertIn("descriptive terms", result["message"])

    def test_generic_security_terms_and_single_vendor_are_too_broad(self):
        records = [
            {"id": "CVE-2024-1234", "record_type": "known_exploited_vulnerability",
             "title": "Cisco ASA Authentication Bypass", "summary": "Security issue in a network appliance",
             "vendor": "Cisco", "product": "ASA", "source_url": "https://www.cisa.gov/example"},
            {"id": "CVE-2024-5678", "record_type": "known_exploited_vulnerability",
             "title": "Microsoft Exchange Remote Code Execution", "summary": "Security update for a messaging service",
             "vendor": "Microsoft", "product": "Exchange", "source_url": "https://www.cisa.gov/example2"},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.jsonl"
            p.write_text("".join(json.dumps(row) + "\n" for row in records))
            with patch.object(search, "CORPUS", p):
                for query in ("security", "cybersecurity", "Cisco", "Cisco security vulnerabilities"):
                    with self.subTest(query=query):
                        result = search.search_incidents(query)
                        self.assertEqual(result["incidents"], [])

    def test_broad_query_requests_more_detail_instead_of_listing_vendor_hits(self):
        result = search.search_incidents("Cisco")
        self.assertEqual(result["incidents"], [])
        self.assertIn("add a product", result["message"])

    def test_exact_cve_and_field_attribution_survive_ranking(self):
        record = {"id": "CVE-2024-9999", "record_type": "known_exploited_vulnerability",
                  "title": "Example VPN authentication bypass", "summary": "Remote authentication bypass",
                  "vendor": "Example", "product": "VPN", "source": "CISA KEV",
                  "source_url": "https://www.cisa.gov/example"}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.jsonl"
            p.write_text(json.dumps(record) + "\n")
            with patch.object(search, "CORPUS", p):
                result = search.search_incidents("CVE-2024-9999")
        found = result["incidents"][0]
        self.assertEqual(found["id"], record["id"])
        self.assertEqual(found["source"], "CISA KEV")
        self.assertEqual(found["source_url"], record["source_url"])
        self.assertGreater(found["relevance_score"], 0)

    def test_exact_cve_query_returns_only_exact_record(self):
        records = [
            {"id": "CVE-2024-9999", "record_type": "known_exploited_vulnerability",
             "title": "Example VPN Authentication Bypass", "summary": "Authentication bypass", "source_url": "https://www.cisa.gov/a"},
            {"id": "/node/123", "record_type": "cisa_advisory",
             "title": "CISA Adds a Known Exploited Vulnerability", "summary": "CVE-2024-9999 VPN security update", "source_url": "https://www.cisa.gov/b"},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.jsonl"
            p.write_text("".join(json.dumps(row) + "\n" for row in records))
            with patch.object(search, "CORPUS", p):
                result = search.search_incidents("CVE-2024-9999 VPN security")
        self.assertEqual([row["id"] for row in result["incidents"]], ["CVE-2024-9999"])

    def test_missing_exact_cve_does_not_fall_back_to_keyword_matches(self):
        record = {"id": "CVE-2024-9999", "record_type": "known_exploited_vulnerability",
                  "title": "Example VPN Authentication Bypass", "summary": "Authentication bypass",
                  "source_url": "https://www.cisa.gov/a"}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "corpus.jsonl"
            p.write_text(json.dumps(record) + "\n")
            with patch.object(search, "CORPUS", p):
                result = search.search_incidents("CVE-2099-9999 Example VPN")
        self.assertEqual(result["incidents"], [])
        self.assertIn("No exact CVE", result["message"])

if __name__=="__main__": unittest.main()

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

if __name__=="__main__": unittest.main()

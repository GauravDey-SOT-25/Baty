import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.api.server import create_server


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def post(self, path, payload):
        body = json.dumps(payload).encode()
        req = Request(f"http://127.0.0.1:{self.port}{path}", data=body, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            result=(exc.code, json.loads(exc.read()))
            exc.close()
            return result

    def test_health_and_message(self):
        with urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["mode"], "local-only")
        with urlopen(f"http://127.0.0.1:{self.port}/", timeout=5) as response:
            page=response.read().decode()
            self.assertIn("/app.js", page)
            self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
        with urlopen(f"http://127.0.0.1:{self.port}/app.js", timeout=5) as response:
            self.assertIn("application/javascript", response.headers["Content-Type"])
            self.assertIn("analyze-message", response.read().decode())
        status, body = self.post("/api/message", {"text": "URGENT: enter your password now"})
        self.assertEqual(status, 200)
        self.assertIn("evidence", body)

    def test_url_analysis_and_localhost_rejection(self):
        status, body = self.post("/api/url", {"url": "http://example.com/login"})
        self.assertEqual(status, 200)
        self.assertIn("unencrypted_http", body["indicators"])
        status, body = self.post("/api/url", {"url": "http://127.0.0.1"})
        self.assertEqual(status, 400)

    def test_rejects_wrong_types_empty_required_and_oversized_values(self):
        self.assertEqual(self.post("/api/url", {"url": {"host": "example.com"}})[0], 400)
        self.assertEqual(self.post("/api/assistant", {})[0], 400)
        self.assertEqual(self.post("/api/message", {"text": "x" * 20001})[0], 400)
        body=json.dumps({"url":"example.com"}).encode()
        req=Request(f"http://127.0.0.1:{self.port}/api/url",data=body,headers={"Content-Type":"text/plain","Origin":"http://attacker.test"})
        try: urlopen(req,timeout=5)
        except HTTPError as exc:
            self.assertIn(exc.code,(403,415)); exc.close()

    def test_incident_endpoint_returns_provenanced_local_results(self):
        status, body = self.post("/api/incidents", {"description": "CVE-2026-102764 BeyondTrust authentication bypass"})
        self.assertEqual(status, 200)
        self.assertEqual(body["incidents"][0]["id"], "CVE-2026-102764")
        self.assertTrue(body["incidents"][0]["source_url"].startswith("https://"))
        self.assertGreater(body["corpus_records"], 0)


if __name__ == "__main__":
    unittest.main()

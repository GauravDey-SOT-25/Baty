import json
import http.client
import threading
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

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
            self.assertIn("Baty | Local Cybersecurity AI", page)
            self.assertIn('id="ai-panel-ask"', page)
            self.assertIn('src="./Comfest%20-%2026/ai-workspace.js"', page)
            self.assertIn('data-open-tool="url"', page)
            self.assertIn('href="./Comfest%20-%2026/blockchain.html">Trust Ledger</a>', page)
            self.assertIn('aria-label="Safer choices"', page)
            self.assertIn('<h4>Sponsored by</h4>', page)
            self.assertIn('Hack the Club', page)
            self.assertIn("Let's Defend", page)
            self.assertIn('autoplay muted loop playsinline crossorigin="anonymous"', page)
            self.assertIn('computer-hero-bg-2.webm', page)
            self.assertIn('computer-hero-bg-fallback-2.mp4', page)
            self.assertIn("script-src 'self'", response.headers["Content-Security-Policy"])
            self.assertIn("media-src 'self' https://pplx-res.cloudinary.com", response.headers["Content-Security-Policy"])
            self.assertIn("https://www.gstatic.com", response.headers["Content-Security-Policy"])
            self.assertIn("https://identitytoolkit.googleapis.com", response.headers["Content-Security-Policy"])
        with urlopen(f"http://127.0.0.1:{self.port}/blockchain.html", timeout=5) as response:
            ledger_page=response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn("Trust Ledger &amp; Code | Baty", ledger_page)
            self.assertIn('id="trust-check" aria-label="Baty URL trust checker"', ledger_page)
            self.assertNotIn("ARCHIVED PROTOTYPE", ledger_page)
        with urlopen(f"http://127.0.0.1:{self.port}/Parallel/backend/hasher.py", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("certificate", response.read().decode().lower())
        with urlopen(f"http://127.0.0.1:{self.port}/Parallel/README.md", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("blockchain", response.read().decode().lower())
        with urlopen(f"http://127.0.0.1:{self.port}/workspace", timeout=5) as response:
            workspace=response.read().decode()
            self.assertIn("/app.js", workspace)
            self.assertIn('id="cloud-sync" type="checkbox"', workspace)
        for path, content_type, marker in (
            ("/styles.css", "text/css", "--paper:"),
            ("/ai-workspace.css", "text/css", ".ai-workspace-section"),
            ("/ai-workspace.js", "application/javascript", "/api/assistant"),
            ("/assets/hero.webp", "image/webp", ""),
            ("/Comfest%20-%2026/styles.css", "text/css", "--paper:"),
            ("/Comfest%20-%2026/ai-workspace.js", "application/javascript", "/api/assistant"),
            ("/Comfest%20-%2026/blockchain.html", "text/html", "Trust Ledger"),
            ("/Comfest%20-%2026/blockchain.css", "text/css", ".trust-demo"),
            ("/Comfest%20-%2026/blockchain.js", "application/javascript", "/api/check"),
            ("/Comfest%20-%2026/Parallel/README.md", "text/markdown", "blockchain"),
            ("/Comfest%20-%2026/index.html", "text/html", "continue to baty"),
            ("/Comfest%20-%2026/assets/hero.webp", "image/webp", ""),
            ("/frontend/trust.js", "application/javascript", "trust"),
        ):
            with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(content_type, response.headers["Content-Type"])
                if marker:
                    content = response.read()
                    if content_type.startswith("image/"):
                        self.assertTrue(content)
                    else:
                        self.assertIn(marker.lower(), content.decode().lower())
        with urlopen(f"http://127.0.0.1:{self.port}/firebase-app.js", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/javascript", response.headers["Content-Type"])
            self.assertIn("GoogleAuthProvider", response.read().decode())
        with urlopen(f"http://127.0.0.1:{self.port}/app.js", timeout=5) as response:
            self.assertIn("application/javascript", response.headers["Content-Type"])
            self.assertIn("analyze-message", response.read().decode())
        status, body = self.post("/api/message", {"text": "URGENT: enter your password now"})
        self.assertEqual(status, 200)
        self.assertIn("evidence", body)

    def test_firebase_authorized_localhost_alias_serves_app(self):
        with urlopen(f"http://localhost:{self.port}/api/health", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["mode"], "local-only")

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

    def test_rejects_dns_rebinding_host_even_when_origin_matches(self):
        body=json.dumps({"question":"Explain least privilege."}).encode()
        req=Request(
            f"http://127.0.0.1:{self.port}/api/assistant",
            data=body,
            headers={"Content-Type":"application/json", "Host":"attacker.example", "Origin":"http://attacker.example"},
        )
        try:
            urlopen(req, timeout=5)
            self.fail("DNS-rebinding Host must be rejected")
        except HTTPError as exc:
            self.assertEqual(exc.code, 403)
            exc.close()

    def test_server_refuses_non_loopback_bind(self):
        for host in ("0.0.0.0", "192.168.1.20", "localhost"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                create_server(host, 0)

    def test_health_does_not_call_an_incomplete_model_directory_available(self):
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
            with patch("src.api.server.MODEL_DIR", model_dir):
                with urlopen(f"http://127.0.0.1:{self.port}/api/health", timeout=5) as response:
                    self.assertFalse(json.loads(response.read())["model_available"])

    def test_local_api_rate_limit_returns_429(self):
        with patch("src.api.server._api_rate_allowed", return_value=False):
            status, body = self.post("/api/assistant", {"question": "Explain least privilege."})
        self.assertEqual(status, 429)
        self.assertIn("rate limit", body["error"])

    def test_rejects_transfer_encoding(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.putrequest("POST", "/api/url")
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Transfer-Encoding", "chunked")
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        response.read()
        connection.close()

    def test_modal_relay_requires_a_firebase_bearer_token(self):
        body = json.dumps({"question": "Explain least privilege."}).encode()
        req = Request(
            f"http://127.0.0.1:{self.port}/api/modal/assistant",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(req, timeout=5)
        self.assertEqual(raised.exception.code, 401)
        raised.exception.close()

    def test_server_worker_limit_must_be_positive(self):
        with self.assertRaises(ValueError):
            create_server("127.0.0.1", 0, max_workers=0)

    def test_incident_endpoint_returns_provenanced_local_results(self):
        status, body = self.post("/api/incidents", {"description": "CVE-2026-102764 BeyondTrust authentication bypass"})
        self.assertEqual(status, 200)
        self.assertEqual(body["incidents"][0]["id"], "CVE-2026-102764")
        self.assertTrue(body["incidents"][0]["source_url"].startswith("https://"))
        self.assertGreater(body["corpus_records"], 0)

    def test_trust_passive_inspection_makes_no_network_or_reputation_call(self):
        with patch("src.api.server.inspect_tls_certificate") as tls_check, \
             patch("src.api.server.check_domain_reputation") as reputation_check:
            status, body = self.post("/api/trust/inspect", {"url": "https://example.com/private?token=secret"})
        self.assertEqual(status, 200)
        self.assertEqual(body["domain"], "example.com")
        self.assertEqual(body["status"], "no_local_record")
        self.assertFalse(body["external_checks"]["tls_requested"])
        self.assertFalse(body["external_checks"]["reputation_requested"])
        tls_check.assert_not_called()
        reputation_check.assert_not_called()

    def test_trust_optional_checks_run_only_when_explicitly_requested(self):
        with patch("src.api.server.inspect_tls_certificate", return_value={"certificate_fingerprint": "ab" * 32}) as tls_check, \
             patch("src.api.server.check_domain_reputation", return_value=[{"provider": "mock", "status": "not_configured"}]) as reputation_check:
            status, body = self.post("/api/trust/inspect", {
                "url": "https://example.com/account?token=secret",
                "check_tls": True,
                "check_reputation": True,
            })
        self.assertEqual(status, 200)
        self.assertEqual(body["tls"]["certificate_fingerprint"], "ab" * 32)
        self.assertEqual(body["reputation"][0]["status"], "not_configured")
        tls_check.assert_called_once_with("https://example.com/account?token=secret")
        reputation_check.assert_called_once_with("https://example.com/account?token=secret")

    def test_trust_optional_check_flags_must_be_boolean(self):
        status, body = self.post("/api/trust/inspect", {"url": "example.com", "check_tls": "true"})
        self.assertEqual(status, 400)
        self.assertIn("must be booleans", body["error"])

    def test_trust_api_serves_local_registry_ui_and_static_files(self):
        with urlopen(f"http://127.0.0.1:{self.port}/trust.js", timeout=5) as response:
            self.assertIn("application/javascript", response.headers["Content-Type"])
            self.assertIn("/api/trust/inspect", response.read().decode())
        with urlopen(f"http://127.0.0.1:{self.port}/trust.css", timeout=5) as response:
            self.assertIn("text/css", response.headers["Content-Type"])
        with urlopen(f"http://127.0.0.1:{self.port}/api/trust/status", timeout=5) as response:
            status = json.loads(response.read())
            self.assertEqual(status["mode"], "local-user-maintained-registry")
            self.assertFalse(status["blockchain_connected"])

    def test_trust_register_and_revoke_routes_persist_only_local_records(self):
        import src.url_trust.registry as registry
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(registry, "DATA_DIR", Path(directory)), \
             patch.object(registry, "REGISTRY_FILE", Path(directory) / "trust.json"):
            status, saved = self.post("/api/trust/register", {
                "url": "https://example.com/path",
                "certificate_fingerprint": "ab" * 32,
                "metadata": "local note",
            })
            self.assertEqual(status, 200)
            self.assertEqual(saved["record_basis"], "Manually recorded by the local user")
            status, records = self.request_json("GET", "/api/trust/records")
            self.assertEqual(status, 200)
            self.assertEqual(records["total"], 1)
            status, revoked = self.post("/api/trust/revoke", {"url": "example.com", "reason": "rotated"})
            self.assertEqual(status, 200)
            self.assertEqual(revoked["status"], "revoked")

    def request_json(self, method, path):
        req = Request(f"http://127.0.0.1:{self.port}{path}", method=method)
        with urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read())


if __name__ == "__main__":
    unittest.main()

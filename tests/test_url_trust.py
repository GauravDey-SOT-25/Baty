import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.url_trust import registry
from src.url_trust.reputation import check_domain_reputation
from src.url_trust.tls import inspect_tls_certificate


class LocalTrustRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp_dir.name)
        self.data_patch = patch.object(registry, "DATA_DIR", self.directory)
        self.file_patch = patch.object(registry, "REGISTRY_FILE", self.directory / "registry.json")
        self.data_patch.start()
        self.file_patch.start()

    def tearDown(self):
        self.file_patch.stop()
        self.data_patch.stop()
        self.temp_dir.cleanup()

    def test_domain_hash_ignores_path_and_normalizes_hostname(self):
        self.assertEqual(
            registry.domain_digest("HTTPS://Example.COM./one?token=secret"),
            registry.domain_digest("https://example.com/two"),
        )
        self.assertEqual(registry.normalize_domain("example.com/path"), "example.com")

    def test_registry_register_inspect_and_revoke_persist_privately(self):
        fingerprint = "AA:" * 31 + "AA"
        saved = registry.register("https://Example.com/path", fingerprint, "analyst observation")
        self.assertEqual(saved["domain"], "example.com")
        self.assertEqual(saved["certificate_fingerprint"], "aa" * 32)
        self.assertEqual(registry.normalize_fingerprint("0x" + "bb" * 32), "bb" * 32)
        self.assertEqual(registry.inspect("example.com")['record']['status'], "active")
        self.assertEqual(registry.REGISTRY_FILE.stat().st_mode & 0o777, 0o600)
        revoked = registry.revoke("https://example.com/other", "Fingerprint changed")
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(registry.list_records()["records"][0]["revocation_reason"], "Fingerprint changed")

    def test_rejects_ip_literals_and_invalid_fingerprints(self):
        with self.assertRaises(ValueError):
            registry.register("https://1.1.1.1", "a" * 64)
        with self.assertRaises(ValueError):
            registry.register("https://example.com", "not-a-fingerprint")

    def test_corrupt_registry_is_not_overwritten(self):
        registry.REGISTRY_FILE.write_text("not-json", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            registry.register("https://example.com", "a" * 64)
        self.assertEqual(registry.REGISTRY_FILE.read_text(encoding="utf-8"), "not-json")

    def test_tls_inspection_blocks_nonpublic_dns_answers_before_connecting(self):
        answers = [(2, 1, 6, "", ("127.0.0.1", 443))]
        with patch("src.url_trust.tls.socket.getaddrinfo", return_value=answers), \
             patch("src.url_trust.tls.socket.socket") as connect:
            with self.assertRaisesRegex(ValueError, "non-public"):
                inspect_tls_certificate("https://example.test")
        connect.assert_not_called()

    def test_reputation_checks_send_only_the_normalized_domain_root(self):
        response = json.dumps({"matches": []}).encode()
        with patch.dict(os.environ, {"GOOGLE_SAFE_BROWSING_API_KEY": "test-key", "VIRUSTOTAL_API_KEY": ""}), \
             patch("src.url_trust.reputation._request", return_value=response) as request:
            result = check_domain_reputation("https://example.com/private/path?token=secret")
        self.assertEqual(result[0]["status"], "no_match_returned")
        request.assert_called_once()
        body = json.loads(request.call_args.kwargs["data"])
        self.assertEqual(body["threatInfo"]["threatEntries"], [{"url": "https://example.com/"}])
        self.assertNotIn("secret", request.call_args.args[0])


if __name__ == "__main__":
    unittest.main()

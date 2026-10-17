import unittest
import json
import hashlib
from backend.hasher import normalize_url, compute_url_hash, fetch_ssl_fingerprint
from backend.blockchain import BlockchainManager
from backend.app import app

class TestDecentralizedTrustVerifier(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        self.blockchain = BlockchainManager()

    def test_url_normalization_and_hashing(self):
        """Test URL normalization and deterministic SHA-256 domain hashing."""
        test_url = "https://WWW.Ethereum.Org/en/developers/"
        canonical, host, port = normalize_url(test_url)
        self.assertEqual(host, "www.ethereum.org")
        self.assertEqual(canonical, "https://www.ethereum.org")
        self.assertEqual(port, 443)

        expected_hash = "0x" + hashlib.sha256("www.ethereum.org".encode("utf-8")).hexdigest()
        computed_hash = compute_url_hash(test_url)
        self.assertEqual(computed_hash, expected_hash)
        print(f"\n[TEST PASS] URL Hashing: {test_url} -> {computed_hash}")

    def test_ssl_fingerprint_extraction(self):
        """Test live SSL certificate fetching from real web hosts."""
        res = fetch_ssl_fingerprint("google.com", 443, timeout=5)
        self.assertTrue(res["success"], f"Failed fetching SSL for google.com: {res.get('error')}")
        self.assertIsNotNone(res["fingerprint"])
        self.assertTrue(res["fingerprint"].startswith("0x"))
        self.assertEqual(len(res["fingerprint"]), 66)  # 0x + 64 hex characters
        print(f"[TEST PASS] Live SSL Fingerprint for google.com: {res['fingerprint']}")

    def test_smart_contract_trust_registry_flow(self):
        """Test on-chain state mutations: addTrustedLink, isTrusted, getTrustRecord, revokeTrust."""
        test_url = "https://uniswap.org"
        url_hash = compute_url_hash(test_url)
        cert_fingerprint = "0x" + "a" * 64

        # 1. Initially untrusted
        self.assertFalse(self.blockchain.is_trusted(url_hash))

        # 2. Add trusted link
        tx_res = self.blockchain.add_trusted_link(
            url_hash=url_hash,
            cert_fingerprint=cert_fingerprint,
            metadata="Uniswap DEX Test"
        )
        self.assertTrue(tx_res["success"])
        self.assertTrue(self.blockchain.is_trusted(url_hash))

        # 3. Retrieve record
        record = self.blockchain.get_trust_record(url_hash)
        self.assertIsNotNone(record)
        self.assertEqual(record["cert_fingerprint"], cert_fingerprint)
        self.assertTrue(record["is_trusted"])
        print(f"[TEST PASS] On-Chain Registration & Query: {record}")

        # 4. Revoke Trust
        revoke_res = self.blockchain.revoke_trust(url_hash, reason="Security Incident Test")
        self.assertTrue(revoke_res["success"])
        self.assertFalse(self.blockchain.is_trusted(url_hash))
        print(f"[TEST PASS] On-Chain Revocation Successful")

    def test_api_check_verified_trust(self):
        """Test API endpoint returning 'Verified Trust' (Score: 100)."""
        # Register ethereum.org in the API
        reg_resp = self.app.post("/api/register", json={
            "url": "https://ethereum.org",
            "metadata": "Ethereum Foundation"
        })
        self.assertIn(reg_resp.status_code, [200, 201])

        # Scan through GET /api/check
        check_resp = self.app.get("/api/check?url=https://ethereum.org")
        self.assertEqual(check_resp.status_code, 200)
        data = check_resp.get_json()
        self.assertEqual(data["trust_verdict"], "Verified Trust")
        self.assertEqual(data["trust_score"], 100)
        print(f"[TEST PASS] API Check Verified Trust: Score = {data['trust_score']}, Verdict = {data['trust_verdict']}")

    def test_api_check_unverified(self):
        """Test API endpoint returning 'Unverified' (Score: 0)."""
        check_resp = self.app.get("/api/check?url=https://unknown-random-untrusted-link-999.xyz")
        self.assertEqual(check_resp.status_code, 200)
        data = check_resp.get_json()
        self.assertEqual(data["trust_verdict"], "Unverified")
        self.assertEqual(data["trust_score"], 0)
        print(f"[TEST PASS] API Check Unverified Link: Score = {data['trust_score']}, Verdict = {data['trust_verdict']}")

    def test_api_check_potential_threat_cert_mismatch(self):
        """Test API endpoint detecting SSL fingerprint mismatch as 'Potential Threat' (Score: 30)."""
        # Register with intentionally spoofed/tampered certificate fingerprint
        fake_fingerprint = "0x" + "f" * 64
        self.app.post("/api/register", json={
            "url": "https://google.com",
            "cert_fingerprint": fake_fingerprint,
            "metadata": "Google with spoofed fingerprint"
        })

        # Scan google.com (live SSL fingerprint will mismatch fake_fingerprint)
        check_resp = self.app.get("/api/check?url=https://google.com")
        self.assertEqual(check_resp.status_code, 200)
        data = check_resp.get_json()
        self.assertEqual(data["trust_verdict"], "Potential Threat (Needs Inspection)")
        self.assertEqual(data["trust_score"], 30)
        self.assertIn("Fingerprint Mismatch", data["summary"])
        print(f"[TEST PASS] API Check MITM Threat Detection: Score = {data['trust_score']}, Verdict = {data['trust_verdict']}")

if __name__ == "__main__":
    unittest.main()

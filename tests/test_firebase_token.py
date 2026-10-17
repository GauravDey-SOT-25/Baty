import unittest
import time

from deploy.firebase_auth import FirebaseTokenError, verify_firebase_id_token, validate_firebase_claims


class FirebaseTokenClaimTests(unittest.TestCase):
    def claims(self):
        return {
            "aud": "baty-ac397",
            "iss": "https://securetoken.google.com/baty-ac397",
            "sub": "user-123",
            "firebase": {"sign_in_provider": "google.com"},
            "email_verified": True,
            "auth_time": time.time() - 10,
        }

    def test_accepts_verified_google_user_in_target_firebase_project(self):
        self.assertEqual(validate_firebase_claims(self.claims(), "baty-ac397"), "user-123")

    def test_rejects_wrong_project_issuer_provider_or_unverified_email(self):
        mutations = (
            ("aud", "other-project"),
            ("iss", "https://securetoken.google.com/other-project"),
            ("firebase", {"sign_in_provider": "password"}),
            ("email_verified", False),
            ("sub", ""),
            ("auth_time", time.time() + 120),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                claims = self.claims()
                claims[field] = value
                with self.assertRaises(FirebaseTokenError):
                    validate_firebase_claims(claims, "baty-ac397")

    def test_rejects_malformed_firebase_claims(self):
        claims = self.claims()
        claims["firebase"] = "google.com"
        with self.assertRaises(FirebaseTokenError):
            validate_firebase_claims(claims, "baty-ac397")

    def test_verifier_is_called_for_the_expected_project(self):
        calls = []

        def fake_verifier(token, request, audience):
            calls.append((token, request, audience))
            return self.claims()

        self.assertEqual(verify_firebase_id_token("signed-id-token", "baty-ac397", fake_verifier), "user-123")
        self.assertEqual(calls[0][0], "signed-id-token")
        self.assertEqual(calls[0][2], "baty-ac397")
        self.assertTrue(callable(calls[0][1]))


if __name__ == "__main__":
    unittest.main()

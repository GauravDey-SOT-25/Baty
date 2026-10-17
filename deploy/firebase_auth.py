"""Firebase Google ID-token verification for the Modal inference API."""

import time
from urllib.error import HTTPError
from urllib.request import Request as UrlRequest, urlopen


class FirebaseTokenError(ValueError):
    """Raised when a Firebase token is not a verified Google sign-in."""


class _CertResponse:
    def __init__(self, status: int, data: bytes, headers):
        self.status = status
        self.data = data
        self.headers = headers


class _FirebaseCertRequest:
    """Minimal google-auth transport using Python's verified TLS defaults."""

    def __call__(self, url, method="GET", body=None, headers=None, timeout=10, **kwargs):
        request = UrlRequest(url, data=body, headers=dict(headers or {}), method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                return _CertResponse(response.status, response.read(), response.headers)
        except HTTPError as response:
            try:
                return _CertResponse(response.code, response.read(), response.headers)
            finally:
                response.close()


def validate_firebase_claims(claims: dict, project_id: str) -> str:
    """Enforce Firebase project, issuer, user, Google-provider, and email claims."""
    firebase = claims.get("firebase")
    uid = claims.get("sub")
    auth_time = claims.get("auth_time")
    if (
        claims.get("aud") != project_id
        or claims.get("iss") != f"https://securetoken.google.com/{project_id}"
        or not isinstance(uid, str)
        or not uid
        or len(uid) > 128
        or not isinstance(firebase, dict)
        or firebase.get("sign_in_provider") != "google.com"
        or claims.get("email_verified") is not True
        or not isinstance(auth_time, (int, float))
        or auth_time <= 0
        or auth_time > time.time() + 60
    ):
        raise FirebaseTokenError("A verified Google account for this Firebase project is required.")
    return uid


def verify_firebase_id_token(token: str, project_id: str, verifier=None) -> str:
    """Verify the JWT signature and standard claims against Google's Firebase certs."""
    if not isinstance(token, str) or not token or len(token) > 8192:
        raise FirebaseTokenError("Missing or oversized Firebase ID token.")
    try:
        if verifier is None:
            from google.oauth2.id_token import verify_firebase_token

            verifier = verify_firebase_token
        claims = verifier(token, _FirebaseCertRequest(), audience=project_id)
    except Exception as exc:
        raise FirebaseTokenError("Firebase ID token signature or standard claims are invalid.") from exc
    try:
        return validate_firebase_claims(claims, project_id)
    except (AttributeError, TypeError) as exc:
        raise FirebaseTokenError("Firebase ID token claims are malformed.") from exc

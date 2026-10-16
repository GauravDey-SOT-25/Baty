from __future__ import annotations
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def classifier_text(raw: str) -> str:
    """Canonicalize URL text for the local classifier, masking query values."""
    parts = urlsplit(raw if "://" in raw else "//" + raw)
    host = (parts.hostname or "").lower().rstrip(".")
    query = urlencode([(key[:80], "REDACTED") for key, _ in parse_qsl(parts.query, keep_blank_values=True)[:30]])
    return urlunsplit((parts.scheme.lower() if parts.scheme else "", host, parts.path[:2048], query, ""))

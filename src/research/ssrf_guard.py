"""SSRF and URL safety guard for the research extract feature.

Extends the existing url_analysis.analyzer.normalize_url with additional
restrictions appropriate for server-side outbound HTTP requests:
- Only HTTPS is accepted (HTTP would leak plaintext to the provider)
- Cloud metadata endpoints are blocked
- Response size limits are documented for callers

This module treats all user-supplied URLs as untrusted.
"""
from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit

# Well-known cloud instance metadata endpoints (IPv4 and IPv6 link-local)
_METADATA_PATTERNS = [
    # AWS IMDSv1/v2
    re.compile(r"^169\.254\.169\.254$"),
    # GCP metadata
    re.compile(r"^metadata\.google\.internal$"),
    # Azure IMDS
    re.compile(r"^169\.254\.169\.254$"),
    # Link-local prefix (covers all 169.254.x.x)
    re.compile(r"^169\.254\.\d+\.\d+$"),
]

# Blocked IP ranges beyond private/loopback
_BLOCKED_PREFIXES = [
    "0.",          # unspecified / this-network
    "100.64.",     # shared address space (RFC 6598)
    "192.0.0.",    # IETF Protocol Assignments
    "192.0.2.",    # TEST-NET-1
    "198.51.100.", # TEST-NET-2
    "203.0.113.",  # TEST-NET-3
    "240.",        # reserved
    "255.",        # broadcast
]


class SSRFError(ValueError):
    """Raised when a URL is rejected for SSRF-prevention reasons."""


def validate_extract_url(raw: str) -> str:
    """Validate and normalise a URL for use in an extract request.

    Returns the normalised URL string on success.
    Raises SSRFError with a user-safe message if the URL is not acceptable.

    Security properties enforced:
    - Only HTTPS scheme accepted
    - No credentials in URL (user:pass)
    - No localhost, .local, .internal hostnames
    - No private, loopback, link-local, or reserved IP addresses
    - No cloud metadata endpoint patterns
    - No control characters
    - Maximum 4096 characters
    """
    raw = (raw or "").strip()
    if not raw:
        raise SSRFError("URL must not be empty")
    if len(raw) > 4096:
        raise SSRFError("URL exceeds the 4096 character limit")
    if any(ord(c) < 32 for c in raw):
        raise SSRFError("URL contains control characters")

    # Reuse existing normalizer for base checks (scheme, credentials, port)
    try:
        from src.url_analysis.analyzer import normalize_url
        normalised = normalize_url(raw)
    except ValueError as exc:
        raise SSRFError(str(exc)) from exc

    parts = urlsplit(normalised)

    # Extract-specific: require HTTPS (no plain HTTP to a provider endpoint)
    if parts.scheme != "https":
        raise SSRFError("Only HTTPS URLs are accepted for content extraction")

    host = (parts.hostname or "").lower()

    # Browsers and some HTTP stacks accept legacy numeric host forms such as
    # 127.1, 2130706433, or 0x7f000001 as IPv4 addresses. Python's strict
    # ipaddress parser does not accept all of these, so reject ambiguous
    # numeric-only host spellings before treating a host as a DNS name.
    if re.fullmatch(r"(?i)(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*", host):
        raise SSRFError("Ambiguous numeric IP hostnames are not accepted")

    # Percent-encoded hostnames can be decoded differently by URL consumers.
    if "%" in host:
        raise SSRFError("Percent-encoded hostnames are not accepted")

    # Block cloud metadata patterns
    for pattern in _METADATA_PATTERNS:
        if pattern.match(host):
            raise SSRFError("Cloud metadata endpoints are not accepted")

    # Block additional reserved prefixes
    for prefix in _BLOCKED_PREFIXES:
        if host.startswith(prefix):
            raise SSRFError("Reserved or documentation IP ranges are not accepted")

    # Block .internal TLD (common cloud-internal DNS)
    if host.endswith(".internal"):
        raise SSRFError("Internal hostnames are not accepted")

    # Extra check: if host is an IPv6 link-local
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
        if ip.is_link_local or ip.is_loopback or not ip.is_global:
            raise SSRFError("Non-global IP addresses are not accepted")
    except ValueError:
        pass  # Non-IP hostname — already handled by normalize_url

    return normalised


def validate_extract_urls(raw_urls: list) -> tuple[list[str], list[dict]]:
    """Validate a list of URLs for extraction.

    Returns (valid_urls, errors) where errors is a list of dicts
    with 'url' and 'error' keys for rejected entries.
    """
    if not isinstance(raw_urls, list):
        raise ValueError("urls must be a list")
    if len(raw_urls) > 20:
        raise ValueError("At most 20 URLs may be extracted per request")

    valid: list[str] = []
    errors: list[dict] = []

    for entry in raw_urls:
        if not isinstance(entry, str):
            errors.append({"url": repr(entry), "error": "URL must be a string"})
            continue
        if len(entry) > 4096:
            errors.append({"url": entry[:80] + "…", "error": "URL exceeds 4096 characters"})
            continue
        try:
            normalised = validate_extract_url(entry)
            valid.append(normalised)
        except SSRFError as exc:
            errors.append({"url": entry, "error": str(exc)})

    return valid, errors

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit, urlunsplit

MAX_URL_LENGTH = 4096


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw or len(raw) > MAX_URL_LENGTH:
        raise ValueError("URL is empty or exceeds the 4096 character limit")
    if any(ord(c) < 32 for c in raw):
        raise ValueError("Control characters are not allowed")
    candidate = raw if "://" in raw else "https://" + raw
    parts = urlsplit(candidate)
    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported")
    if not parts.hostname:
        raise ValueError("URL must include a hostname")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URLs containing embedded credentials are not accepted")
    try:
        parts.port  # validate malformed port syntax
    except ValueError as exc:
        raise ValueError("URL contains an invalid port") from exc
    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("Local hostnames are not accepted")
    try:
        ip = ipaddress.ip_address(host)
        if not ip.is_global:
            raise ValueError("Local, private, and reserved IP addresses are not accepted")
    except ValueError as exc:
        if "not accepted" in str(exc):
            raise
        # Non-IP hostnames continue to static syntax inspection.
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        raise ValueError("Hostname contains unsupported characters")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def analyze_url(raw: str) -> dict:
    normalized = normalize_url(raw)
    parts = urlsplit(normalized)
    host = parts.hostname or ""
    indicators: list[str] = []
    try:
        ipaddress.ip_address(host)
        indicators.append("ip_literal_host")
    except ValueError:
        pass
    if parts.scheme == "http":
        indicators.append("unencrypted_http")
    if "xn--" in host:
        indicators.append("punycode_hostname")
    if len(host.split(".")) >= 5:
        indicators.append("many_subdomains")
    if len(host) > 60:
        indicators.append("long_hostname")
    if "@" in parts.path:
        indicators.append("at_sign_in_path")
    risk = "moderate" if indicators else "unknown"
    return {"normalized_url": normalized, "host": host, "risk": risk,
            "checks": ["URL syntax", "scheme", "hostname character pattern", "static URL indicators"],
            "indicators": indicators, "recommendation": "Treat as unverified. No threat detected by this local syntax check is not the same as verified safe.",
            "limitations": ["No DNS, registration, certificate, redirect, or reputation check was performed.",
                            "The URL was not opened, resolved, fetched, or sent to a third party."],
            "assessment_timestamp": None}

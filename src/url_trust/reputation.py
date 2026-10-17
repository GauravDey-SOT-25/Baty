"""Opt-in domain-root lookups using user-configured reputation provider keys.

Never invoked implicitly. The caller must explicitly opt in, and only the
canonical HTTPS origin is sent; submitted paths, query strings, and fragments
are discarded before the request.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from src.research.config import load_env
from src.url_trust.registry import normalize_domain

_MAX_RESPONSE_BYTES = 128 * 1024
_TIMEOUT = 5


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Prevent API-key-bearing requests from following untrusted redirects."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def provider_status() -> dict:
    load_env()
    return {
        "google_safe_browsing_configured": bool(os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY", "").strip()),
        "virustotal_configured": bool(os.environ.get("VIRUSTOTAL_API_KEY", "").strip()),
        "external_calls_default": "off",
    }


def check_domain_reputation(raw: str) -> list[dict]:
    """Query configured services for a domain root after explicit user consent."""
    domain = normalize_domain(raw)
    origin = f"https://{domain}/"
    status = provider_status()
    results = []
    if status["google_safe_browsing_configured"]:
        results.append(_check_google(origin))
    else:
        results.append({"provider": "Google Safe Browsing", "status": "not_configured"})
    if status["virustotal_configured"]:
        results.append(_check_virustotal(origin))
    else:
        results.append({"provider": "VirusTotal", "status": "not_configured"})
    return results


def _check_google(origin: str) -> dict:
    key = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY", "").strip()
    endpoint = "https://safebrowsing.googleapis.com/v4/threatMatches:find?" + urllib.parse.urlencode({"key": key})
    body = {
        "client": {"clientId": "cyber-desk-local", "clientVersion": "1"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": origin}],
        },
    }
    try:
        response = _request(endpoint, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        payload = json.loads(response)
        matches = payload.get("matches", []) if isinstance(payload, dict) else []
        return {
            "provider": "Google Safe Browsing",
            "status": "match" if matches else "no_match_returned",
            "match_count": len(matches) if isinstance(matches, list) else 0,
            "threat_types": sorted({item.get("threatType", "unknown") for item in matches if isinstance(item, dict)}),
            "checked_at": _now(),
        }
    except Exception:
        return {"provider": "Google Safe Browsing", "status": "unavailable"}


def _check_virustotal(origin: str) -> dict:
    key = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
    url_id = base64.urlsafe_b64encode(origin.encode("utf-8")).decode("ascii").rstrip("=")
    endpoint = f"https://www.virustotal.com/api/v3/urls/{url_id}"
    try:
        payload = json.loads(_request(endpoint, headers={"x-apikey": key}))
        attributes = payload.get("data", {}).get("attributes", {}) if isinstance(payload, dict) else {}
        stats = attributes.get("last_analysis_stats", {})
        if not isinstance(stats, dict):
            stats = {}
        malicious = int(stats.get("malicious", 0) or 0)
        suspicious = int(stats.get("suspicious", 0) or 0)
        return {
            "provider": "VirusTotal",
            "status": "match" if malicious or suspicious else "no_malicious_or_suspicious_votes_returned",
            "malicious_votes": malicious,
            "suspicious_votes": suspicious,
            "analysis_date": attributes.get("last_analysis_date"),
            "checked_at": _now(),
        }
    except urllib.error.HTTPError as exc:
        exc.close()
        status = "not_found" if exc.code == 404 else "unavailable"
        return {"provider": "VirusTotal", "status": status}
    except Exception:
        return {"provider": "VirusTotal", "status": "unavailable"}


def _request(url: str, data: bytes | None = None, headers: dict | None = None) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(request, timeout=_TIMEOUT) as response:
        body = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(body) > _MAX_RESPONSE_BYTES:
        raise ValueError("Provider response exceeded limit")
    return body


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

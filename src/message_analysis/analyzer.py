from __future__ import annotations

import re
from urllib.parse import urlsplit

URL_RE = re.compile(r"https?://[^\s<>\"']+|\bwww\.[^\s<>\"']+", re.I)
INDICATORS = {
    "credential_request": re.compile(r"\b(password|passcode|verification code|one[- ]time code|OTP|PIN)\b", re.I),
    "urgent_action": re.compile(r"\b(urgent|immediately|act now|within \d+ hours?|account.{0,20}(?:suspend|lock|close))\b", re.I),
    "payment_pressure": re.compile(r"\b(wire transfer|gift cards?|crypto(?:currency)?|payment.{0,20}(?:today|immediately))\b", re.I),
    "link_action": re.compile(r"\b(click|sign in|log in|verify your account|open the link)\b", re.I),
    "impersonation_claim": re.compile(r"\b(IT support|help ?desk|CEO|payroll|bank security|tax authority)\b", re.I),
}


def extract_urls(text: str) -> list[str]:
    return [m.group(0).rstrip(".,);]}") for m in URL_RE.finditer(text or "")]


def analyze_message(text: str, sender: str | None = None, context: str | None = None, urls: list[str] | None = None) -> dict:
    text = (text or "")[:20_000]
    combined = " ".join(x for x in (text, sender or "", context or "") if x)
    evidence: list[dict[str, str]] = []
    for kind, pattern in INDICATORS.items():
        match = pattern.search(combined)
        if match:
            evidence.append({"indicator": kind, "excerpt": match.group(0)[:160]})
    found_urls = list(dict.fromkeys((urls or []) + extract_urls(text)))
    for raw in found_urls[:20]:
        candidate = raw if "://" in raw else "http://" + raw
        host = urlsplit(candidate).hostname or ""
        if host and (host.startswith("xn--") or "xn--" in host):
            evidence.append({"indicator": "punycode_domain", "excerpt": host[:180]})
        if host and len(host.split(".")) > 4:
            evidence.append({"indicator": "many_subdomains", "excerpt": host[:180]})

    # This is a transparent rule baseline, not a calibrated probability or verdict.
    points = len(evidence)
    risk = "high" if points >= 3 else "moderate" if points >= 1 else "low"
    if not text.strip():
        risk = "unknown"
    recommendations = ["Do not use links or contact details in the message until independently verified.",
                       "Contact the organization through a known, trusted channel if the request may be genuine."] if points else [
                       "No strong indicator was found by this basic local check; that does not prove the message is safe.",
                       "Verify unexpected requests through a separate trusted channel."]
    return {"risk": risk, "evidence": evidence, "explanation": "Rule-based indicators are clues only; context and source verification matter.",
            "recommendations": recommendations, "limitations": ["No sender authentication, reputation, or external threat-intelligence checks were performed.",
            "This score is not calibrated and is not a probability."], "urls": found_urls[:20], "confidence": None}

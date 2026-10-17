import os
import requests
from typing import Dict, Any, List
from urllib.parse import urlparse

# Google Safe Browsing API Configuration
GSB_API_KEY = os.environ.get(
    "GOOGLE_SAFE_BROWSING_API_KEY",
    "AIzaSyB_33SuQo2XQ15HpHTL_JZxoa4n2Q8pRjg"
)

# VirusTotal v3 API Configuration
VT_API_KEY = os.environ.get(
    "VIRUSTOTAL_API_KEY",
    "688c4e575ec751c4ae6792c8b08530cd0e4263848e81526d2df2516f913c19b6"
)

def check_google_safe_browsing(target_url: str, timeout: float = 4.0) -> Dict[str, Any]:
    """
    Queries Google Safe Browsing API v4 for malware, phishing, and harmful applications.
    """
    if not GSB_API_KEY:
        return {
            "success": False,
            "status": "disabled",
            "message": "Google Safe Browsing API key not configured"
        }

    api_endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_API_KEY}"
    payload = {
        "client": {
            "clientId": "decentralized-url-trust-verifier",
            "clientVersion": "2.0.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE",
                "SOCIAL_ENGINEERING",
                "UNWANTED_SOFTWARE",
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": target_url}]
        }
    }

    try:
        resp = requests.post(api_endpoint, json=payload, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            matches = data.get("matches", [])
            is_threat = len(matches) > 0
            threat_types = list(set(m.get("threatType") for m in matches))
            return {
                "success": True,
                "status": "Threat Detected" if is_threat else "Clean (No Threats Found)",
                "is_threat": is_threat,
                "threat_types": threat_types,
                "threat_count": len(matches),
                "details": matches
            }
        elif resp.status_code == 403:
            err_data = resp.json().get("error", {})
            err_msg = err_data.get("message", "Permission Denied")
            activation_url = "https://console.developers.google.com/apis/api/safebrowsing.googleapis.com/overview?project=288219958251"
            return {
                "success": False,
                "status": "Activation Required in GCP",
                "is_threat": False,
                "error": err_msg,
                "activation_url": activation_url,
                "note": "Safe Browsing API requires 1-click activation in Google Cloud Console."
            }
        else:
            return {
                "success": False,
                "status": f"HTTP {resp.status_code}",
                "is_threat": False,
                "error": resp.text[:200]
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "Connection Error",
            "is_threat": False,
            "error": str(e)
        }


def check_virustotal(domain_or_url: str, timeout: float = 4.5) -> Dict[str, Any]:
    """
    Queries VirusTotal v3 API for real-time reputation across 90+ antivirus & security engines.
    """
    if not VT_API_KEY:
        return {
            "success": False,
            "status": "disabled",
            "message": "VirusTotal API key not configured"
        }

    # Extract clean domain
    parsed = urlparse(domain_or_url if "://" in domain_or_url else f"https://{domain_or_url}")
    clean_domain = parsed.netloc.split(":")[0] if parsed.netloc else domain_or_url.split("/")[0]

    api_endpoint = f"https://www.virustotal.com/api/v3/domains/{clean_domain}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        resp = requests.get(api_endpoint, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            attributes = data.get("attributes", {})
            stats = attributes.get("last_analysis_stats", {})

            malicious = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            harmless = stats.get("harmless", 0)
            undetected = stats.get("undetected", 0)
            total_engines = malicious + suspicious + harmless + undetected

            reputation = attributes.get("reputation", 0)
            categories = attributes.get("categories", {})

            is_malicious = (malicious >= 2) or (malicious >= 1 and reputation < 0) or (suspicious >= 3)
            verdict = "Clean"
            if is_malicious:
                verdict = f"MALICIOUS ({malicious}/{total_engines} engines flagged)"
            elif malicious > 0:
                verdict = f"Clean (1/{total_engines} Disputed Engine Flag)"
            elif suspicious > 0:
                verdict = f"Suspicious ({suspicious}/{total_engines} engines flagged)"
            else:
                verdict = f"Clean (0/{total_engines} Antivirus Engines Flagged)"

            return {
                "success": True,
                "status": verdict,
                "domain": clean_domain,
                "is_threat": is_malicious,
                "malicious_count": malicious,
                "suspicious_count": suspicious,
                "harmless_count": harmless,
                "undetected_count": undetected,
                "total_engines": total_engines,
                "reputation_score": reputation,
                "categories": list(categories.values())[:3],
                "last_analysis_date": attributes.get("last_analysis_date")
            }
        else:
            return {
                "success": False,
                "status": f"HTTP {resp.status_code}",
                "is_threat": False,
                "error": resp.text[:200]
            }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status": "Connection Error",
            "is_threat": False,
            "error": str(e)
        }


def get_threat_intelligence(target_url: str, domain: str) -> Dict[str, Any]:
    """
    Aggregates Google Safe Browsing and VirusTotal telemetry into a unified Threat Intel Shield.
    """
    vt_result = check_virustotal(domain)
    gsb_result = check_google_safe_browsing(target_url)

    is_any_threat = vt_result.get("is_threat", False) or gsb_result.get("is_threat", False)

    return {
        "is_threat_detected": is_any_threat,
        "virustotal": vt_result,
        "google_safe_browsing": gsb_result
    }

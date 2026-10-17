import hashlib
import socket
import ssl
from urllib.parse import urlparse
from typing import Dict, Any, Tuple, Optional

def normalize_url(raw_url: str) -> Tuple[str, str, int]:
    """
    Normalizes a URL into:
    - canonical_url: Normalized lowercase scheme and domain
    - hostname: Clean domain/host without port or path
    - port: Target port (default 443 for https, 80 for http)
    """
    clean_url = raw_url.strip()
    if not clean_url.startswith(("http://", "https://")):
        # Default to https for security verification
        clean_url = "https://" + clean_url

    parsed = urlparse(clean_url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    if ":" in netloc:
        host, port_str = netloc.split(":", 1)
        port = int(port_str)
    else:
        host = netloc
        port = 443 if scheme == "https" else 80

    # Canonical representation: scheme://host
    canonical_url = f"{scheme}://{host}"
    return canonical_url, host, port


def compute_url_hash(input_str: str) -> str:
    """
    Computes standard SHA-256 hash of the canonical domain/URL.
    Returns 0x-prefixed 64-character lowercase hex string.
    """
    _, host, _ = normalize_url(input_str)
    # Hash the normalized domain name
    raw_hash = hashlib.sha256(host.encode("utf-8")).hexdigest()
    return f"0x{raw_hash}"


def compute_string_hash(text: str) -> str:
    """Computes SHA-256 hash of arbitrary string."""
    raw_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
    return f"0x{raw_hash}"


def fetch_ssl_fingerprint(hostname: str, port: int = 443, timeout: float = 3.5) -> Dict[str, Any]:
    """
    Connects to the target host and retrieves its live SSL certificate.
    Calculates the SHA-256 fingerprint from the raw DER certificate bytes.
    """
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED

    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                der_cert = ssock.getpeercert(binary_form=True)
                if not der_cert:
                    return {
                        "success": False,
                        "error": "No binary certificate returned",
                        "fingerprint": None,
                        "issuer": None,
                        "subject": None
                    }

                # Calculate SHA-256 of the DER bytes
                sha256_digest = hashlib.sha256(der_cert).hexdigest()
                hex_fingerprint = f"0x{sha256_digest}"

                # Extract human-readable details
                parsed_cert = ssock.getpeercert(binary_form=False) or {}
                issuer_dict = dict(x[0] for x in parsed_cert.get("issuer", []))
                subject_dict = dict(x[0] for x in parsed_cert.get("subject", []))

                return {
                    "success": True,
                    "fingerprint": hex_fingerprint,
                    "raw_sha256": sha256_digest,
                    "issuer": issuer_dict.get("organizationName") or issuer_dict.get("commonName") or "Unknown Issuer",
                    "subject": subject_dict.get("commonName") or hostname,
                    "expires": parsed_cert.get("notAfter", "Unknown"),
                    "version": parsed_cert.get("version", "Unknown")
                }

    except ssl.SSLCertVerificationError as e:
        # Self-signed, expired, or invalid SSL
        return {
            "success": False,
            "error": f"SSL Verification Failed: {e.reason}",
            "fingerprint": None,
            "is_suspicious": True
        }
    except (socket.timeout, TimeoutError):
        return {
            "success": False,
            "error": f"Connection timed out after {timeout}s",
            "fingerprint": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "fingerprint": None
        }

"""Explicit HTTPS certificate observation with DNS-rebinding/SSRF safeguards.

This function is only called when a local user checks the UI opt-in. It makes a
TLS handshake to a public hostname on port 443, does not issue an HTTP request,
and never follows redirects.
"""
from __future__ import annotations

import ipaddress
import hashlib
import socket
import ssl
import threading
from datetime import datetime, timezone
from urllib.parse import urlsplit

from src.research.ssrf_guard import SSRFError, validate_extract_url

_INSPECTION_SLOTS = threading.BoundedSemaphore(2)
_TIMEOUT_SECONDS = 3.0


def inspect_tls_certificate(raw: str) -> dict:
    try:
        normalized = validate_extract_url(raw)
    except SSRFError as exc:
        raise ValueError(str(exc)) from exc
    parts = urlsplit(normalized)
    host = parts.hostname or ""
    if parts.port not in (None, 443):
        raise ValueError("TLS inspection only connects to the standard HTTPS port 443")
    if not _INSPECTION_SLOTS.acquire(blocking=False):
        raise ValueError("TLS inspection is busy; try again shortly")
    try:
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError("The public hostname could not be resolved") from exc
        if not addresses or len(addresses) > 32:
            raise ValueError("The hostname returned an invalid number of addresses")
        parsed_addresses = []
        for family, socktype, proto, _canonname, sockaddr in addresses:
            try:
                ip = ipaddress.ip_address(sockaddr[0])
            except ValueError as exc:
                raise ValueError("The hostname resolved to an unsupported address") from exc
            if not ip.is_global:
                raise ValueError("TLS inspection is blocked because the hostname resolves to a non-public address")
            parsed_addresses.append((family, socktype, proto, sockaddr))

        failures = []
        for family, socktype, proto, sockaddr in parsed_addresses[:3]:
            try:
                certificate_der, verified = _fetch_certificate(host, family, socktype, proto, sockaddr)
                return {
                    "domain": host,
                    "certificate_fingerprint": hashlib.sha256(certificate_der).hexdigest(),
                    "certificate_valid": verified,
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "connection": "TLS handshake only; no HTTP request or redirects",
                }
            except ssl.SSLCertVerificationError as exc:
                failures.append(exc)
                try:
                    certificate_der = _fetch_unverified_certificate(host, family, socktype, proto, sockaddr)
                    return {
                        "domain": host,
                        "certificate_fingerprint": hashlib.sha256(certificate_der).hexdigest(),
                        "certificate_valid": False,
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                        "connection": "TLS handshake only; certificate validation failed; no HTTP request or redirects",
                    }
                except (OSError, ssl.SSLError) as fallback_exc:
                    failures.append(fallback_exc)
            except (OSError, ssl.SSLError) as exc:
                failures.append(exc)
        raise ValueError("A TLS certificate could not be retrieved from this hostname")
    finally:
        _INSPECTION_SLOTS.release()


def _fetch_certificate(host: str, family: int, socktype: int, proto: int, sockaddr) -> tuple[bytes, bool]:
    raw_socket = socket.socket(family, socktype, proto)
    try:
        raw_socket.settimeout(_TIMEOUT_SECONDS)
        raw_socket.connect(sockaddr)  # Connect to the checked DNS answer; do not resolve again.
        context = ssl.create_default_context()
        with context.wrap_socket(raw_socket, server_hostname=host) as tls_socket:
            certificate = tls_socket.getpeercert(binary_form=True)
            if not certificate:
                raise ssl.SSLError("Peer provided no certificate")
            return certificate, True
    finally:
        # wrap_socket takes ownership after a successful wrap; close is safe in either case.
        raw_socket.close()


def _fetch_unverified_certificate(host: str, family: int, socktype: int, proto: int, sockaddr) -> bytes:
    """Fetch a peer fingerprint for diagnostics without treating it as valid."""
    raw_socket = socket.socket(family, socktype, proto)
    try:
        raw_socket.settimeout(_TIMEOUT_SECONDS)
        raw_socket.connect(sockaddr)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        with context.wrap_socket(raw_socket, server_hostname=host) as tls_socket:
            certificate = tls_socket.getpeercert(binary_form=True)
            if not certificate:
                raise ssl.SSLError("Peer provided no certificate")
            return certificate
    finally:
        raw_socket.close()

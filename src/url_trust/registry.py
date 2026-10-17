"""Private local registry for user-maintained domain observations.

Entries are local notes, not independent proof that a site is safe or trusted.
No URL is opened, resolved, or sent anywhere by registry operations.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from src.url_analysis.analyzer import normalize_url

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CYBER_DATA_PATH", ROOT / "data"))
REGISTRY_FILE = DATA_DIR / "url_trust_registry.json"
MAX_RECORDS = 1000
_LOCK = threading.RLock()
_FINGERPRINT_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def normalize_domain(raw: str) -> str:
    """Normalize a URL to its DNS hostname, ignoring path, query, and fragment."""
    normalized = normalize_url(raw)
    host = (urlsplit(normalized).hostname or "").rstrip(".").lower()
    if not host:
        raise ValueError("URL must include a hostname")
    # Trust records are domain-scoped, not IP-address attestations.
    try:
        import ipaddress
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Trust records require a DNS hostname, not an IP address")
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local and internal hostnames cannot be registered")
    return host


def domain_digest(raw: str) -> str:
    """Return the SHA-256 hex digest of a normalized domain name."""
    return hashlib.sha256(normalize_domain(raw).encode("utf-8")).hexdigest()


def normalize_fingerprint(value: str) -> str:
    """Accept a certificate's SHA-256 fingerprint and return 64 lowercase hex chars."""
    if not isinstance(value, str):
        raise ValueError("Certificate fingerprint must be text")
    compact = value.strip().lower().replace(":", "").replace("-", "")
    if compact.startswith("0x"):
        compact = compact[2:]
    if not _FINGERPRINT_RE.fullmatch(compact):
        raise ValueError("Enter a 64-character SHA-256 certificate fingerprint")
    return compact


def inspect(raw: str) -> dict:
    domain = normalize_domain(raw)
    digest = hashlib.sha256(domain.encode("utf-8")).hexdigest()
    records = _read_records()
    record = next((item for item in records if item["domain_hash"] == digest), None)
    return {
        "domain": domain,
        "domain_hash": digest,
        "record": record,
        "status": "recorded" if record else "no_local_record",
        "notice": "A local registry match is a user-maintained note, not proof that the domain is safe.",
    }


def list_records(limit: int = 100) -> dict:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    records = _read_records()
    records.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
    return {"records": records[:limit], "total": len(records), "limit": limit}


def register(raw: str, fingerprint: str, metadata: str = "") -> dict:
    domain = normalize_domain(raw)
    digest = hashlib.sha256(domain.encode("utf-8")).hexdigest()
    fingerprint = normalize_fingerprint(fingerprint)
    if not isinstance(metadata, str) or len(metadata) > 500:
        raise ValueError("metadata must be text of at most 500 characters")
    now = _now()
    with _LOCK:
        records = _read_records_locked()
        existing = next((item for item in records if item["domain_hash"] == digest), None)
        if existing:
            existing.update({
                "domain": domain,
                "certificate_fingerprint": fingerprint,
                "metadata": metadata.strip(),
                "status": "active",
                "updated_at": now,
                "revoked_at": None,
                "revocation_reason": "",
            })
            result = existing.copy()
        else:
            if len(records) >= MAX_RECORDS:
                raise ValueError(f"Local registry is limited to {MAX_RECORDS} records")
            result = {
                "domain": domain,
                "domain_hash": digest,
                "certificate_fingerprint": fingerprint,
                "metadata": metadata.strip(),
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "revoked_at": None,
                "revocation_reason": "",
                "record_basis": "Manually recorded by the local user",
            }
            records.append(result)
        _write_records(records)
    return result


def revoke(raw: str, reason: str) -> dict:
    domain = normalize_domain(raw)
    digest = hashlib.sha256(domain.encode("utf-8")).hexdigest()
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError("A revocation reason of 1–500 characters is required")
    with _LOCK:
        records = _read_records_locked()
        record = next((item for item in records if item["domain_hash"] == digest), None)
        if record is None:
            raise ValueError("No local registry record exists for this domain")
        record.update({
            "status": "revoked",
            "updated_at": _now(),
            "revoked_at": _now(),
            "revocation_reason": reason.strip(),
        })
        _write_records(records)
        return record.copy()


def _read_records() -> list[dict]:
    with _LOCK:
        return _read_records_locked()


def _read_records_locked() -> list[dict]:
    if not REGISTRY_FILE.exists():
        return []
    try:
        raw = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Local trust registry cannot be read; preserve and inspect its data file.") from exc
    if not isinstance(raw, list) or len(raw) > MAX_RECORDS or not all(isinstance(item, dict) for item in raw):
        raise RuntimeError("Local trust registry has an invalid data structure; it was not modified.")
    return raw


def _write_records(records: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{REGISTRY_FILE.name}.", dir=DATA_DIR)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, REGISTRY_FILE)
        os.chmod(REGISTRY_FILE, 0o600)
    finally:
        temp_path.unlink(missing_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

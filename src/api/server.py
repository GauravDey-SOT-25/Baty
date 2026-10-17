from __future__ import annotations

import json
import importlib.util
import ipaddress
import os
import ssl
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.assistant.service import answer
from src.assistant.local_model import ADAPTER_DIR, MODEL_DIR
from src.incident_search.search import search_incidents
from src.message_analysis.analyzer import analyze_message
from src.url_analysis.analyzer import analyze_url
from src.ocr.local_ocr import OCRUnavailableError, extract_text_from_base64
from src.url_trust.registry import inspect as inspect_trust_target, list_records as list_trust_records
from src.url_trust.registry import register as register_trust_record, revoke as revoke_trust_record
from src.url_trust.tls import inspect_tls_certificate
from src.url_trust.reputation import check_domain_reputation, provider_status as trust_provider_status

# Research subsystem — imported lazily to keep startup fast
def _research():
    from src.research import service as _svc
    return _svc

ROOT = Path(__file__).resolve().parents[2]
COMFEST_ROOT = ROOT / "Comfest - 26"
_RATE_LOCK = threading.Lock()
_RATE_EVENTS = defaultdict(deque)
_API_EVENTS = defaultdict(deque)
_API_LIMITS = {
    "/api/assistant": 12, "/api/modal/assistant": 3, "/api/incidents": 60, "/api/ocr": 12,
    "/api/trust/inspect": 20, "/api/trust/register": 20, "/api/trust/revoke": 20,
}
_MAX_REQUEST_BYTES = 32_768
_MAX_OCR_REQUEST_BYTES = 6 * 1024 * 1024
_MODAL_ASSISTANT_URL = "https://gauravdey2020--cyber-qwen-modal-preview-inference-api.us-east.modal.run/api/assistant"


def _modal_tls_context() -> ssl.SSLContext:
    """Use a configured CA bundle, including macOS's system PEM bundle."""
    defaults = ssl.get_default_verify_paths()
    candidates = (
        os.environ.get("SSL_CERT_FILE"),
        defaults.cafile,
        "/etc/ssl/cert.pem",
        "/etc/ssl/certs/ca-certificates.crt",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def _research_rate_allowed(ip: str, path: str) -> bool:
    """Bound provider usage per local client; this is not user authentication."""
    if path.endswith("/search"):
        limit = 20
    elif path.endswith("/extract"):
        limit = 10
    elif path == "/api/research/responses":
        limit = 12
    elif path == "/api/research/findall/ingest":
        limit = 3
    elif path == "/api/research/findall/runs":
        limit = 2
    elif path == "/api/research/tasks":
        limit = 3
    elif path == "/api/research/monitors":
        limit = 2
    elif path == "/api/research/enrich":
        limit = 3
    else:
        limit = 60
    if path.startswith("/api/research/tasks/"):
        bucket = "task-status"
    elif path.startswith("/api/research/monitors/"):
        bucket = "monitor-write"
    elif path in {"/api/research/tasks", "/api/research/monitors", "/api/research/enrich", "/api/research/responses", "/api/research/findall/ingest", "/api/research/findall/runs"}:
        bucket = path.removeprefix("/api/research/")
    else:
        bucket = "research-other"
    key = (ip, bucket)
    now = time.monotonic()
    with _RATE_LOCK:
        events = _RATE_EVENTS[key]
        while events and now - events[0] >= 60:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalCyberAssistant/0.1"
    def setup(self):
        # Bound slow header/body clients. The local listener is intentionally
        # single-user; long-lived streaming connections are not supported.
        self.request.settimeout(15)
        super().setup()

    def _send(self, code: int, payload, content_type="application/json; charset=utf-8"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' https://www.gstatic.com https://apis.google.com; media-src 'self' https://pplx-res.cloudinary.com; connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com https://baty-ac397-default-rtdb.firebaseio.com https://*.firebaseio.com https://*.firebasedatabase.app https://www.googleapis.com https://apis.google.com wss://baty-ac397-default-rtdb.firebaseio.com wss://*.firebaseio.com wss://*.firebasedatabase.app; frame-src https://baty-ac397.firebaseapp.com https://accounts.google.com; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if not _request_host_allowed(self):
            return self._send(403, {"error": "Requests must use the local loopback address."})
        if urlparse(self.path).path == "/api/health":
            return self._send(200, {
                "status": "ok",
                "mode": "local-only",
                "model_available": _model_available(),
                "model_runtime_available": importlib.util.find_spec("mlx_lm") is not None,
                "adapter_enabled": (ADAPTER_DIR / "adapters.safetensors").is_file(),
            })
        path = urlparse(self.path).path
        if path.startswith("/api/research/") and not _research_rate_allowed(self.client_address[0], path):
            return self._send(429, {"error": "Local research rate limit exceeded; wait a minute and retry."})
        if path in {"/", "/index.html"}:
            homepage = COMFEST_ROOT / "index.html"
            if homepage.is_file():
                return self._send(200, homepage.read_bytes(), "text/html; charset=utf-8")
            return self._send(503, {"error": "The Comfest homepage is unavailable."})
        if path in {"/workspace", "/workspace/", "/workspace/index.html"}:
            return self._send(200, (ROOT / "frontend" / "index.html").read_bytes(), "text/html; charset=utf-8")
        comfest_static = {
            "/styles.css": (COMFEST_ROOT / "styles.css", "text/css; charset=utf-8"),
            "/script.js": (COMFEST_ROOT / "script.js", "application/javascript; charset=utf-8"),
            "/ai-workspace.css": (COMFEST_ROOT / "ai-workspace.css", "text/css; charset=utf-8"),
            "/ai-workspace.js": (COMFEST_ROOT / "ai-workspace.js", "application/javascript; charset=utf-8"),
            "/blockchain.html": (COMFEST_ROOT / "blockchain.html", "text/html; charset=utf-8"),
            "/blockchain.css": (COMFEST_ROOT / "blockchain.css", "text/css; charset=utf-8"),
            "/blockchain.js": (COMFEST_ROOT / "blockchain.js", "application/javascript; charset=utf-8"),
        }
        if path in comfest_static:
            file_path, content_type = comfest_static[path]
            if file_path.is_file():
                return self._send(200, file_path.read_bytes(), content_type)
            return self._send(404, {"error": "Not found"})
        if path.startswith("/Parallel/"):
            parallel_root = (COMFEST_ROOT / "Parallel").resolve()
            source_path = (parallel_root / path.removeprefix("/Parallel/")).resolve()
            content_types = {
                ".css": "text/css; charset=utf-8",
                ".html": "text/html; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".md": "text/markdown; charset=utf-8",
                ".py": "text/plain; charset=utf-8",
                ".sol": "text/plain; charset=utf-8",
            }
            if source_path.is_relative_to(parallel_root) and source_path.is_file() and source_path.suffix.lower() in content_types:
                return self._send(200, source_path.read_bytes(), content_types[source_path.suffix.lower()])
            return self._send(404, {"error": "Not found"})
        if path.startswith("/assets/"):
            asset_path = (COMFEST_ROOT / path.lstrip("/")).resolve()
            assets_root = (COMFEST_ROOT / "assets").resolve()
            if asset_path.is_relative_to(assets_root) and asset_path.is_file() and asset_path.suffix.lower() in {".webp", ".png", ".jpg", ".jpeg", ".svg", ".avif"}:
                content_type = {".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml", ".avif": "image/avif"}[asset_path.suffix.lower()]
                return self._send(200, asset_path.read_bytes(), content_type)
            return self._send(404, {"error": "Not found"})
        if path == "/app.js":
            return self._send(200, (ROOT / "frontend" / "app.js").read_bytes(), "application/javascript; charset=utf-8")
        if path == "/responsive.css":
            return self._send(200, (ROOT / "frontend" / "responsive.css").read_bytes(), "text/css; charset=utf-8")
        if path == "/ocr.js":
            return self._send(200, (ROOT / "frontend" / "ocr.js").read_bytes(), "application/javascript; charset=utf-8")
        if path == "/research.js":
            return self._send(200, (ROOT / "frontend" / "research.js").read_bytes(), "application/javascript; charset=utf-8")
        if path == "/firebase-app.js":
            return self._send(200, (ROOT / "frontend" / "firebase-app.js").read_bytes(), "text/javascript; charset=utf-8")
        if path == "/trust.js":
            return self._send(200, (ROOT / "frontend" / "trust.js").read_bytes(), "application/javascript; charset=utf-8")
        if path == "/trust.css":
            return self._send(200, (ROOT / "frontend" / "trust.css").read_bytes(), "text/css; charset=utf-8")
        if path == "/api/trust/status":
            try:
                status = trust_provider_status()
                status.update({"mode": "local-user-maintained-registry", "blockchain_connected": False})
                return self._send(200, status)
            except Exception:
                return self._send(500, {"error": "Trust registry status is unavailable."})
        if path == "/api/trust/records":
            try:
                return self._send(200, list_trust_records())
            except Exception:
                return self._send(500, {"error": "Local trust records are unavailable."})
        # Research GET endpoints
        if path == "/api/research/status":
            try:
                return self._send(200, _research().get_provider_status())
            except Exception:
                return self._send(500, {"error": "Internal error"})
        if path.startswith("/api/research/tasks/"):
            task_id = path[len("/api/research/tasks/"):]
            if task_id and "/" not in task_id:
                try:
                    result = _research().get_task_status(task_id, poll=True)
                    code = 404 if "error" in result and "not found" in result.get("error", "").lower() else 200
                    return self._send(code, result)
                except Exception:
                    return self._send(500, {"error": "Internal error"})
        if path.startswith("/api/research/findall/runs/"):
            run_id = path[len("/api/research/findall/runs/"):]
            if run_id and "/" not in run_id:
                try:
                    result = _research().findall_status(
                        run_id, include_result=urlparse(self.path).query == "include_result=1"
                    )
                    return self._send(200, result)
                except Exception:
                    return self._send(500, {"error": "Internal error"})
        if path == "/api/research/tasks":
            try:
                return self._send(200, _research().list_research_tasks())
            except Exception:
                return self._send(500, {"error": "Internal error"})
        if path == "/api/research/monitors":
            try:
                return self._send(200, _research().list_monitors())
            except Exception:
                return self._send(500, {"error": "Internal error"})
        if path.startswith("/api/research/monitors/") and path.endswith("/events"):
            monitor_id = path[len("/api/research/monitors/"):-len("/events")].strip("/")
            try:
                result = _research().get_monitor_events(monitor_id)
                code = 404 if result.get("error") == "Monitor not found" else 200
                return self._send(code, result)
            except Exception:
                return self._send(500, {"error": "Internal error"})
        self._send(404, {"error": "Not found"})
    def do_POST(self):
        if not self.path.startswith("/api/"):
            return self._send(404, {"error": "Not found"})
        try:
            if not _request_host_allowed(self):
                return self._send(403, {"error": "Requests must use the local loopback address."})
            if len(self.headers.get_all("Host", [])) != 1:
                return self._send(400, {"error": "Exactly one Host header is required."})
            if self.headers.get("Transfer-Encoding") is not None:
                return self._send(400, {"error": "Transfer-Encoding is not supported."})
            if len(self.headers.get_all("Content-Length", [])) != 1:
                return self._send(400, {"error": "Exactly one Content-Length header is required."})
            origin = self.headers.get("Origin")
            if len(self.headers.get_all("Origin", [])) > 1:
                return self._send(403, {"error": "Ambiguous request origin is not allowed."})
            if origin and origin != f"http://{self.headers.get('Host', '').lower()}":
                return self._send(403, {"error": "Cross-origin requests are not allowed"})
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                return self._send(415, {"error": "Content-Type must be application/json"})
            path = urlparse(self.path).path
            max_request_bytes = _MAX_OCR_REQUEST_BYTES if path == "/api/ocr" else _MAX_REQUEST_BYTES
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= max_request_bytes:
                return self._send(413, {"error": f"Request body must be between 1 and {max_request_bytes} bytes"})
            if path.startswith("/api/") and not _api_rate_allowed(self.client_address[0], path):
                return self._send(429, {"error": "Local API rate limit exceeded; wait a minute and retry."})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                return self._send(400, {"error": "JSON request body must be an object"})
            if path.startswith("/api/research/") and not _research_rate_allowed(self.client_address[0], path):
                return self._send(429, {"error": "Local research rate limit exceeded; wait a minute and retry."})
            if path == "/api/ocr":
                result = {"text": extract_text_from_base64(_string(data, "image_base64", 5_600_000, required=True))}
            elif path == "/api/message":
                urls = data.get("urls")
                if urls is not None and (not isinstance(urls, list) or len(urls) > 20 or not all(isinstance(url, str) and len(url) <= 4096 for url in urls)):
                    raise ValueError("urls must be a list of at most 20 strings of 4096 characters or fewer")
                sender = _string(data, "sender", 500)
                context = _string(data, "context", 4000)
                result = analyze_message(_string(data, "text", 20000, required=True), sender, context, urls)
            elif path == "/api/url":
                result = analyze_url(_string(data, "url", 4096, required=True))
            elif path == "/api/trust/inspect":
                target = _string(data, "url", 4096, required=True)
                check_tls = data.get("check_tls", False)
                check_reputation = data.get("check_reputation", False)
                if not isinstance(check_tls, bool) or not isinstance(check_reputation, bool):
                    raise ValueError("check_tls and check_reputation must be booleans")
                result = inspect_trust_target(target)
                result["external_checks"] = {
                    "tls_requested": check_tls,
                    "reputation_requested": check_reputation,
                }
                if check_tls:
                    try:
                        result["tls"] = inspect_tls_certificate(target)
                    except ValueError as exc:
                        result["tls"] = {"status": "blocked_or_unavailable", "message": str(exc)}
                if check_reputation:
                    result["reputation"] = check_domain_reputation(target)
                result["limitations"] = [
                    "A local registry match is a user-maintained note, not proof of legitimacy or safety.",
                    "A TLS certificate proves a certificate was presented for the hostname; it does not prove the site owner or content is trustworthy.",
                    "Reputation services can miss threats and may retain submitted domain data.",
                    "No blockchain is connected and no decentralized consensus is performed.",
                ]
            elif path == "/api/trust/register":
                result = register_trust_record(
                    _string(data, "url", 4096, required=True),
                    _string(data, "certificate_fingerprint", 128, required=True),
                    _string(data, "metadata", 500) or "",
                )
            elif path == "/api/trust/revoke":
                result = revoke_trust_record(
                    _string(data, "url", 4096, required=True),
                    _string(data, "reason", 500, required=True),
                )
            elif path == "/api/assistant":
                include_records = data.get("include_local_records", True)
                if not isinstance(include_records, bool):
                    raise ValueError("include_local_records must be a boolean")
                result = answer(
                    _string(data, "question", 8000, required=True),
                    _string(data, "lab_context", 2000),
                    include_local_records=include_records,
                )
            elif path == "/api/modal/assistant":
                question = _string(data, "question", 8000, required=True).strip()
                if len(question) > 8000:
                    raise ValueError("question exceeds the 8000 character limit")
                bearer = self.headers.get_all("Authorization", [])
                if len(bearer) != 1 or not bearer[0].startswith("Bearer "):
                    return self._send(401, {"error": "Sign in with Google to use the Modal model."})
                id_token = bearer[0][7:].strip()
                if not id_token or len(id_token) > 8192:
                    return self._send(401, {"error": "Firebase sign-in token is missing or invalid."})
                from src.research.config import load_env
                load_env()
                proxy_key = os.environ.get("MODAL_PROXY_KEY", "").strip()
                proxy_secret = os.environ.get("MODAL_PROXY_SECRET", "").strip()
                if not proxy_key or not proxy_secret:
                    return self._send(503, {"error": "Modal access is not configured on this computer."})
                outbound = urllib.request.Request(
                    _MODAL_ASSISTANT_URL,
                    data=json.dumps({"question": question}).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {id_token}",
                        "Modal-Key": proxy_key,
                        "Modal-Secret": proxy_secret,
                    },
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(outbound, timeout=600, context=_modal_tls_context()) as response:
                        modal_body = json.loads(response.read())
                    return self._send(200, modal_body)
                except urllib.error.HTTPError as exc:
                    exc.close()
                    if exc.code in {401, 403, 422, 429, 503}:
                        detail = {
                            401: "Firebase sign-in is invalid or expired. Sign in again.",
                            403: "Use a verified Google account for Modal inference.",
                            422: "Modal rejected the question format.",
                            429: "Modal inference rate limit reached; wait and retry.",
                            503: "The Modal model is temporarily unavailable.",
                        }[exc.code]
                        return self._send(exc.code, {"error": detail})
                    return self._send(502, {"error": "Modal inference request failed."})
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                    return self._send(502, {"error": "Could not reach the Modal inference service."})
            elif path == "/api/incidents":
                result = search_incidents(_string(data, "description", 8000, required=True))
            elif path == "/api/research/search":
                sq = data.get("search_queries")
                result = _research().search(
                    _string(data, "query", 2000, required=True),
                    search_queries=sq if isinstance(sq, list) else None,
                    max_results=min(int(data.get("max_results", 10) or 10), 30),
                )
            elif path == "/api/research/responses":
                result = _research().quick_answer(
                    _string(data, "question", 8000, required=True),
                    effort=_string(data, "effort", 10) or "low",
                )
            elif path == "/api/research/findall/ingest":
                result = _research().findall_ingest(
                    _string(data, "objective", 8000, required=True)
                )
            elif path == "/api/research/findall/runs":
                conditions = data.get("match_conditions")
                if not isinstance(conditions, list):
                    raise ValueError("match_conditions must be a list")
                result = _research().findall_create(
                    _string(data, "objective", 8000, required=True),
                    _string(data, "entity_type", 120, required=True), conditions,
                    generator=_string(data, "generator", 20) or "preview",
                    match_limit=data.get("match_limit", 5),
                )
            elif path == "/api/research/extract":
                urls_raw = data.get("urls", [])
                if not isinstance(urls_raw, list):
                    raise ValueError("urls must be a list")
                result = _research().extract(
                    urls_raw,
                    objective=_string(data, "objective", 2000),
                )
            elif path == "/api/research/tasks":
                result = _research().create_research_task(
                    _string(data, "question", 8000, required=True),
                    processor=_string(data, "processor", 20) or "pro",
                )
            elif path == "/api/research/enrich":
                record = data.get("record")
                fields = data.get("fields")
                if not isinstance(record, dict) or not isinstance(fields, list):
                    raise ValueError("record must be an object and fields must be a list")
                result = _research().create_enrichment_task(
                    record,
                    fields,
                    processor=_string(data, "processor", 20) or "base",
                )
            elif path == "/api/research/monitors":
                result = _research().create_monitor(
                    _string(data, "query", 2000, required=True),
                )
            elif path.startswith("/api/research/monitors/") and path.endswith("/delete"):
                monitor_id = path[len("/api/research/monitors/"):-len("/delete")]
                result = _research().delete_monitor_by_id(monitor_id)
            else:
                return self._send(404, {"error": "Not found"})
            self._send(200, result)
        except OCRUnavailableError as exc:
            self._send(503, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception:
            self._send(500, {"error": "Internal error"})
    def log_message(self, fmt, *args):
        # Request content is never logged.
        return


def _string(data: dict, name: str, limit: int, required: bool = False) -> str | None:
    value = data.get(name, "")
    if value is None and not required:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if required and not value.strip():
        raise ValueError(f"{name} is required")
    if len(value) > limit:
        raise ValueError(f"{name} exceeds the {limit} character limit")
    return value

def _request_host_allowed(handler: BaseHTTPRequestHandler) -> bool:
    """Reject DNS-rebinding Host headers; this service is loopback-only."""
    port = handler.server.server_port
    allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
    hosts = handler.headers.get_all("Host", [])
    return len(hosts) == 1 and hosts[0].strip().lower() in allowed


def _api_rate_allowed(ip: str, path: str) -> bool:
    """Bound local model and retrieval work; this is not authentication."""
    if path in _API_LIMITS:
        bucket = path
        limit = _API_LIMITS[path]
    elif path in {"/api/message", "/api/url"}:
        bucket, limit = "/api/triage", 120
    elif path.startswith("/api/research/"):
        bucket, limit = "/api/research/", 120
    else:
        bucket, limit = "/api/other", 120
    now = time.monotonic()
    key = (ip, bucket)
    with _RATE_LOCK:
        events = _API_EVENTS[key]
        while events and now - events[0] >= 60:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True


def _model_available() -> bool:
    """Only report available when config, tokenizer, and at least one weight exist."""
    if not (MODEL_DIR / "config.json").is_file() or not (MODEL_DIR / "tokenizer.json").is_file():
        return False
    return any(MODEL_DIR.glob("*.safetensors"))


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Keep local request concurrency bounded under accidental request floods."""
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, handler, max_workers: int = 32):
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        self.max_workers = max_workers
        self._worker_slots = threading.BoundedSemaphore(max_workers)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self._worker_slots.acquire(blocking=False):
            try:
                body = b'{"error":"Server is busy"}'
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\n"
                    b"Content-Type: application/json\r\n"
                    b"Connection: close\r\nContent-Length: "
                    + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
                )
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._worker_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._worker_slots.release()

def create_server(host: str = "127.0.0.1", port: int = 8765, max_workers: int = 32):
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    if not loopback or host != "127.0.0.1":
        raise ValueError("The local assistant server must bind to 127.0.0.1 only")
    return BoundedThreadingHTTPServer((host, port), Handler, max_workers=max_workers)

def main():
    address = ("127.0.0.1", 8765)
    print(f"Local Cybersecurity Assistant: http://{address[0]}:{address[1]}")
    create_server(*address).serve_forever()


if __name__ == "__main__":
    main()

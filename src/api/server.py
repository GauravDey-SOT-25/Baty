from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.assistant.service import answer
from src.incident_search.search import search_incidents
from src.message_analysis.analyzer import analyze_message
from src.url_analysis.analyzer import analyze_url

ROOT = Path(__file__).resolve().parents[2]


class Handler(BaseHTTPRequestHandler):
    server_version = "LocalCyberAssistant/0.1"
    def _send(self, code: int, payload, content_type="application/json; charset=utf-8"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if urlparse(self.path).path == "/api/health":
            return self._send(200, {"status": "ok", "mode": "local-only"})
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            return self._send(200, (ROOT / "frontend" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path == "/app.js":
            return self._send(200, (ROOT / "frontend" / "app.js").read_bytes(), "application/javascript; charset=utf-8")
        self._send(404, {"error": "Not found"})
    def do_POST(self):
        if not self.path.startswith("/api/"):
            return self._send(404, {"error": "Not found"})
        try:
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host', '')}":
                return self._send(403, {"error": "Cross-origin requests are not allowed"})
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                return self._send(415, {"error": "Content-Type must be application/json"})
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 32_768:
                return self._send(413, {"error": "Request body must be between 1 and 32768 bytes"})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                return self._send(400, {"error": "JSON request body must be an object"})
            path = urlparse(self.path).path
            if path == "/api/message":
                urls = data.get("urls")
                if urls is not None and (not isinstance(urls, list) or len(urls) > 20 or not all(isinstance(url, str) and len(url) <= 4096 for url in urls)):
                    raise ValueError("urls must be a list of at most 20 strings of 4096 characters or fewer")
                sender = _string(data, "sender", 500)
                context = _string(data, "context", 4000)
                result = analyze_message(_string(data, "text", 20000, required=True), sender, context, urls)
            elif path == "/api/url":
                result = analyze_url(_string(data, "url", 4096, required=True))
            elif path == "/api/assistant":
                result = answer(_string(data, "question", 8000, required=True), _string(data, "lab_context", 2000))
            elif path == "/api/incidents":
                result = search_incidents(_string(data, "description", 8000, required=True))
            else:
                return self._send(404, {"error": "Not found"})
            self._send(200, result)
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

def create_server(host: str = "127.0.0.1", port: int = 8765):
    return ThreadingHTTPServer((host, port), Handler)

def main():
    address = ("127.0.0.1", 8765)
    print(f"Local Cybersecurity Assistant: http://{address[0]}:{address[1]}")
    create_server(*address).serve_forever()


if __name__ == "__main__":
    main()

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
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if urlparse(self.path).path == "/api/health":
            return self._send(200, {"status": "ok", "mode": "local-only"})
        if urlparse(self.path).path in {"/", "/index.html"}:
            return self._send(200, (ROOT / "frontend" / "index.html").read_bytes(), "text/html; charset=utf-8")
        self._send(404, {"error": "Not found"})
    def do_POST(self):
        if not self.path.startswith("/api/"):
            return self._send(404, {"error": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 32_768:
                return self._send(413, {"error": "Request body must be between 1 and 32768 bytes"})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                return self._send(400, {"error": "JSON request body must be an object"})
            path = urlparse(self.path).path
            if path == "/api/message":
                urls = data.get("urls")
                if urls is not None and (not isinstance(urls, list) or not all(isinstance(url, str) for url in urls)):
                    raise ValueError("urls must be a list of strings")
                result = analyze_message(str(data.get("text", "")), data.get("sender"), data.get("context"), urls)
            elif path == "/api/url":
                result = analyze_url(str(data.get("url", "")))
            elif path == "/api/assistant":
                result = answer(str(data.get("question", "")), data.get("lab_context"))
            elif path == "/api/incidents":
                result = search_incidents(str(data.get("description", "")))
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


def main():
    address = ("127.0.0.1", 8765)
    print(f"Local Cybersecurity Assistant: http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, Handler).serve_forever()


if __name__ == "__main__":
    main()

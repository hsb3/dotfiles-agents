"""Local Bookmark Vault — a zero-dependency, self-hosted bookmark manager.

Serves a static single-page frontend (static/) plus a small JSON REST API
backed by a flat bookmarks.json file. No database, no external packages —
stdlib `http.server` only.

Run: `make serve` (or `python3 server.py`), then open http://127.0.0.1:8000/
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from lib import filter_by_tag, next_id, remove_by_id, validate_bookmark

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "bookmarks.json")
STATIC_DIR = os.path.join(HERE, "static")


def _load() -> list[dict]:
    if not os.path.isfile(DATA_FILE):
        return []
    with open(DATA_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def _save(bookmarks: list[dict]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(bookmarks, fh, indent=2)


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str) -> None:
        if path == "/":
            path = "/index.html"
        target = os.path.join(STATIC_DIR, path.lstrip("/"))
        if not os.path.isfile(target):
            self.send_response(404)
            self.end_headers()
            return
        ctype = "text/html"
        if target.endswith(".js"):
            ctype = "application/javascript"
        elif target.endswith(".css"):
            ctype = "text/css"
        with open(target, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/api/bookmarks"):
            tag = None
            if "?" in self.path:
                query = self.path.split("?", 1)[1]
                params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
                tag = params.get("tag")
            self._json(200, filter_by_tag(_load(), tag))
            return
        self._static(self.path)

    def do_POST(self) -> None:
        if self.path != "/api/bookmarks":
            self.send_response(404)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid JSON"})
            return
        error = validate_bookmark(data)
        if error:
            self._json(400, {"error": error})
            return
        bookmarks = _load()
        record = {
            "id": next_id(bookmarks),
            "url": data["url"],
            "title": data["title"],
            "tag": data.get("tag", ""),
        }
        bookmarks.append(record)
        _save(bookmarks)
        self._json(201, record)

    def do_DELETE(self) -> None:
        prefix = "/api/bookmarks/"
        if not self.path.startswith(prefix):
            self.send_response(404)
            self.end_headers()
            return
        try:
            bookmark_id = int(self.path[len(prefix) :])
        except ValueError:
            self._json(400, {"error": "id must be an integer"})
            return
        bookmarks, removed = remove_by_id(_load(), bookmark_id)
        if removed:
            _save(bookmarks)
        self._json(200 if removed else 404, {"removed": removed})

    def log_message(self, fmt, *args):  # quiet during normal operation
        pass


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Local Bookmark Vault serving on http://127.0.0.1:{port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()

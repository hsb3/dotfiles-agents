#!/usr/bin/env python3
"""One-shot sign-off server for the owner-signoff skill.

Serves a sign-off form directory and waits for a single POST /save; writes the
answers as answers.json next to index.html, then shuts down — so a harness
background-task notification tells the session the answers are ready.

Usage: python3 serve_signoff.py <form-dir> [port]
  <form-dir>  directory containing index.html; answers.json is written there
  [port]      preferred port (default 8737); walks forward if taken

First line of output states the actual URL — read it before opening the browser.
"""
import http.server
import json
import pathlib
import sys
import threading

FORM_DIR = pathlib.Path(sys.argv[1]).resolve()
PREFERRED_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8737


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FORM_DIR), **kwargs)

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.send_error(400, "invalid JSON")
            return
        out = FORM_DIR / "answers.json"
        out.write_text(json.dumps(data, indent=2) + "\n")
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(f"answers saved to {out}; shutting down", flush=True)
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


def bind(port_start):
    for port in range(port_start, port_start + 20):
        try:
            return http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler), port
        except OSError:
            continue
    raise SystemExit(f"no free port in {port_start}..{port_start + 19}")


if __name__ == "__main__":
    srv, port = bind(PREFERRED_PORT)
    print(f"serving {FORM_DIR} on http://localhost:{port}/ — waiting for submit", flush=True)
    with srv:
        srv.serve_forever()
    print("server exited cleanly", flush=True)

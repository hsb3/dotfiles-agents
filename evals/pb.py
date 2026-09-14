"""Minimal PocketBase REST client (stdlib-only) shared by schema.py and ingest.py.

Auth resolution order: PB_URL / PB_ADMIN_EMAIL / PB_ADMIN_PASSWORD env vars, then
.claude/operations/extender-db.env (KEY=VALUE lines, untracked). Fails loudly if absent.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ENV_FILE = os.path.join(REPO, ".claude", "operations", "extender-db.env")


def _load_env():
    env = {}
    if os.path.isfile(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    for k in ("PB_URL", "PB_ADMIN_EMAIL", "PB_ADMIN_PASSWORD"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


class PB:
    def __init__(self):
        env = _load_env()
        self.base = env.get("PB_URL", "http://127.0.0.1:8090").rstrip("/")
        email = env.get("PB_ADMIN_EMAIL")
        password = env.get("PB_ADMIN_PASSWORD")
        if not email or not password:
            raise SystemExit(
                f"missing PB_ADMIN_EMAIL/PB_ADMIN_PASSWORD (env vars or {ENV_FILE})"
            )
        resp = self._req(
            "POST",
            "/api/collections/_superusers/auth-with-password",
            {"identity": email, "password": password},
            token=None,
        )
        self.token = resp["token"]

    def _req(self, method, path, body=None, token="use-auth", params=None):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if token == "use-auth":
            req.add_header("Authorization", self.token)
        elif token:
            req.add_header("Authorization", token)
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from None

    # --- collections ---
    def get_collection(self, name):
        try:
            return self._req("GET", f"/api/collections/{name}")
        except RuntimeError as e:
            if "-> 404" in str(e):
                return None
            raise

    def create_collection(self, spec):
        return self._req("POST", "/api/collections", spec)

    def update_collection(self, name, spec):
        return self._req("PATCH", f"/api/collections/{name}", spec)

    # --- records ---
    def find_first(self, coll, flt):
        resp = self._req(
            "GET",
            f"/api/collections/{coll}/records",
            params={"filter": flt, "perPage": 1},
        )
        items = resp.get("items", [])
        return items[0] if items else None

    def list_all(self, coll, flt=None):
        items, page = [], 1
        while True:
            params = {"page": page, "perPage": 200}
            if flt:
                params["filter"] = flt
            resp = self._req("GET", f"/api/collections/{coll}/records", params=params)
            items.extend(resp["items"])
            if page >= resp["totalPages"]:
                return items
            page += 1

    def create(self, coll, body):
        return self._req("POST", f"/api/collections/{coll}/records", body)

    def create_multipart(self, coll, body, files):
        """POST a record whose fields include file uploads (PB file fields cannot be
        set via JSON). `files`: {field_name: (filename, content_bytes, mime)}. The
        `@jsonPayload` part is PocketBase's special key that preserves json/bool/number
        field types (a plain form part would stringify them). Mirrors `_req`'s auth +
        HTTPError->RuntimeError handling; hand-builds the multipart body (stdlib only)."""
        boundary = "pb" + uuid.uuid4().hex
        dash = b"--" + boundary.encode()
        parts = [
            dash,
            b'Content-Disposition: form-data; name="@jsonPayload"',
            b"",
            json.dumps(body).encode(),
        ]
        for field, (filename, content, mime) in files.items():
            parts += [
                dash,
                f'Content-Disposition: form-data; name="{field}"; filename="{filename}"'.encode(),
                f"Content-Type: {mime}".encode(),
                b"",
                content,
            ]
        parts += [dash + b"--", b""]
        data = b"\r\n".join(parts)
        path = f"/api/collections/{coll}/records"
        req = urllib.request.Request(self.base + path, data=data, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Authorization", self.token)
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise RuntimeError(f"POST {path} -> {e.code}: {detail}") from None

    def update(self, coll, rec_id, body):
        return self._req("PATCH", f"/api/collections/{coll}/records/{rec_id}", body)

    def delete(self, coll, rec_id):
        return self._req("DELETE", f"/api/collections/{coll}/records/{rec_id}")

    def upsert(self, coll, flt, body):
        """Update the record matching `flt`, or create it. Returns (record, created?)."""
        existing = self.find_first(coll, flt)
        if existing:
            return self.update(coll, existing["id"], body), False
        return self.create(coll, body), True


def esc(value):
    """Escape a value for a PocketBase filter string literal."""
    return str(value).replace("\\", "\\\\").replace("'", "\\'")

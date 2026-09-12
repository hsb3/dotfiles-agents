"""Hermetic checks for the isolated evals toolbox deployment package."""

import hashlib
import http.server
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_toolbox", ROOT / "evals" / "package_toolbox.py")
package_toolbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package_toolbox)


class PocketBaseFixture:
    """Disposable read-only HTTP fixture; no PocketBase binary or real token required."""

    def __enter__(self):
        fixture = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/api/collections/users/auth-with-password":
                    self.reply({"token": "fixture-token", "record": {"id": "fixture-user"}})
                elif self.path == "/api/files/token":
                    self.reply({"token": "fixture-file-token"})
                else:
                    self.send_error(404)

            def do_GET(self):
                pages = {
                    "/api/collections/runs/records?page=1&perPage=1": {"page": 1, "perPage": 1, "totalPages": 2, "items": [{"id": "run-1"}]},
                    "/api/collections/runs/records?page=2&perPage=1": {"page": 2, "perPage": 1, "totalPages": 2, "items": [{"id": "run-2"}]},
                    "/api/collections/artifacts/records/run-1": {"id": "artifact-1", "blob": "proof.txt"},
                }
                payload = pages.get(self.path)
                if payload is None:
                    self.send_error(404)
                else:
                    self.reply(payload)

            def reply(self, payload):
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"


class ToolboxPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / "source"
        (self.source / ".claude-plugin").mkdir(parents=True)
        (self.source / "docs").mkdir()
        (self.source / "evals" / "deploy").mkdir(parents=True)
        (self.source / "evals" / "ui" / "assets").mkdir(parents=True)
        (self.source / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"plugins": [
            {"name": "alpha-tool", "version": "1.0.0", "description": "Alpha"},
            {"name": "beta", "version": "2.0.0", "description": "Beta"},
        ]}), encoding="utf-8")
        (self.source / "docs" / "workflows.md").write_text(
            "# Workflows\n\n## Choose a workflow\n\n"
            "| Stage | Current marketplace plugin(s) | Choose them when |\n"
            "| --- | --- | --- |\n"
            "| Build | [alpha-tool](../plugins/alpha-tool/README.md), [beta](../plugins/beta/README.md) | Make things |\n",
            encoding="utf-8",
        )
        for name in ("Dockerfile", "start.sh", "railway.toml"):
            (self.source / "evals" / "deploy" / name).write_text(name + "\n", encoding="utf-8")
        (self.source / "evals" / "ui" / "index.html").write_text("<main>safe</main>\n", encoding="utf-8")
        (self.source / "evals" / "ui" / "assets" / "app.js").write_text("console.log('safe')\n", encoding="utf-8")
        (self.source / "evals" / "pb_data").mkdir()
        (self.source / "evals" / "pb_data" / "secret.db").write_text("secret", encoding="utf-8")
        (self.source / ".env").write_text("PB_SUPERUSER_PASSWORD=secret", encoding="utf-8")
        (self.source / "evals" / "private.json").write_text('{"token": "secret"}', encoding="utf-8")

    def test_build_is_allowlisted_deterministic_and_snapshot_labeled(self):
        first, second = Path(self.tmp.name) / "first", Path(self.tmp.name) / "second"
        package_toolbox.build_package(self.source, first)
        package_toolbox.build_package(self.source, second)
        self.assertEqual(
            sorted(path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()),
            sorted(["Dockerfile", "railway.toml", "start.sh", "pb_public/assets/app.js", "pb_public/index.html", "pb_public/toolbox-catalog.json"]),
        )
        self.assertEqual(
            {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()},
            {p.relative_to(second).as_posix(): p.read_bytes() for p in second.rglob("*") if p.is_file()},
        )
        catalog = json.loads((first / "pb_public" / "toolbox-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in catalog["plugins"]], ["alpha-tool", "beta"])
        self.assertEqual(catalog["source_snapshot"], hashlib.sha256(
            (self.source / ".claude-plugin" / "marketplace.json").read_bytes() + b"\0" +
            (self.source / "docs" / "workflows.md").read_bytes()).hexdigest())
        self.assertNotIn("secret", "".join(p.name for p in first.rglob("*")))
        self.assertNotIn(b"secret", b"".join(p.read_bytes() for p in first.rglob("*") if p.is_file()))

    def test_refuses_existing_output_and_bad_workflow_references(self):
        output = Path(self.tmp.name) / "output"
        output.mkdir()
        (output / "present").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(FileExistsError, "output"):
            package_toolbox.build_package(self.source, output)
        (self.source / "docs" / "workflows.md").write_text(
            "## Choose a workflow\n| Stage | Current marketplace plugin(s) | Choose them when |\n| --- | --- | --- |\n| Build | [missing](../plugins/missing/README.md) | x |\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            package_toolbox.build_package(self.source, Path(self.tmp.name) / "bad")

    def test_rejects_missing_ui_and_fixture_is_paginated_and_token_free(self):
        (self.source / "evals" / "ui" / "index.html").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "UI"):
            package_toolbox.build_package(self.source, Path(self.tmp.name) / "missing-ui")
        with PocketBaseFixture() as fixture:
            from urllib.request import urlopen
            self.assertEqual(json.load(urlopen(fixture.url + "/api/collections/runs/records?page=2&perPage=1"))["items"][0]["id"], "run-2")
            self.assertEqual(json.load(urlopen(fixture.url + "/api/files/token", data=b"{}"))["token"], "fixture-file-token")

    def test_rejects_ui_secret_files_and_symlink_escapes(self):
        (self.source / "evals" / "ui" / ".env").write_text("token=secret", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "static asset"):
            package_toolbox.build_package(self.source, Path(self.tmp.name) / "env-output")
        (self.source / "evals" / "ui" / ".env").unlink()
        escaped = self.source / "evals" / "ui" / "assets" / "escaped.js"
        escaped.symlink_to(self.source / ".env")
        with self.assertRaisesRegex(ValueError, "static asset"):
            package_toolbox.build_package(self.source, Path(self.tmp.name) / "symlink-output")


if __name__ == "__main__":
    unittest.main()

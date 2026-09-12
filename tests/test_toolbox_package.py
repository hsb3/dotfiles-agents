"""Hermetic checks for the isolated evals toolbox deployment package."""

import hashlib
import http.server
import importlib.util
import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_toolbox", ROOT / "evals" / "package_toolbox.py")
package_toolbox = importlib.util.module_from_spec(SPEC)
sys.modules["package_toolbox"] = package_toolbox
SPEC.loader.exec_module(package_toolbox)
FIXTURE_SPEC = importlib.util.spec_from_file_location("toolbox_fixture", ROOT / "evals" / "toolbox_fixture.py")
toolbox_fixture = importlib.util.module_from_spec(FIXTURE_SPEC)
FIXTURE_SPEC.loader.exec_module(toolbox_fixture)


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
        (self.source / "evals" / "deploy" / "pb_hooks").mkdir()
        (self.source / "evals" / "ui").mkdir(parents=True)
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
        (self.source / "evals" / "deploy" / "pb_hooks" / "toolbox_catalog.pb.js").write_text("hook\n", encoding="utf-8")
        (self.source / "evals" / "ui" / "index.html").write_text("<main>safe</main>\n", encoding="utf-8")
        (self.source / "evals" / "ui" / "styles.css").write_text("main {}\n", encoding="utf-8")
        (self.source / "evals" / "ui" / "app.js").write_text("console.log('safe')\n", encoding="utf-8")
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
            sorted(["Dockerfile", "railway.toml", "start.sh", "pb_catalog/toolbox-catalog.json", "pb_hooks/toolbox_catalog.pb.js", "pb_public/app.js", "pb_public/index.html", "pb_public/styles.css"]),
        )
        self.assertEqual(
            {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()},
            {p.relative_to(second).as_posix(): p.read_bytes() for p in second.rglob("*") if p.is_file()},
        )
        self.assertFalse((first / "pb_public" / "toolbox-catalog.json").exists())
        catalog = json.loads((first / "pb_catalog" / "toolbox-catalog.json").read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in catalog["plugins"]], ["alpha-tool", "beta"])
        self.assertEqual(catalog["workflows"], [{
            "guidance": "Make things", "id": "build", "name": "Build", "plugins": ["alpha-tool", "beta"],
        }])
        self.assertEqual([item["workflows"] for item in catalog["plugins"]], [["build"], ["build"]])
        self.assertEqual(catalog["source_snapshot"], hashlib.sha256(
            (self.source / ".claude-plugin" / "marketplace.json").read_bytes() + b"\0" +
            (self.source / "docs" / "workflows.md").read_bytes()).hexdigest())
        self.assertNotIn("secret", "".join(p.name for p in first.rglob("*")))
        self.assertNotIn(b"secret", b"".join(p.read_bytes() for p in first.rglob("*") if p.is_file()))

    def test_catalog_hook_requires_auth_and_reads_the_private_snapshot(self):
        hook = (ROOT / "evals" / "deploy" / "pb_hooks" / "toolbox_catalog.pb.js").read_text(encoding="utf-8")
        start = (ROOT / "evals" / "deploy" / "start.sh").read_text(encoding="utf-8")
        self.assertIn('"/api/toolbox/catalog"', hook)
        self.assertIn("$apis.requireAuth()", hook)
        self.assertIn("/pb/pb_catalog/toolbox-catalog.json", hook)
        self.assertNotIn("pb_public", hook)
        self.assertIn('--hooksDir="$package_dir/pb_hooks"', start)
        self.assertIn('--publicDir="$package_dir/pb_public"', start)

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
        output = Path(self.tmp.name) / "missing-ui"
        with self.assertRaisesRegex(FileNotFoundError, "UI"):
            package_toolbox.build_package(self.source, output)
        self.assertFalse(output.exists())
        with PocketBaseFixture() as fixture:
            from urllib.request import urlopen
            self.assertEqual(json.load(urlopen(fixture.url + "/api/collections/runs/records?page=2&perPage=1"))["items"][0]["id"], "run-2")
            self.assertEqual(json.load(urlopen(fixture.url + "/api/files/token", data=b"{}"))["token"], "fixture-file-token")

    def test_ignores_extra_files_and_rejects_symlinked_required_sources(self):
        (self.source / "evals" / "ui" / "private.json").write_text('{"token": "secret"}', encoding="utf-8")
        (self.source / "evals" / "ui" / "debug.map").write_text("secret", encoding="utf-8")
        clean_output = Path(self.tmp.name) / "clean-output"
        package_toolbox.build_package(self.source, clean_output)
        self.assertNotIn(b"secret", b"".join(p.read_bytes() for p in clean_output.rglob("*") if p.is_file()))
        (self.source / "evals" / "ui" / "app.js").unlink()
        (self.source / "evals" / "ui" / "app.js").symlink_to(self.source / ".env")
        symlink_output = Path(self.tmp.name) / "symlink-output"
        with self.assertRaisesRegex(FileNotFoundError, "unsafe"):
            package_toolbox.build_package(self.source, symlink_output)
        self.assertFalse(symlink_output.exists())
        source_link = Path(self.tmp.name) / "source-link"
        source_link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "ancestor"):
            package_toolbox.build_package(source_link, Path(self.tmp.name) / "ancestor-output")

    def test_current_catalog_keeps_hyphenated_marketplace_ids(self):
        catalog = json.loads(package_toolbox.build_catalog(ROOT))
        ids = {item["id"] for item in catalog["plugins"]}
        self.assertTrue({"board-desk", "plugin-feedback", "solo-skills"} <= ids)
        self.assertTrue(all({"id", "name", "guidance", "plugins"} <= set(workflow)
                            for workflow in catalog["workflows"]))
        workflow_ids = {item["id"] for item in catalog["workflows"]}
        self.assertTrue(workflow_ids)
        self.assertTrue(all({"id", "workflows"} <= set(plugin) for plugin in catalog["plugins"]))
        self.assertTrue(all(isinstance(workflow_id, str) and workflow_id in workflow_ids
                            for plugin in catalog["plugins"] for workflow_id in plugin["workflows"]))
        self.assertTrue(all(plugin["id"] in workflow["plugins"]
                            for plugin in catalog["plugins"] for workflow_id in plugin["workflows"]
                            for workflow in catalog["workflows"] if workflow["id"] == workflow_id))

    @unittest.skipUnless(shutil.which("pocketbase") and (ROOT / "evals" / "ui" / "index.html").is_file(),
                         "requires PocketBase and the integrated UI sources")
    def test_actual_loopback_fixture_serves_authenticated_private_data(self):
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        with toolbox_fixture.ToolboxFixture(ROOT, shutil.which("pocketbase")) as fixture:
            with self.assertRaises(HTTPError) as denied:
                urlopen(fixture.url + "/api/toolbox/catalog")
            self.assertEqual(denied.exception.code, 401)
            catalog_request = Request(fixture.url + "/api/toolbox/catalog")
            catalog_request.add_header("Authorization", fixture.user_token)
            self.assertIn("source_snapshot", json.load(urlopen(catalog_request)))
            runs_request = Request(fixture.url + "/api/collections/runs/records?page=1&perPage=1")
            runs_request.add_header("Authorization", fixture.user_token)
            self.assertEqual(len(json.load(urlopen(runs_request))["items"]), 1)
            with self.assertRaises(HTTPError) as anonymous:
                urlopen(fixture.url + "/api/collections/runs/records?page=1&perPage=1")
            self.assertEqual(anonymous.exception.code, 403)
            token_request = Request(fixture.url + "/api/files/token", data=b"{}", method="POST")
            token_request.add_header("Content-Type", "application/json")
            token_request.add_header("Authorization", fixture.user_token)
            file_token = json.load(urlopen(token_request))["token"]
            blob = fixture.artifact["blob"]
            self.assertEqual(urlopen(fixture.url + f"/api/files/artifacts/{fixture.artifact['id']}/{blob}?token={file_token}").read(), fixture.artifact_bytes)
            self.assertEqual(sorted(p.relative_to(fixture.package).as_posix() for p in fixture.package.rglob("*") if p.is_file()), sorted([
                "Dockerfile", "railway.toml", "start.sh", "pb_catalog/toolbox-catalog.json",
                "pb_hooks/toolbox_catalog.pb.js", "pb_public/app.js", "pb_public/index.html", "pb_public/styles.css",
            ]))


if __name__ == "__main__":
    unittest.main()

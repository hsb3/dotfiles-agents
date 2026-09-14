"""Hermetic checks for the isolated evals toolbox deployment package."""

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
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
        self.ui_build = self.source / "evals" / "ui" / "dist"
        (self.ui_build / "assets" / "nested").mkdir(parents=True)
        (self.ui_build / "index.html").write_text('<script src="/assets/toolbox.js"></script>\n', encoding="utf-8")
        (self.ui_build / "assets" / "toolbox.js").write_text("console.log('built')\n", encoding="utf-8")
        (self.ui_build / "assets" / "nested" / "toolbox.css").write_text("main {}\n", encoding="utf-8")
        (self.source / "evals" / "pb_data").mkdir()
        (self.source / "evals" / "pb_data" / "secret.db").write_text("secret", encoding="utf-8")
        (self.source / ".env").write_text("PB_SUPERUSER_PASSWORD=secret", encoding="utf-8")
        (self.source / "evals" / "private.json").write_text('{"token": "secret"}', encoding="utf-8")

    def test_build_is_allowlisted_deterministic_and_snapshot_labeled(self):
        first, second = Path(self.tmp.name) / "first", Path(self.tmp.name) / "second"
        package_toolbox.build_package(self.source, first, self.ui_build)
        package_toolbox.build_package(self.source, second, self.ui_build)
        self.assertEqual(
            sorted(path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()),
            sorted(["Dockerfile", "railway.toml", "start.sh", "pb_hooks/toolbox-catalog.json", "pb_hooks/toolbox-package.json", "pb_hooks/toolbox_catalog.pb.js", "pb_public/assets/nested/toolbox.css", "pb_public/assets/toolbox.js", "pb_public/index.html"]),
        )
        self.assertEqual(
            {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob("*") if p.is_file()},
            {p.relative_to(second).as_posix(): p.read_bytes() for p in second.rglob("*") if p.is_file()},
        )
        self.assertFalse((first / "pb_public" / "toolbox-catalog.json").exists())
        catalog = json.loads((first / "pb_hooks" / "toolbox-catalog.json").read_text(encoding="utf-8"))
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
        receipt = json.loads((first / "pb_hooks" / "toolbox-package.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["ui_build"], "evals/ui/dist")
        self.assertEqual(receipt["ui_files"], ["assets/nested/toolbox.css", "assets/toolbox.js", "index.html"])
        self.assertEqual(receipt["ui_source_files"], ["app.js", "index.html", "styles.css"])
        self.assertEqual(receipt["ui_source_snapshot"], hashlib.sha256(
            b"app.js\0console.log('safe')\n\0index.html\0<main>safe</main>\n\0styles.css\0main {}\n\0"
        ).hexdigest())
        self.assertEqual(receipt["ui_snapshot"], hashlib.sha256(
            b"assets/nested/toolbox.css\0main {}\n\0assets/toolbox.js\0console.log('built')\n\0index.html\0<script src=\"/assets/toolbox.js\"></script>\n\0"
        ).hexdigest())

    def test_catalog_hook_requires_auth_and_reads_the_private_snapshot(self):
        hook = (ROOT / "evals" / "deploy" / "pb_hooks" / "toolbox_catalog.pb.js").read_text(encoding="utf-8")
        start = (ROOT / "evals" / "deploy" / "start.sh").read_text(encoding="utf-8")
        self.assertIn('"/api/toolbox/catalog"', hook)
        self.assertIn("$apis.requireAuth()", hook)
        self.assertIn("${__hooks}/toolbox-catalog.json", hook)
        self.assertIn("String.fromCharCode.apply", hook)
        self.assertNotIn("pb_public", hook)
        self.assertIn('--hooksDir="$package_dir/pb_hooks"', start)
        self.assertIn('--publicDir="$package_dir/pb_public"', start)

    def test_refuses_existing_output_and_bad_workflow_references(self):
        output = Path(self.tmp.name) / "output"
        output.mkdir()
        (output / "present").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(FileExistsError, "output"):
            package_toolbox.build_package(self.source, output, self.ui_build)
        (self.source / "docs" / "workflows.md").write_text(
            "## Choose a workflow\n| Stage | Current marketplace plugin(s) | Choose them when |\n| --- | --- | --- |\n| Build | [missing](../plugins/missing/README.md) | x |\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "missing"):
            package_toolbox.build_package(self.source, Path(self.tmp.name) / "bad", self.ui_build)

    def test_refuses_output_inside_the_source_tree(self):
        output = self.source / "generated-package"
        with self.assertRaisesRegex(ValueError, "output"):
            package_toolbox.build_package(self.source, output, self.ui_build)
        self.assertFalse(output.exists())

    def test_requires_explicit_usable_ui_build(self):
        output = Path(self.tmp.name) / "missing-ui"
        with self.assertRaisesRegex(ValueError, "ui build"):
            package_toolbox.build_package(self.source, output)
        self.assertFalse(output.exists())
        (self.ui_build / "assets" / "toolbox.js").unlink()
        (self.ui_build / "assets" / "nested" / "toolbox.css").unlink()
        with self.assertRaisesRegex(ValueError, "assets"):
            package_toolbox.build_package(self.source, output, self.ui_build)
        self.assertFalse(output.exists())

    def test_ignores_extra_files_and_rejects_symlinked_required_sources(self):
        (self.source / "evals" / "ui" / "private.json").write_text('{"token": "secret"}', encoding="utf-8")
        (self.source / "evals" / "ui" / "debug.map").write_text("secret", encoding="utf-8")
        clean_output = Path(self.tmp.name) / "clean-output"
        package_toolbox.build_package(self.source, clean_output, self.ui_build)
        self.assertNotIn(b"secret", b"".join(p.read_bytes() for p in clean_output.rglob("*") if p.is_file()))
        start = self.source / "evals" / "deploy" / "start.sh"
        start.unlink()
        start.symlink_to(self.source / ".env")
        deploy_output = Path(self.tmp.name) / "deploy-symlink-output"
        with self.assertRaisesRegex(ValueError, "symlink"):
            package_toolbox.build_package(self.source, deploy_output, self.ui_build)
        self.assertFalse(deploy_output.exists())
        start.unlink()
        start.write_text("start.sh\n", encoding="utf-8")
        (self.ui_build / "assets" / "toolbox.js").unlink()
        (self.ui_build / "assets" / "toolbox.js").symlink_to(self.source / ".env")
        symlink_output = Path(self.tmp.name) / "symlink-output"
        with self.assertRaisesRegex(ValueError, "symlink"):
            package_toolbox.build_package(self.source, symlink_output, self.ui_build)
        self.assertFalse(symlink_output.exists())
        source_link = Path(self.tmp.name) / "source-link"
        source_link.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "ancestor"):
            package_toolbox.build_package(source_link, Path(self.tmp.name) / "ancestor-output", self.ui_build)

    def test_rejects_unsafe_vite_output_and_outside_build_tree(self):
        output = Path(self.tmp.name) / "unsafe-output"
        for unsafe in ("assets/toolbox.js.map", "assets/.env", "assets/private.json", "src/private.js", "node_modules/package.js"):
            path = self.ui_build / unsafe
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("secret", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                package_toolbox.build_package(self.source, output, self.ui_build)
            self.assertFalse(output.exists())
            path.unlink()
        external = Path(self.tmp.name) / "external-dist"
        shutil.copytree(self.ui_build, external)
        with self.assertRaisesRegex(ValueError, "source root"):
            package_toolbox.build_package(self.source, output, external)

    def test_current_catalog_keeps_hyphenated_marketplace_ids(self):
        catalog = json.loads(package_toolbox.build_catalog(ROOT))
        ids = {item["id"] for item in catalog["plugins"]}
        self.assertTrue({"board-desk", "plugin-feedback", "solo-skills"} <= ids)
        self.assertTrue(all({"id", "name", "guidance", "plugins"} <= set(workflow)
                            for workflow in catalog["workflows"]))
        workflow_ids = {item["id"] for item in catalog["workflows"]}
        self.assertTrue(workflow_ids)
        self.assertTrue(all({"id", "name", "workflows"} <= set(plugin) for plugin in catalog["plugins"]))
        self.assertTrue(all(plugin["id"] == plugin["name"] for plugin in catalog["plugins"]))
        self.assertTrue(all(isinstance(workflow_id, str) and workflow_id in workflow_ids
                            for plugin in catalog["plugins"] for workflow_id in plugin["workflows"]))
        self.assertTrue(all(plugin["id"] in workflow["plugins"]
                            for plugin in catalog["plugins"] for workflow_id in plugin["workflows"]
                            for workflow in catalog["workflows"] if workflow["id"] == workflow_id))

    @unittest.skipUnless(shutil.which("pocketbase"), "requires PocketBase")
    def test_actual_loopback_fixture_serves_authenticated_private_data(self):
        from urllib.error import HTTPError
        from urllib.request import Request, urlopen
        shutil.copytree(ROOT / "evals" / "deploy", self.source / "evals" / "deploy", dirs_exist_ok=True)
        with toolbox_fixture.ToolboxFixture(self.source, shutil.which("pocketbase")) as fixture:
            with self.assertRaises(HTTPError) as denied:
                urlopen(fixture.url + "/api/toolbox/catalog")
            self.assertEqual(denied.exception.code, 401)
            denied.exception.close()
            catalog_request = Request(fixture.url + "/api/toolbox/catalog")
            catalog_request.add_header("Authorization", fixture.user_token)
            try:
                catalog = json.load(urlopen(catalog_request))
            except HTTPError as error:
                self.fail(f"authenticated catalog failed: {error.code} {error.read().decode()}")
            self.assertIn("source_snapshot", catalog)
            runs_request = Request(fixture.url + "/api/collections/runs/records?page=1&perPage=1")
            runs_request.add_header("Authorization", fixture.user_token)
            page = json.load(urlopen(runs_request))
            self.assertEqual(len(page["items"]), 1)
            self.assertEqual(page["totalItems"], 27)
            self.assertEqual(page["totalPages"], 27)
            self.assertTrue({"model", "cost_usd", "duration_ms", "passed"} <= set(page["items"][0]))
            anonymous_runs = json.load(urlopen(fixture.url + "/api/collections/runs/records?page=1&perPage=1"))
            self.assertEqual(anonymous_runs["totalItems"], 0)
            token_request = Request(fixture.url + "/api/files/token", data=b"{}", method="POST")
            token_request.add_header("Content-Type", "application/json")
            token_request.add_header("Authorization", fixture.user_token)
            file_token = json.load(urlopen(token_request))["token"]
            blob = fixture.artifact["blob"]
            self.assertEqual(urlopen(fixture.url + f"/api/files/artifacts/{fixture.artifact['id']}/{blob}?token={file_token}").read(), fixture.artifact_bytes)
            self.assertEqual(sorted(p.relative_to(fixture.package).as_posix() for p in fixture.package.rglob("*") if p.is_file()), sorted([
                "Dockerfile", "railway.toml", "start.sh", "pb_hooks/toolbox-catalog.json",
                "pb_hooks/toolbox-package.json", "pb_hooks/toolbox_catalog.pb.js", "pb_public/assets/nested/toolbox.css", "pb_public/assets/toolbox.js", "pb_public/index.html",
            ]))


if __name__ == "__main__":
    unittest.main()

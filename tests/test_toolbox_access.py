import os
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

EVALS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evals")
if EVALS not in sys.path:
    sys.path.insert(0, EVALS)

import toolbox_access
import toolbox_fixture


ROOT = Path(__file__).resolve().parents[1]


class FakePB:
    def __init__(self, collections):
        self.collections = collections
        self.updates = []

    def get_collection(self, name):
        return self.collections[name]

    def update_collection(self, name, patch):
        self.updates.append((name, patch))


class FixturePB:
    def __init__(self, fixture):
        self.fixture = fixture

    def request(self, method, path, body=None, token=None):
        request = Request(self.fixture.url + path, method=method)
        if body is not None:
            request.data = json.dumps(body).encode()
            request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", token or self.fixture.admin_token)
        return json.load(urlopen(request))

    def get_collection(self, name):
        return self.request("GET", "/api/collections/" + name)

    def update_collection(self, name, patch):
        return self.request("PATCH", "/api/collections/" + name, patch)


def api(url, path, token=None, method="GET", body=None):
    request = Request(url + path, method=method)
    if body is not None:
        request.data = json.dumps(body).encode()
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", token)
    return json.load(urlopen(request))


def locked(**extra):
    return {"listRule": None, "viewRule": None, "createRule": None,
            "updateRule": None, "deleteRule": None, "fields": ["unchanged"], **extra}


class ToolboxAccessTests(unittest.TestCase):
    def collections(self):
        return {name: locked() for name in toolbox_access.COLLECTIONS}

    def test_dry_run_and_apply_are_allowlisted_idempotent_and_preserve_other_rules(self):
        """Fails if a non-allowlisted collection is patched or a write rule is included."""
        collections = self.collections()
        collections["frameworks"]["viewRule"] = toolbox_access.AUTH_RULE
        collections["users"] = locked(listRule="id = @request.auth.id")
        pb = FakePB(collections)

        changed, noop = toolbox_access.set_authenticated_read(pb)
        self.assertEqual(changed, toolbox_access.COLLECTIONS)
        self.assertEqual(noop, ())
        self.assertEqual(pb.updates, [])

        changed, noop = toolbox_access.set_authenticated_read(pb, apply=True)
        self.assertEqual(changed, toolbox_access.COLLECTIONS)
        self.assertEqual(noop, ())
        self.assertEqual(len(pb.updates), len(changed))
        self.assertNotIn("users", [name for name, _ in pb.updates])
        framework_patch = next(patch for name, patch in pb.updates if name == "frameworks")
        self.assertEqual(framework_patch, {"listRule": toolbox_access.AUTH_RULE})
        for _name, patch in pb.updates:
            self.assertTrue(set(patch) <= {"listRule", "viewRule"})

        for name, patch in pb.updates:
            collections[name].update(patch)
        pb.updates.clear()
        self.assertEqual(toolbox_access.set_authenticated_read(pb, apply=True), ((), toolbox_access.COLLECTIONS))
        self.assertEqual(pb.updates, [])

    def test_unexpected_rule_fails_preflight_before_any_write(self):
        """Fails if validation moves inside the write loop and leaves a partial mutation."""
        collections = self.collections()
        collections["tool_calls"]["viewRule"] = "owner = @request.auth.id"
        pb = FakePB(collections)

        with self.assertRaisesRegex(ValueError, "tool_calls.viewRule"):
            toolbox_access.set_authenticated_read(pb, apply=True)
        self.assertEqual(pb.updates, [])

    def seed_readable_records(self, fixture):
        def create(name, body):
            return api(fixture.url, f"/api/collections/{name}/records", fixture.admin_token, "POST", body)

        records = {"artifacts": fixture.artifact, "runs": {"id": fixture.artifact["run"]}}
        records["frameworks"] = create("frameworks", {"slug": "fixture-framework", "name": "Fixture", "kind": "principles"})
        records["sources"] = create("sources", {"slug": "fixture-source", "name": "Fixture"})
        records["extenders"] = create("extenders", {"slug": "fixture-extender", "kind": "skill"})
        records["framework_elements"] = create("framework_elements", {
            "framework": records["frameworks"]["id"], "slug": "fixture-job", "name": "Fixture", "element_kind": "job",
        })
        records["files"] = create("files", {"extender": records["extenders"]["id"], "relpath": "fixture.md"})
        records["distributions"] = create("distributions", {"slug": "fixture-distribution", "kind": "plugin"})
        records["eval_runs"] = create("eval_runs", {"slug": "fixture-eval", "kind": "mechanical"})
        records["eval_responses"] = create("eval_responses", {"run": records["eval_runs"]["id"], "role": "fixture"})
        records["assessments"] = create("assessments", {
            "extender": records["extenders"]["id"], "framework": records["frameworks"]["id"], "verdict": "present",
        })
        records["job_coverage"] = create("job_coverage", {"job": records["framework_elements"]["id"]})
        records["run_events"] = create("run_events", {"run": records["runs"]["id"], "seq": 1})
        records["tool_calls"] = create("tool_calls", {
            "run": records["runs"]["id"], "tool_call_id": "fixture-call", "tool_name": "fixture",
        })
        return records

    def fixture_source(self, source):
        for relative in (".claude-plugin/marketplace.json", "docs/workflows.md"):
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        shutil.copytree(ROOT / "evals" / "deploy", source / "evals" / "deploy")
        legacy_ui = source / "evals" / "ui"
        legacy_ui.mkdir(parents=True)
        (legacy_ui / "index.html").write_text("<!doctype html>", encoding="utf-8")
        (legacy_ui / "styles.css").write_text("", encoding="utf-8")
        (legacy_ui / "app.js").write_text("", encoding="utf-8")
        dist = legacy_ui / "dist"
        assets = dist / "assets"
        assets.mkdir(parents=True)
        (dist / "index.html").write_text(
            '<!doctype html><link rel="stylesheet" href="/assets/styles.css">'
            '<script type="module" src="/assets/app.js"></script>', encoding="utf-8")
        (assets / "styles.css").write_text("", encoding="utf-8")
        (assets / "app.js").write_text("", encoding="utf-8")

    @unittest.skipUnless(shutil.which("pocketbase"), "requires PocketBase")
    def test_real_fixture_keeps_writes_and_users_private(self):
        """Fails if access becomes anonymous, writable, or broadens the users collection."""
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            self.fixture_source(source)
            with toolbox_fixture.ToolboxFixture(source, shutil.which("pocketbase")) as fixture:
                second_email = "fixture-second@example.test"
                second_password = "FixtureSecondPassword123"
                api(fixture.url, "/api/collections/users/records", fixture.admin_token, "POST", {
                    "email": second_email, "password": second_password,
                    "passwordConfirm": second_password, "verified": True,
                })
                second_token = api(fixture.url, "/api/collections/users/auth-with-password", None, "POST", {
                    "identity": second_email, "password": second_password,
                })["token"]
                records = self.seed_readable_records(fixture)
                changed, noop = toolbox_access.set_authenticated_read(FixturePB(fixture), apply=True)
                self.assertEqual(set(changed) | set(noop), set(toolbox_access.COLLECTIONS))

                for name in toolbox_access.COLLECTIONS:
                    record_path = f"/api/collections/{name}/records/{records[name]['id']}"
                    self.assertGreaterEqual(api(fixture.url, f"/api/collections/{name}/records", fixture.user_token)["totalItems"], 1)
                    self.assertGreaterEqual(api(fixture.url, f"/api/collections/{name}/records", second_token)["totalItems"], 1)
                    self.assertEqual(api(fixture.url, f"/api/collections/{name}/records")["totalItems"], 0)
                    self.assertEqual(api(fixture.url, record_path, fixture.user_token)["id"], records[name]["id"])
                    for token, method, path, body, status in (
                        (None, "GET", record_path, None, 404),
                        (fixture.user_token, "POST", f"/api/collections/{name}/records", {}, 403),
                        (fixture.user_token, "PATCH", record_path, {}, 403),
                        (fixture.user_token, "DELETE", record_path, None, 403),
                    ):
                        with self.assertRaises(HTTPError) as denied:
                            api(fixture.url, path, token, method, body)
                        self.assertEqual(denied.exception.code, status)
                        denied.exception.close()

                users = api(fixture.url, "/api/collections/users/records", fixture.user_token)
                self.assertEqual(users["totalItems"], 1)
                with self.assertRaises(HTTPError) as denied_other_user:
                    api(fixture.url, f"/api/collections/users/records/{users['items'][0]['id']}", second_token)
                self.assertEqual(denied_other_user.exception.code, 404)
                denied_other_user.exception.close()
                file_token = api(fixture.url, "/api/files/token", fixture.user_token, "POST")["token"]
                blob = fixture.artifact["blob"]
                self.assertEqual(urlopen(fixture.url + f"/api/files/artifacts/{fixture.artifact['id']}/{blob}?token={file_token}").read(), fixture.artifact_bytes)


if __name__ == "__main__":
    unittest.main()

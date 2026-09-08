"""board-triage's split into a backend-agnostic core plus per-backend adapters.

Two invariants: the split itself. If the rubric page starts naming a backend again, or an
adapter stops declaring where the rubric's outputs land, the skill has quietly re-fused and
adding a third backend means editing the procedure again. Both failures are silent — an
agent reading a GitHub-flavoured procedure against another board just produces a wrong
changeset.

Adapter logic is pinned per adapter in its own file (test_kata_board.py,
test_github_projects_board.py); the one exception kept here is
GithubProjectsFailIsOnStderr, which pins where a refusal is printed.
"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "board-triage")
ADAPTERS = os.path.join(SKILL, "references", "adapters")

# Loaded by path (not sys.path import) so this file's fixture module name can't collide
# with test_github_projects_board.py's own load of the same script.
_gpb_spec = importlib.util.spec_from_file_location(
    "github_projects_board_stderr_pin", os.path.join(SKILL, "scripts", "github_projects_board.py")
)
gpb = importlib.util.module_from_spec(_gpb_spec)
_gpb_spec.loader.exec_module(gpb)

# Naming any of these on the rubric page means the judgment has been re-coupled to one
# board. Lowercased substring match, so "gh " catches the CLI without catching "high".
BACKEND_TOKENS = (
    "github",
    "graphql",
    "projects (v2)",
    "project (v2)",
    "kaneo",
    "gh ",
    "jira",
    "linear",
)

# Every adapter answers the same four questions, or the core cannot rely on it.
REQUIRED_ADAPTER_SECTIONS = ("## Key", "## Export", "## Apply", "## Field map")


def read(path):
    with open(path) as handle:
        return handle.read()


class BackendAgnosticCore(unittest.TestCase):
    """AC #1/#3: the rubric and procedure name no backend, so a new one costs an adapter."""

    def test_skill_body_names_no_backend(self):
        # Frontmatter is exempt: the description is the trigger surface, and someone
        # asking to triage a named board should still reach this skill.
        raw = read(os.path.join(SKILL, "SKILL.md"))
        body = raw.split("\n---\n", 1)[1] if raw.startswith("---\n") else raw
        offset = len(raw[: len(raw) - len(body)].splitlines())

        offenders = []
        for lineno, line in enumerate(body.splitlines(), offset + 1):
            if "references/adapters/" in line:
                continue  # the adapter index is the one place a backend may be named
            low = line.lower()
            for token in BACKEND_TOKENS:
                if token in low:
                    offenders.append(f"SKILL.md:{lineno}: {token!r} in {line.strip()!r}")
        self.assertEqual([], offenders, "backend leaked into the backend-agnostic core")

    def test_core_documents_the_adapter_contract(self):
        body = read(os.path.join(SKILL, "SKILL.md"))
        for required in ("**Snapshot**", "**Changeset**", "**Apply**", "**Field map**"):
            self.assertIn(required, body, "adapter contract is missing a required artifact")

    def test_no_dangling_board_analyst_agent(self):
        """AC #4: the hand-off variant used to route through an agent that never existed."""
        for dirpath, _, filenames in os.walk(SKILL):
            for name in filenames:
                if name.endswith(".md"):
                    path = os.path.join(dirpath, name)
                    self.assertNotIn("board-analyst", read(path), f"{path} names a nonexistent agent")


class Adapters(unittest.TestCase):
    """AC #2: two adapters, each answering the contract's questions."""

    def test_at_least_two_adapters_exist(self):
        found = sorted(n for n in os.listdir(ADAPTERS) if n.endswith(".md"))
        self.assertGreaterEqual(len(found), 2, f"expected two or more adapters, found {found}")

    def test_each_adapter_declares_the_contract(self):
        for name in sorted(os.listdir(ADAPTERS)):
            if not name.endswith(".md"):
                continue
            body = read(os.path.join(ADAPTERS, name))
            with self.subTest(adapter=name):
                for section in REQUIRED_ADAPTER_SECTIONS:
                    self.assertIn(section, body, f"{name} is missing {section}")

    def test_core_links_every_adapter(self):
        body = read(os.path.join(SKILL, "SKILL.md"))
        for name in sorted(os.listdir(ADAPTERS)):
            if name.endswith(".md"):
                self.assertIn(f"references/adapters/{name}", body, f"{name} is unreachable")


class GithubProjectsFailIsOnStderr(unittest.TestCase):
    """SKIP already moved to stderr for this adapter (see the fix on 5c9f095); FAIL must
    match, so `apply || abort` means one thing on every adapter."""

    @staticmethod
    def _stub_gh(cmd, capture_output=False, text=False, env=None):
        query = next((a for a in cmd if a.startswith("query=")), "")
        if "projectV2(number:$n)" in query:
            payload = {"data": {"user": {"projectV2": {"id": "PVT_1", "title": "t"}}}}
        elif "fields(first:50" in query:
            payload = {
                "data": {"node": {"fields": {"nodes": [
                    {"id": "F_status", "name": "Status", "dataType": "SINGLE_SELECT",
                     "options": [{"id": "opt_todo", "name": "Todo"}]},
                ]}}}
            }
        elif "items(first:100" in query:
            payload = {
                "data": {"node": {"items": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{
                        "id": "PVTI_1",
                        "content": {
                            "__typename": "Issue", "number": 1, "title": "x", "state": "OPEN",
                            "repository": {"nameWithOwner": "acme/widgets"},
                            "labels": {"nodes": []}, "milestone": None, "parent": None,
                        },
                        "fieldValues": {"nodes": []},
                    }],
                }}}
            }
        else:
            raise AssertionError(f"unexpected query: {query[:80]}")
        return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")

    def test_an_unresolvable_option_fails_on_stderr_not_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "changeset.tsv")
            with open(path, "w") as handle:
                handle.write("1\tstatus\tShipped\n")
            out, err = io.StringIO(), io.StringIO()
            with mock.patch("subprocess.run", self._stub_gh):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = gpb.main(["apply", "-o", "acme", "-n", "8", "--changeset", path])
        self.assertEqual(1, code)
        self.assertIn("FAIL  #1 status=Shipped: no option 'Shipped'", err.getvalue())
        self.assertNotIn("FAIL", out.getvalue(), "a refusal belongs on stderr, not the row log")


if __name__ == "__main__":
    unittest.main()

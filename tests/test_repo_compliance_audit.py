"""repo-compliance-audit's parser, dispatch, and exit-code contract.

audit.py reads checklist rows from a plugin root, runs each row's check kind against a
repo, and prints a pass/gap table. Git is the only subprocess boundary (`rev-parse` for
the toplevel, `check-ignore` for the gitignore checks) — both are stubbed here so no test
ever shells out. A hand-written checklist fixture (not the real standards' checklists)
exercises the parser and several check kinds independently of the standards' content;
one test loads the real checklists to prove they still parse without error.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "repo-compliance-audit")
REAL_PLUGIN_ROOT = os.path.join(ROOT, "primitives-core")

sys.path.insert(0, os.path.join(SKILL, "scripts"))

import audit  # noqa: E402

FIXTURE_CHECKLIST = """# fixture checklist

| DOC-01 | docs | `path-exists: README.md` | file exists |
| DOC-02 | docs | `path-exists: MISSING.md` | file exists |
| GIT-01 | git | `gitignore-tracks: .env` | tracked, not ignored |
| GIT-02 | git | `gitignore-ignores: secrets.txt` | ignored (migration debt) |
| MEM-01 | memory | `frontmatter-has: owner` | frontmatter has owner |
not a table row at all
| bad-id | area | not-backtick-wrapped | cond |
"""


def fake_git_run(argv, **kwargs):
    """Stand-in for subprocess.run covering both git calls audit.py makes.

    `.env` reads as tracked (not ignored, check-ignore exit 1); `secrets.txt` reads as
    ignored (exit 0). Anything else not-ignored, matching a typical fixture repo.
    """
    if argv[:2] == ["git", "rev-parse"]:
        return subprocess.CompletedProcess(argv, 0, stdout=kwargs.get("cwd", "") + "\n", stderr="")
    if argv[:2] == ["git", "check-ignore"]:
        probe = argv[-1]
        code = 0 if probe == "secrets.txt" else 1
        return subprocess.CompletedProcess(argv, code, stdout="", stderr="")
    raise AssertionError(f"unexpected subprocess.run call: {argv}")


class ParseChecklist(unittest.TestCase):
    def test_yields_structured_rows_and_skips_malformed(self):
        rows = audit.parse_checklist(FIXTURE_CHECKLIST)
        self.assertEqual(
            ["DOC-01", "DOC-02", "GIT-01", "GIT-02", "MEM-01"],
            [r["id"] for r in rows],
        )
        doc01 = rows[0]
        self.assertEqual("docs", doc01["area"])
        self.assertEqual("path-exists", doc01["type"])
        self.assertEqual("README.md", doc01["arg"])
        self.assertFalse(doc01["debt"])

    def test_migration_debt_condition_sets_debt_flag(self):
        rows = audit.parse_checklist(FIXTURE_CHECKLIST)
        git02 = next(r for r in rows if r["id"] == "GIT-02")
        self.assertTrue(git02["debt"])


class LoadChecklists(unittest.TestCase):
    def test_missing_checklist_file_raises(self):
        with tempfile.TemporaryDirectory() as empty_root:
            with self.assertRaises(audit.AuditError):
                audit.load_checklists(empty_root)

    def test_checklist_with_zero_rows_raises(self):
        with tempfile.TemporaryDirectory() as root:
            for rel in audit.CHECKLIST_RELPATHS:
                path = os.path.join(root, rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as fh:
                    fh.write("# no rows here\n")
            with self.assertRaises(audit.AuditError):
                audit.load_checklists(root)

    def test_real_checklists_load_without_error(self):
        rows = audit.load_checklists(REAL_PLUGIN_ROOT)
        self.assertGreater(len(rows), 0)


def build_fixture_repo(compliant_frontmatter=True):
    repo = tempfile.mkdtemp()
    with open(os.path.join(repo, "README.md"), "w") as fh:
        fh.write("# demo\n")
    plans = os.path.join(repo, "_meta", "plans")
    os.makedirs(plans)
    front = "owner: someone\n" if compliant_frontmatter else "title: no owner\n"
    with open(os.path.join(plans, "plan.md"), "w") as fh:
        fh.write(f"---\n{front}---\nbody\n")
    return repo


class RunAudit(unittest.TestCase):
    def test_path_exists_pass_and_gap(self):
        repo = build_fixture_repo()
        rows = [r for r in audit.parse_checklist(FIXTURE_CHECKLIST) if r["id"] in ("DOC-01", "DOC-02")]
        results = audit.run_audit(repo, rows)
        verdicts = {r["id"]: r["verdict"] for r in results}
        self.assertEqual(audit.PASS, verdicts["DOC-01"])
        self.assertEqual(audit.GAP, verdicts["DOC-02"])

    @patch("audit.subprocess.run", side_effect=fake_git_run)
    def test_gitignore_pass_and_gap(self, _mock_run):
        repo = build_fixture_repo()
        rows = [r for r in audit.parse_checklist(FIXTURE_CHECKLIST) if r["id"] in ("GIT-01", "GIT-02")]
        results = audit.run_audit(repo, rows)
        verdicts = {r["id"]: r["verdict"] for r in results}
        # GIT-01 wants .env tracked (not ignored) -> fake reports exit 1 (not ignored) -> pass
        self.assertEqual(audit.PASS, verdicts["GIT-01"])
        # GIT-02 wants secrets.txt ignored -> fake reports exit 0 (ignored) -> pass
        self.assertEqual(audit.PASS, verdicts["GIT-02"])

    @patch("audit.subprocess.run", side_effect=fake_git_run)
    def test_gitignore_gap_when_expectation_flips(self, _mock_run):
        repo = build_fixture_repo()
        row = next(r for r in audit.parse_checklist(FIXTURE_CHECKLIST) if r["id"] == "GIT-01")
        row = dict(row, arg="secrets.txt")  # secrets.txt IS ignored, but GIT-01 wants tracked
        results = audit.run_audit(repo, [row])
        self.assertEqual(audit.GAP, results[0]["verdict"])

    def test_frontmatter_has_pass_and_gap(self):
        row = next(r for r in audit.parse_checklist(FIXTURE_CHECKLIST) if r["id"] == "MEM-01")
        compliant = build_fixture_repo(compliant_frontmatter=True)
        noncompliant = build_fixture_repo(compliant_frontmatter=False)
        self.assertEqual(audit.PASS, audit.run_audit(compliant, [row])[0]["verdict"])
        self.assertEqual(audit.GAP, audit.run_audit(noncompliant, [row])[0]["verdict"])

    def test_no_inline_hooks_pass_and_gap(self):
        row = dict(audit.HOOK_ROW)
        repo_clean = build_fixture_repo()
        os.makedirs(os.path.join(repo_clean, ".claude"))
        with open(os.path.join(repo_clean, ".claude", "settings.json"), "w") as fh:
            fh.write(
                '{"hooks": {"PreToolUse": [{"hooks": '
                '[{"type": "command", "command": "python3 hooks/foo/run.py"}]}]}}'
            )
        self.assertEqual(audit.PASS, audit.run_audit(repo_clean, [row])[0]["verdict"])

        repo_inline = build_fixture_repo()
        os.makedirs(os.path.join(repo_inline, ".claude"))
        with open(os.path.join(repo_inline, ".claude", "settings.json"), "w") as fh:
            fh.write(
                '{"hooks": {"PreToolUse": [{"hooks": '
                '[{"type": "command", "command": "echo hi; rm -rf /tmp/x"}]}]}}'
            )
        self.assertEqual(audit.GAP, audit.run_audit(repo_inline, [row])[0]["verdict"])

    def test_unknown_check_type_raises(self):
        with self.assertRaises(audit.AuditError):
            audit.run_audit(build_fixture_repo(), [{"id": "X-01", "type": "not-a-real-check", "arg": ""}])


class RenderTable(unittest.TestCase):
    def test_table_shows_pass_and_gap_markers_and_summary(self):
        repo = build_fixture_repo()
        rows = [r for r in audit.parse_checklist(FIXTURE_CHECKLIST) if r["id"] in ("DOC-01", "DOC-02")]
        results = audit.run_audit(repo, rows)
        table = audit.render_table(repo, results, {})
        self.assertIn("DOC-01", table)
        self.assertIn(audit.PASS, table)
        self.assertIn("DOC-02", table)
        self.assertIn(audit.GAP, table)
        self.assertIn("1 pass / 1 gap", table)


class Main(unittest.TestCase):
    def _fixture_plugin_root(self):
        root = tempfile.mkdtemp()
        for rel in audit.CHECKLIST_RELPATHS:
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(FIXTURE_CHECKLIST)
        return root

    @patch("audit.subprocess.run", side_effect=fake_git_run)
    def test_exit_zero_on_clean_repo_despite_gap_rows(self, _mock_run):
        # audit.py's stated stance: read-only reporting, exit 0 whether or not gaps
        # exist (see module docstring); non-zero is reserved for hard errors only.
        repo = build_fixture_repo()
        plugin_root = self._fixture_plugin_root()
        with patch("os.getcwd", return_value=repo):
            code = audit.main(["--plugin-root", plugin_root])
        self.assertEqual(audit.EXIT_OK, code)

    def test_exit_error_when_plugin_root_missing(self):
        with patch.dict(os.environ, {"CLAUDE_PLUGIN_ROOT": ""}, clear=False):
            code = audit.main([])
        self.assertEqual(audit.EXIT_ERROR, code)

    @patch("audit.subprocess.run", side_effect=fake_git_run)
    def test_exit_error_when_checklist_missing(self, _mock_run):
        repo = build_fixture_repo()
        with tempfile.TemporaryDirectory() as empty_root:
            with patch("os.getcwd", return_value=repo):
                code = audit.main(["--plugin-root", empty_root])
        self.assertEqual(audit.EXIT_ERROR, code)


if __name__ == "__main__":
    unittest.main()

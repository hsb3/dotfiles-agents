"""Tests for the mise-en-place-scaffold skill's scripts/scaffold.py.

Unit level: the duplicated manifest reader (shared semantics with audit.py proven by
parsing the same text through both), stub shapes, template sourcing. Integration level:
full subprocess runs against `git init` fixture repos — plan read-only (TC-001), apply
creates exactly the plan (TC-002), idempotence (TC-003), conflict-never-overwritten
(TC-004), byte-identical template is no conflict (TC-005), empty repo passes the audit
after one --apply (TC-006), manifest init + tracking (TC-007), shared manifest
semantics (TC-008), malformed/unknown fields (TC-009), non-mechanical items reported
only (TC-010), dirty-tree warning (TC-011), memory-stub compatibility shape (TC-012).

The never-overwrite property is asserted byte-for-byte; the plan read-only property is
asserted with the same `git status` + full-tree-hash probe test_audit.py uses.

Stdlib-only (unittest), so `make test` runs in CI with zero install.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests.test_audit import (
    GITIGNORE_TEMPLATE,
    PLUGIN_ROOT,
    _write,
    make_conformant_repo,
    parse_rows,
    run_audit,
    tree_state,
)
from tests.test_audit import A as AUDIT  # the audit module (shared-semantics checks)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "primitives-core", "skills", "mise-en-place-scaffold")
SCAFFOLD = os.path.join(SKILL, "scripts", "scaffold.py")

sys.path.insert(0, os.path.join(SKILL, "scripts"))
import scaffold as S  # noqa: E402

ACTION_ROW_RE = re.compile(
    r"^([A-Z]+-\d+)\s*\|\s*(.*?)\s*\|\s*(CREATE|OK|CONFLICT|MANUAL)\s*\|\s*(.*)$"
)

FILLED_MANIFEST = (
    "owner: hsb3\n"
    "repo: demo\n"
    "default_branch: main\n"
    "board_title: demo board\n"
    "required_folders:\n  - notebooks/\n"
    "required_files:\n  - justfile\n"
)


def make_empty_repo(tmp, name="repo"):
    root = os.path.realpath(os.path.join(tmp, name))
    subprocess.run(["git", "init", "-q", root], check=True, capture_output=True)
    return root


def run_scaffold(repo, *extra, plugin_root=PLUGIN_ROOT):
    return subprocess.run(
        [sys.executable, SCAFFOLD, "--plugin-root", plugin_root, *extra],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def parse_actions(stdout):
    """{id: (action, detail)} from the printed table."""
    rows = {}
    for line in stdout.splitlines():
        m = ACTION_ROW_RE.match(line.strip())
        if m:
            rows[m.group(1)] = (m.group(3), m.group(4).strip())
    return rows


def parse_created(stdout):
    """Paths listed under `Planned creations:` / `Created:` (the `  + path` lines)."""
    return [
        line.strip()[2:].strip()
        for line in stdout.splitlines()
        if line.startswith("  + ")
    ]


def file_set(root):
    """Every file relpath under root, excluding .git/."""
    out = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for fn in filenames:
            out.add(os.path.relpath(os.path.join(dirpath, fn), root))
    return out


# ── TC-001: plan is read-only ─────────────────────────────────────────────────────────


class PlanReadOnly(unittest.TestCase):
    def assert_plan_read_only(self, repo):
        before = tree_state(repo)
        r = run_scaffold(repo, "--plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(tree_state(repo), before, "--plan modified the repo")
        return r

    def test_plan_writes_nothing_on_gapped_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(os.path.join(repo, "keep.txt"), "pre-existing\n")
            r = self.assert_plan_read_only(repo)
            actions = parse_actions(r.stdout)
            self.assertEqual(actions["META-01"][0], "CREATE")
            self.assertEqual(actions["ROOT-06"][0], "CREATE")
            self.assertIn("plan only — nothing written", r.stdout)
            self.assertTrue(parse_created(r.stdout))

    def test_plan_writes_nothing_on_conflicted_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(os.path.join(repo, ".gitignore"), "_meta/\n.env\n")
            r = self.assert_plan_read_only(repo)
            self.assertEqual(parse_actions(r.stdout)["ROOT-06"][0], "CONFLICT")

    def test_plan_writes_nothing_on_conformant_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_conformant_repo(os.path.realpath(os.path.join(tmp, "repo")))
            r = self.assert_plan_read_only(repo)
            actions = parse_actions(r.stdout)
            creates = {i for i, v in actions.items() if v[0] == "CREATE"}
            self.assertEqual(creates, set(), "conformant repo must plan zero creations")
            # the fixture carries a frontmatter-less issue-body.md — the scaffold's
            # duplicated plans_scope must honor the same exemption the audit does (#45)
            for i in range(1, 7):
                self.assertEqual(actions[f"PLANS-0{i}"][0], "OK", f"PLANS-0{i}")


# ── TC-002 + TC-003: apply creates exactly the plan; repeat is a no-op ────────────────


class ApplyAndIdempotence(unittest.TestCase):
    def test_apply_creates_exactly_the_plan_then_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            planned = parse_created(run_scaffold(repo, "--plan").stdout)
            planned_files = {p for p in planned if not p.endswith("/")}
            before = file_set(repo)

            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            created = parse_created(r.stdout)
            self.assertEqual(created, planned, "apply diverged from the plan")
            self.assertEqual(
                file_set(repo) - before,
                planned_files,
                "filesystem delta is not exactly the planned file set",
            )
            for d in (p for p in planned if p.endswith("/")):
                self.assertTrue(os.path.isdir(os.path.join(repo, d)), d)

            # TC-003: re-plan is zero creations; re-apply is byte-identical
            r2 = run_scaffold(repo, "--plan")
            self.assertEqual(parse_created(r2.stdout), [])
            actions2 = parse_actions(r2.stdout)
            self.assertEqual(
                {i for i, v in actions2.items() if v[0] == "CREATE"}, set()
            )
            state = tree_state(repo)
            r3 = run_scaffold(repo, "--apply")
            self.assertEqual(r3.returncode, 0, r3.stderr)
            self.assertEqual(parse_created(r3.stdout), [])
            self.assertEqual(tree_state(repo), state, "second --apply changed bytes")

    def test_apply_on_conformant_repo_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_conformant_repo(os.path.realpath(os.path.join(tmp, "repo")))
            state = tree_state(repo)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(parse_created(r.stdout), [])
            self.assertEqual(tree_state(repo), state)


# ── TC-004 + TC-005: conflicts never overwritten; identical file is no conflict ───────


class Conflicts(unittest.TestCase):
    HAND_ROLLED = "_meta/\n.env\nnode_modules\n"

    def test_conflicting_gitignore_diffed_untouched_still_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            gi = os.path.join(repo, ".gitignore")
            _write(gi, self.HAND_ROLLED)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(gi, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), self.HAND_ROLLED, ".gitignore was modified")
            actions = parse_actions(r.stdout)
            self.assertEqual(actions["ROOT-06"][0], "CONFLICT")
            self.assertEqual(actions["IGNORE-06"][0], "CONFLICT")
            # the diff points at the missing track-by-default stanza (ADR-0006)
            self.assertIn("Conflict diffs", r.stdout)
            self.assertIn("+_meta/operations/*", r.stdout)
            self.assertNotIn(".gitignore", parse_created(r.stdout))
            # re-run audit: the row keeps failing (never silently passed)
            audit_rows = parse_rows(run_audit(repo).stdout)
            self.assertEqual(audit_rows["IGNORE-06"][0], "GAP")
            self.assertEqual(audit_rows["IGNORE-02"][0], "GAP")

    def test_byte_identical_template_is_ok_not_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            shutil.copyfile(GITIGNORE_TEMPLATE, os.path.join(repo, ".gitignore"))
            r = run_scaffold(repo, "--plan")
            actions = parse_actions(r.stdout)
            self.assertEqual(actions["ROOT-06"][0], "OK")
            self.assertNotIn("Conflict diffs", r.stdout)

    def test_differing_github_template_untouched_with_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            ci = os.path.join(repo, ".github", "workflows", "ci.yml")
            _write(ci, "name: my own ci\n")
            r = run_scaffold(repo, "--apply")
            actions = parse_actions(r.stdout)
            self.assertEqual(actions["GH-07"][0], "CONFLICT")
            with open(ci, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "name: my own ci\n")


# ── TC-006: empty repo + filled manifest + one --apply passes the audit ───────────────


class EmptyRepoPath(unittest.TestCase):
    def test_one_apply_produces_audit_passing_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(os.path.join(repo, "_meta", "mise-en-place.yml"), FILLED_MANIFEST)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            actions = parse_actions(r.stdout)
            # authored-content rows reported as out-of-scope guidance, not created
            for rid, skill in (
                ("ROOT-01", "readme-value-and-proof"),
                ("ROOT-02", "agent-dot-md-authoring"),
                ("ROOT-03", "agent-dot-md-authoring"),
            ):
                self.assertEqual(actions[rid][0], "MANUAL")
                self.assertIn(skill, actions[rid][1])
            # manifest extras created (VAR rows)
            self.assertTrue(os.path.isdir(os.path.join(repo, "notebooks")))
            self.assertTrue(os.path.isfile(os.path.join(repo, "justfile")))
            # the audit passes everything except the authored-content rows
            audit = run_audit(repo)
            self.assertEqual(audit.returncode, 0, audit.stderr)
            rows = parse_rows(audit.stdout)
            gaps = {i for i, v in rows.items() if v[0] != "PASS"}
            self.assertEqual(gaps, {"ROOT-01", "ROOT-02", "ROOT-03", "DOCS-02"})
            self.assertEqual(rows["VAR-01"][0], "PASS")
            self.assertEqual(rows["VAR-02"][0], "PASS")


# ── TC-007: manifest init + tracking ──────────────────────────────────────────────────


class ManifestInit(unittest.TestCase):
    def test_init_writes_template_never_overwrites_and_is_tracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            shutil.copyfile(GITIGNORE_TEMPLATE, os.path.join(repo, ".gitignore"))
            r = run_scaffold(repo, "--init-manifest")
            self.assertEqual(r.returncode, 0, r.stderr)
            path = os.path.join(repo, "_meta", "mise-en-place.yml")
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for field in (
                "owner:",
                "repo:",
                "default_branch: main",
                "gh_issue_labels:",
                "gh_milestones:",
                "board_title:",
                "required_folders:",
                "required_files:",
            ):
                self.assertIn(field, text)
            # both readers accept the freshly written template
            self.assertEqual(
                AUDIT.load_manifest(repo),
                {
                    "default_branch": "main",
                    "required_folders": [],
                    "required_files": [],
                },
            )
            # not ignored: _meta/ is tracked by default (ADR-0006)
            probe = subprocess.run(
                ["git", "check-ignore", "-q", "--", "_meta/mise-en-place.yml"],
                cwd=repo,
                capture_output=True,
            )
            self.assertEqual(probe.returncode, 1, "manifest must not be gitignored")
            # a second init never overwrites
            _write(path, text + "# hand edit\n")
            r2 = run_scaffold(repo, "--init-manifest")
            self.assertEqual(r2.returncode, 0)
            self.assertIn("not overwritten", r2.stdout)
            with open(path, encoding="utf-8") as fh:
                self.assertTrue(fh.read().endswith("# hand edit\n"))


# ── TC-008: manifest semantics shared with the audit ──────────────────────────────────


class SharedManifestSemantics(unittest.TestCase):
    MANIFEST = (
        "owner: mhi-raptorxai\n"
        "default_branch: dev\n"
        "gh_issue_labels:\n  - gate:pilot\n"
        "board_title: rollout\n"
        "required_folders:\n  - notebooks/\n  - data\n"
        "required_files: [justfile]\n"
    )

    def _both_readers(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            _write(os.path.join(tmp, "_meta", "mise-en-place.yml"), text)
            scaffold_view, _ = S.load_manifest(tmp)
            audit_view = AUDIT.load_manifest(tmp)
            return scaffold_view, audit_view

    def test_audit_side_fields_parse_identically(self):
        sv, av = self._both_readers(self.MANIFEST)
        for key in ("default_branch", "required_folders", "required_files"):
            self.assertEqual(sv[key], av[key], key)
        # scaffold additionally reads its own scalars
        self.assertEqual(sv["owner"], "mhi-raptorxai")
        self.assertEqual(sv["board_title"], "rollout")

    def test_variance_rows_identical(self):
        sv, av = self._both_readers(self.MANIFEST)
        s_rows = [(r["id"], r["type"], r["arg"]) for r in S.variance_rows(sv)]
        a_rows = [(r["id"], r["type"], r["arg"]) for r in AUDIT.variance_rows(av)]
        self.assertEqual(s_rows, a_rows)

    def test_acceptance_parity_on_malformed_input(self):
        for bad in (
            "default_branch dev\n",
            "required_folders: notebooks/\n",
            "default_branch:\n",
        ):
            with self.assertRaises(S.ScaffoldError, msg=bad):
                self._both_readers(bad)
        # what the audit tolerates (unknown blocks), the scaffold tolerates too
        tolerated = "github:\n  labels:\n    - x\nowner: hsb3\n"
        sv, av = self._both_readers(tolerated)
        self.assertEqual(av, {})
        self.assertEqual(sv["owner"], "hsb3")

    def test_scaffold_creates_extras_audit_then_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(os.path.join(repo, "_meta", "mise-en-place.yml"), self.MANIFEST)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            audit = run_audit(repo)
            self.assertIn("default_branch=dev", audit.stdout)
            rows = parse_rows(audit.stdout)
            self.assertEqual(rows["VAR-01"][0], "PASS")  # notebooks/
            self.assertEqual(rows["VAR-02"][0], "PASS")  # data/
            self.assertEqual(rows["VAR-03"][0], "PASS")  # justfile


# ── TC-009: malformed aborts before planning; unknown field warns ─────────────────────


class ManifestErrorPaths(unittest.TestCase):
    def test_malformed_manifest_aborts_nothing_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(
                os.path.join(repo, "_meta", "mise-en-place.yml"),
                "default_branch dev\n",
            )
            before = tree_state(repo)
            for mode in ("--plan", "--apply"):
                r = run_scaffold(repo, mode)
                self.assertEqual(r.returncode, 2, mode)
                self.assertIn("malformed manifest", r.stderr)
                self.assertNotIn("Planned creations", r.stdout)
                self.assertEqual(tree_state(repo), before, f"{mode} wrote something")

    def test_unknown_field_warns_and_plans_normally(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(
                os.path.join(repo, "_meta", "mise-en-place.yml"),
                "default_branch: main\nfavorite_color: blue\n",
            )
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("unknown manifest field `favorite_color`", r.stderr)
            self.assertEqual(parse_actions(r.stdout)["META-01"][0], "CREATE")


# ── TC-010: non-mechanical items reported with guidance, never acted on ───────────────


class NonMechanicalItems(unittest.TestCase):
    INLINE_HOOK_SETTINGS = (
        '{"hooks": {"Stop": [{"hooks": [{"type": "command", '
        '"command": "echo done && say finished"}]}]}}'
    )

    def test_avoid_file_and_inline_hook_reported_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            notes = os.path.join(repo, "NOTES.md")
            settings = os.path.join(repo, ".claude", "settings.json")
            _write(notes, "scratch\n")
            _write(settings, self.INLINE_HOOK_SETTINGS)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            actions = parse_actions(r.stdout)
            self.assertEqual(actions["AVOID-03"][0], "MANUAL")
            self.assertIn("_meta/", actions["AVOID-03"][1])
            self.assertEqual(actions["HOOK-01"][0], "MANUAL")
            self.assertIn("hook-composition", actions["HOOK-01"][1])
            # existing settings.json satisfies CLAUDE-06 and is not replaced
            self.assertEqual(actions["CLAUDE-06"][0], "OK")
            with open(notes, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "scratch\n")
            with open(settings, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), self.INLINE_HOOK_SETTINGS)
            self.assertTrue(os.path.isfile(notes), "AVOID file must never be moved")


# ── TC-011: dirty-tree warning; creations proceed, edits untouched ────────────────────


class DirtyTree(unittest.TestCase):
    def test_dirty_tree_warns_and_proceeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            f = os.path.join(repo, "work.txt")
            _write(f, "v1\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=t@t",
                    "-c",
                    "user.name=t",
                    "commit",
                    "-qm",
                    "x",
                ],
                cwd=repo,
                check=True,
            )
            _write(f, "v2 uncommitted\n")
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("working tree is dirty", r.stdout)
            self.assertIn("additive-only", r.stdout)
            self.assertTrue(parse_created(r.stdout), "creations must proceed")
            with open(f, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "v2 uncommitted\n")


# ── TC-012: memory stub shape (cc-project-memory compatibility) ───────────────────────


class MemoryStub(unittest.TestCase):
    def test_stub_shape_and_audit_mem_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp, name="stub-demo")
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            index = os.path.join(repo, ".claude", "memory", "MEMORY.md")
            with open(index, encoding="utf-8") as fh:
                text = fh.read()
            # cc-project-memory MEMORY_STUB shape: comment header, repo-named H1,
            # one-line-per-file format hint (`init` skips creation when the file
            # exists, so any scaffolded index makes a later init a no-op)
            self.assertTrue(
                text.startswith("<!-- Project auto-memory index for stub-demo.")
            )
            self.assertIn("# Project memory — stub-demo", text)
            self.assertIn("one line per memory file", text)
            # the stub must not carry a dangling example link (audit MEM-04)
            rows = parse_rows(run_audit(repo).stdout)
            for rid in ("MEM-01", "MEM-02", "MEM-03", "MEM-04"):
                self.assertEqual(rows[rid][0], "PASS", rid)


# ── #38: gitignore-swallow warning ────────────────────────────────────────────────────


class GitignoreSwallowWarning(unittest.TestCase):
    """A planned creation the target repo's own gitignore swallows gets a per-path
    warning in plan and apply output; behavior and exit codes are unchanged."""

    def test_ignored_planned_file_warns_plan_and_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(os.path.join(repo, ".gitignore"), ".mcp.json\n")
            before = tree_state(repo)
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(tree_state(repo), before, "--plan modified the repo")
            self.assertIn("ignored by the target repo's .gitignore", r.stdout)
            self.assertIn("! .mcp.json", r.stdout)
            r2 = run_scaffold(repo, "--apply")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("! .mcp.json", r2.stdout)
            # informational only: additive behavior unchanged, file still created
            self.assertIn(".mcp.json", parse_created(r2.stdout))
            self.assertTrue(os.path.isfile(os.path.join(repo, ".mcp.json")))

    def test_no_warning_when_nothing_swallowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("ignored by the target repo's .gitignore", r.stdout)


# ── #44: duplicate-reviewer probe + template asset guards ─────────────────────────────


class DuplicateReviewerProbe(unittest.TestCase):
    """An existing claude-code-action PR-review workflow under another name makes
    GH-08 MANUAL instead of planning a duplicate reviewer."""

    EQUIVALENT = (
        "name: PR Review with Progress Tracking\n"
        "on:\n"
        "  pull_request:\n"
        "    types: [opened, synchronize]\n"
        "jobs:\n"
        "  review:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: anthropics/claude-code-action@v1\n"
    )
    TAG_WORKFLOW = (
        "name: Claude\n"
        "on:\n"
        "  issue_comment:\n"
        "    types: [created]\n"
        "  pull_request_review_comment:\n"
        "    types: [created]\n"
        "jobs:\n"
        "  claude:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: anthropics/claude-code-action@v1\n"
    )

    def test_equivalent_review_workflow_is_manual_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(
                os.path.join(repo, ".github", "workflows", "pr-review.yml"),
                self.EQUIVALENT,
            )
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            actions = parse_actions(r.stdout)
            self.assertEqual(actions["GH-08"][0], "MANUAL")
            self.assertIn("pr-review.yml", actions["GH-08"][1])
            self.assertNotIn(
                ".github/workflows/claude-review.yml", parse_created(r.stdout)
            )
            r2 = run_scaffold(repo, "--apply")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertFalse(
                os.path.isfile(
                    os.path.join(repo, ".github", "workflows", "claude-review.yml")
                ),
                "apply must not create a duplicate reviewer",
            )

    def test_tag_workflow_is_not_a_review_equivalent(self):
        # claude.yml-style triggers (pull_request_review_comment:, no pull_request:)
        # must not suppress the GH-08 creation
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(
                os.path.join(repo, ".github", "workflows", "tag-claude.yml"),
                self.TAG_WORKFLOW,
            )
            r = run_scaffold(repo, "--plan")
            self.assertEqual(parse_actions(r.stdout)["GH-08"][0], "CREATE")


class TemplateAssets(unittest.TestCase):
    """Template defects from the Gate-2 pilot: issue forms ship label-less; the
    review workflow cancels stale in-progress runs."""

    ASSETS = os.path.join(
        PLUGIN_ROOT, "skills", "repo-meta-structure", "assets", "github"
    )

    def test_issue_templates_carry_no_labels(self):
        for name in ("bug.yml", "feature.yml", "epic.yml"):
            path = os.path.join(self.ASSETS, "ISSUE_TEMPLATE", name)
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    self.assertFalse(
                        line.startswith("labels:"),
                        f"{name} hardcodes labels — templates are label-less by design",
                    )

    def test_claude_review_cancels_stale_runs(self):
        path = os.path.join(self.ASSETS, "workflows", "claude-review.yml")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("concurrency:", text)
        self.assertIn("cancel-in-progress: true", text)


# ── #34: committed scaffold survives a fresh clone ────────────────────────────────────


class CloneSurvivability(unittest.TestCase):
    def test_fresh_clone_audit_has_no_meta_regaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=t@t",
                    "-c",
                    "user.name=t",
                    "commit",
                    "-qm",
                    "scaffold",
                ],
                cwd=repo,
                check=True,
            )
            clone = os.path.realpath(os.path.join(tmp, "clone"))
            subprocess.run(
                ["git", "clone", "-q", repo, clone], check=True, capture_output=True
            )
            for d in ("_archive", "briefings", "operations", "research"):
                self.assertTrue(
                    os.path.isdir(os.path.join(clone, "_meta", d)),
                    f"_meta/{d}/ lost on clone — .gitkeep not tracked",
                )
            rows = parse_rows(run_audit(clone).stdout)
            gaps = {i for i, v in rows.items() if v[0] != "PASS"}
            self.assertEqual(
                gaps,
                {"ROOT-01", "ROOT-02", "ROOT-03", "DOCS-02"},
                "fresh clone must re-gap only the authored-content rows",
            )


# ── unit: plan internals ──────────────────────────────────────────────────────────────


class PlanInternals(unittest.TestCase):
    def test_template_source_mapping(self):
        self.assertTrue(
            S.template_source(PLUGIN_ROOT, ".gitignore").endswith("gitignore.template")
        )
        self.assertTrue(
            S.template_source(PLUGIN_ROOT, ".github/workflows/ci.yml").endswith(
                os.path.join("assets", "github", "workflows", "ci.yml")
            )
        )
        self.assertTrue(
            S.template_source(PLUGIN_ROOT, "lefthook.yml").endswith(
                "lefthook.template.yml"
            )
        )
        self.assertIsNone(S.template_source(PLUGIN_ROOT, "Makefile"))
        # every GH checklist row resolves to a real shipped asset
        for row in S.load_checklists(PLUGIN_ROOT):
            src = S.template_source(PLUGIN_ROOT, row["arg"])
            if src is not None:
                self.assertTrue(os.path.isfile(src), row["arg"])

    def test_gitkeep_only_in_otherwise_empty_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            planned = parse_created(run_scaffold(repo, "--plan").stdout)
            self.assertIn("_meta/plans/.gitkeep", planned)
            # docs/ receives a planned file (README.md, #40) so it needs no keep-file
            self.assertNotIn("docs/.gitkeep", planned)
            # dirs that receive a planned file need no keep-file
            self.assertNotIn(".claude/memory/.gitkeep", planned)

    def test_mutually_exclusive_modes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--plan", "--apply")
            self.assertEqual(r.returncode, 2)
            self.assertIn("mutually exclusive", r.stderr)

    def test_not_a_git_repo_is_hard_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = os.path.realpath(os.path.join(tmp, "plain"))
            os.makedirs(plain)
            r = run_scaffold(plain, "--plan")
            self.assertEqual(r.returncode, 2)
            self.assertIn("not a git repository", r.stderr)

    def test_broken_plugin_root_is_hard_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--plan", plugin_root=tmp)
            self.assertEqual(r.returncode, 2)
            self.assertIn("checklist file missing", r.stderr)


class DocsRows(unittest.TestCase):
    """DOCS-01..05 (#40): templated docs files, CHARTER authored, broken-install path."""

    def test_plan_creates_docs_templates_and_flags_charter_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            out = run_scaffold(repo, "--plan").stdout
            planned = parse_created(out)
            for f in (
                "docs/README.md",
                "docs/decisions/README.md",
                "docs/decisions/0000-template.md",
            ):
                self.assertIn(f, planned, f"{f} not planned")
            self.assertNotIn("docs/CHARTER.md", planned)
            charter_row = [ln for ln in out.splitlines() if "DOCS-02" in ln]
            self.assertTrue(charter_row and "MANUAL" in charter_row[0], charter_row)

    def test_apply_writes_template_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(os.path.join(repo, "docs", "README.md"), encoding="utf-8") as fh:
                self.assertIn("The boundary with `_meta/` is load-bearing", fh.read())
            with open(
                os.path.join(repo, "docs", "decisions", "0000-template.md"),
                encoding="utf-8",
            ) as fh:
                self.assertIn("## Consequences", fh.read())
            self.assertFalse(
                os.path.exists(os.path.join(repo, "docs", "CHARTER.md")),
                "CHARTER must never be scaffolded",
            )

    def test_missing_docs_asset_is_broken_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            # clone the plugin root minus one docs asset
            broken = os.path.join(tmp, "plugin")
            shutil.copytree(PLUGIN_ROOT, broken)
            os.remove(
                os.path.join(
                    broken,
                    "skills",
                    "repo-meta-structure",
                    "assets",
                    "docs",
                    "README.md",
                )
            )
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--plan", plugin_root=broken)
            self.assertEqual(r.returncode, 2)
            self.assertIn("standard template asset missing", r.stderr)


# ── #67: workflow-template follow-up notes (ci target + secrets) ──────────────────────


class WorkflowFollowupNotes(unittest.TestCase):
    """Planning GH-07 against a repo whose Makefile lacks a `ci:` target emits a
    visible note (the template runs `make ci` and would land a red check); planning
    the claude workflows notes the required repo secret. Informational only —
    actions and additive behavior are unchanged."""

    def test_warns_when_makefile_lacks_ci_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(os.path.join(repo, "Makefile"), "help:\n\t@echo hi\n")
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("no `ci` Makefile target", r.stdout)
            self.assertIn("follow-up(s) the scaffold cannot do", r.stdout)
            actions = parse_actions(r.stdout)
            self.assertEqual(
                actions["GH-07"][0], "CREATE", "note must not block CREATE"
            )

    def test_warns_when_makefile_missing_entirely(self):
        # The Makefile stub deliberately ships without a no-op ci: target, so the
        # note fires for an empty repo too.
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("no `ci` Makefile target", r.stdout)

    def test_no_ci_note_when_target_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(os.path.join(repo, "Makefile"), "ci: check\ncheck:\n\t@true\n")
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("no `ci` Makefile target", r.stdout)

    def test_no_ci_note_when_ci_yml_already_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            _write(
                os.path.join(repo, ".github", "workflows", "ci.yml"),
                "name: ci\non: [push]\n",
            )
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("no `ci` Makefile target", r.stdout)

    def test_secrets_note_on_both_claude_workflows(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--plan")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.count("repo secret before it can run"), 2)

    def test_apply_prints_notes_and_stays_additive(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_empty_repo(tmp)
            r = run_scaffold(repo, "--apply")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("no `ci` Makefile target", r.stdout)
            self.assertIn(".github/workflows/ci.yml", parse_created(r.stdout))


if __name__ == "__main__":
    unittest.main()

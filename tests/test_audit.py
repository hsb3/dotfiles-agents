"""Tests for the repo-compliance-audit skill's scripts/audit.py.

Unit level: checklist parsing, the tailored manifest reader, the HOOK-01 command
classifier, index-link resolution. Integration level: full subprocess runs against
`git init` fixture repos — conformant (all PASS), one fixture per gap class, the
memory-taxonomy MEM-01..04 matrix (persisted regression fixtures for that standard's
ad-hoc verification), manifest variance, and every error path. The read-only property
(TC-003) is asserted on every fixture: `git status --porcelain` + a full tree hash are
byte-identical before/after each run.

Stdlib-only (unittest), so `make test` runs in CI with zero install.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "primitives-core", "skills", "repo-compliance-audit")
AUDIT = os.path.join(SKILL, "scripts", "audit.py")
PLUGIN_ROOT = os.path.join(
    REPO, "primitives-core"
)  # real checklists: skills/*/references/
GITIGNORE_TEMPLATE = os.path.join(
    REPO,
    "primitives-core",
    "skills",
    "repo-meta-structure",
    "assets",
    "gitignore.template",
)

sys.path.insert(0, os.path.join(SKILL, "scripts"))
import audit as A  # noqa: E402

ROW_RE = re.compile(r"^([A-Z]+-\d+)\s*\|\s*(.*?)\s*\|\s*(PASS|GAP|N/A)\s*\|\s*(.*)$")

SCRIPT_HOOK_SETTINGS = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Write|Edit",
                "hooks": [
                    {
                        "type": "command",
                        "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/format/run.sh",
                    }
                ],
            }
        ]
    }
}

PLAN_FRONTMATTER = (
    "---\n"
    "title: Fixture plan\n"
    "type: plan\n"
    "status: active\n"
    "created: 2026-07-02\n"
    "purpose: fixture\n"
    "notes: none\n"
    "---\n\n# Fixture plan\n"
)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def make_conformant_repo(root):
    """A fixture repo satisfying every checklist row (TC-001 baseline)."""
    subprocess.run(["git", "init", "-q", root], check=True, capture_output=True)
    for d in (
        "_meta/_archive",
        "_meta/briefings",
        "_meta/plans/inbox",
        "_meta/operations",
        "_meta/research",
        ".claude/agents",
        ".claude/hooks",
        ".claude/rules",
        ".claude/skills",
        ".github/ISSUE_TEMPLATE",
        ".github/workflows",
        "docs",
        "scripts",
        "tests",
    ):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    for f in (
        "_meta/HANDOFF.md",
        "_meta/README.md",
        ".github/ISSUE_TEMPLATE/config.yml",
        ".github/ISSUE_TEMPLATE/bug.yml",
        ".github/ISSUE_TEMPLATE/feature.yml",
        ".github/ISSUE_TEMPLATE/epic.yml",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/dependabot.yml",
        ".github/workflows/ci.yml",
        ".github/workflows/claude-review.yml",
        ".github/workflows/claude.yml",
        "README.md",
        "CLAUDE.md",
        "AGENTS.md",
        "Makefile",
        "lefthook.yml",
        ".mcp.json",
    ):
        _write(os.path.join(root, f), "fixture\n")
    shutil.copyfile(GITIGNORE_TEMPLATE, os.path.join(root, ".gitignore"))
    _write(
        os.path.join(root, ".claude", "settings.json"),
        json.dumps(SCRIPT_HOOK_SETTINGS, indent=2),
    )
    # memory: index + one resolving topic link (MEM-01..04 all pass)
    _write(
        os.path.join(root, ".claude", "memory", "MEMORY.md"),
        "- [Fixture topic](fixture-topic.md) — hook\n",
    )
    _write(os.path.join(root, ".claude", "memory", "fixture-topic.md"), "fact\n")
    # plans: one conformant doc + excluded files (README.md, _config.md) that would
    # fail the frontmatter rows if the scope exclusions ever regressed
    _write(os.path.join(root, "_meta", "plans", "fixture-plan.md"), PLAN_FRONTMATTER)
    _write(os.path.join(root, "_meta", "plans", "inbox", "intake.md"), PLAN_FRONTMATTER)
    _write(os.path.join(root, "_meta", "plans", "README.md"), "desk index, no fm\n")
    _write(os.path.join(root, "_meta", "plans", "_config.md"), "desk config, no fm\n")
    # staged issue bodies are exempt from the frontmatter schema (owner ruling
    # 2026-07-02, #45): a raw publishable body must not gap PLANS-01..06
    _write(
        os.path.join(root, "_meta", "plans", "fixture-slug", "issue-body.md"),
        "## Problem\n\nraw publishable issue body — no frontmatter\n",
    )
    # docs/ minimums (DOCS-01..05, #40)
    for f in (
        "docs/README.md",
        "docs/CHARTER.md",
        "docs/decisions/README.md",
        "docs/decisions/0000-template.md",
    ):
        _write(os.path.join(root, f), "fixture\n")
    return root


def run_audit(repo, plugin_root=PLUGIN_ROOT, extra=()):
    return subprocess.run(
        [sys.executable, AUDIT, "--plugin-root", plugin_root, *extra],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def parse_rows(stdout):
    """{id: (verdict, detail)} from the printed table."""
    rows = {}
    for line in stdout.splitlines():
        m = ROW_RE.match(line.strip())
        if m:
            rows[m.group(1)] = (m.group(3), m.group(4).strip())
    return rows


def tree_state(root):
    """(git status --porcelain, sha256 over every file incl. .git) — TC-003 probe."""
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True
    ).stdout
    h = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            h.update(os.path.relpath(p, root).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return status, h.hexdigest()


def assert_read_only(testcase, repo, plugin_root=PLUGIN_ROOT):
    """Run the audit and prove the tree is byte-identical before/after."""
    status_before, hash_before = tree_state(repo)
    r = run_audit(repo, plugin_root)
    hash_after = tree_state(repo)[1]
    status_after = tree_state(repo)[0]
    testcase.assertEqual(status_before, status_after)
    testcase.assertEqual(hash_before, hash_after, "audit modified the audited repo")
    return r


# ── unit: checklist parsing ───────────────────────────────────────────────────────────


class ChecklistParsing(unittest.TestCase):
    TABLE = (
        "| ID | Area | Check | Pass condition |\n"
        "|---|---|---|---|\n"
        "| META-01 | `_meta/` | `path-exists: _meta/_archive/` | Directory exists |\n"
        "| CLAUDE-07 | `.claude/` | `flag-if-present: .claude/commands/` | Absent *(migration debt)* |\n"
        "prose line, not a row\n"
        "| bad | row | without backtick check | x |\n"
    )

    def test_rows_and_debt_flag(self):
        rows = A.parse_checklist(self.TABLE)
        self.assertEqual([r["id"] for r in rows], ["META-01", "CLAUDE-07"])
        self.assertEqual(rows[0]["type"], "path-exists")
        self.assertEqual(rows[0]["arg"], "_meta/_archive/")
        self.assertFalse(rows[0]["debt"])
        self.assertTrue(rows[1]["debt"])

    def test_real_checklists_load_expected_families(self):
        rows = A.load_checklists(PLUGIN_ROOT)
        ids = [r["id"] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), "duplicate checklist IDs")
        prefixes = {i.rsplit("-", 1)[0] for i in ids}
        self.assertEqual(
            prefixes,
            {"META", "CLAUDE", "GH", "ROOT", "IGNORE", "AVOID", "PLANS", "MEM", "DOCS"},
        )
        types = {r["type"] for r in rows}
        self.assertTrue(types <= set(A.DISPATCH), f"unknown check types: {types}")

    def test_missing_checklist_file_is_hard_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(A.AuditError) as ctx:
                A.load_checklists(tmp)
            self.assertIn("checklist.md", str(ctx.exception))


# ── unit: manifest reader ─────────────────────────────────────────────────────────────


class ManifestReader(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            _write(os.path.join(tmp, "_meta", "mise-en-place.yml"), text)
            return A.load_manifest(tmp)

    def test_absent_manifest_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(A.load_manifest(tmp), {})

    def test_scalar_and_list_fields(self):
        m = self._load(
            "default_branch: dev\n"
            "required_folders:\n  - notebooks/\n  - data\n"
            "required_files: [justfile]\n"
        )
        self.assertEqual(m["default_branch"], "dev")
        self.assertEqual(m["required_folders"], ["notebooks/", "data"])
        self.assertEqual(m["required_files"], ["justfile"])

    def test_unknown_keys_and_nested_blocks_tolerated(self):
        # scaffold-owned fields (GitHub-side knobs) must never break the audit
        m = self._load(
            "default_branch: main\n"
            "github:\n  labels:\n    - gate:pilot\n  milestones:\n    - v1\n"
            "board: devtools\n"
        )
        self.assertEqual(m, {"default_branch": "main"})

    def test_malformed_top_level_line_aborts(self):
        with self.assertRaises(A.AuditError) as ctx:
            self._load("default_branch dev\n")
        self.assertIn("line 1", str(ctx.exception))

    def test_scalar_where_list_expected_aborts(self):
        with self.assertRaises(A.AuditError):
            self._load("required_folders: notebooks/\n")

    def test_variance_rows_generated(self):
        rows = A.variance_rows(
            {"required_folders": ["notebooks"], "required_files": ["justfile"]}
        )
        self.assertEqual(
            [(r["id"], r["type"], r["arg"]) for r in rows],
            [
                ("VAR-01", "path-exists", "notebooks/"),
                ("VAR-02", "path-exists", "justfile"),
            ],
        )


# ── unit: HOOK-01 command classifier ──────────────────────────────────────────────────


class HookClassifier(unittest.TestCase):
    def test_script_references_pass(self):
        for cmd in (
            "$CLAUDE_PROJECT_DIR/.claude/hooks/format/run.sh",
            "./.claude/hooks/lint/check.py",
            "bash .claude/hooks/guard/guard.sh",
            "python3 -u .claude/hooks/x/y.py",
            "uv run scripts/hook.py",
            "FOO=bar ./.claude/hooks/env/run.sh",
        ):
            self.assertTrue(A.is_script_invocation(cmd), cmd)

    def test_inline_shell_flagged(self):
        for cmd in (
            "echo done",
            "jq -r .tool_input",
            "grep -q TODO && exit 2",
            "cat file | grep x",
            "echo $(date) >> log.txt",
            'ruff format "$path"; ruff check',
            "",
        ):
            self.assertFalse(A.is_script_invocation(cmd), cmd)

    def test_no_settings_or_no_hooks_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            verdict, _ = A.check_no_inline_hooks(tmp, ".claude/settings.json")
            self.assertEqual(verdict, "PASS")
            _write(os.path.join(tmp, ".claude", "settings.json"), "{}")
            verdict, _ = A.check_no_inline_hooks(tmp, ".claude/settings.json")
            self.assertEqual(verdict, "PASS")

    def test_unparseable_settings_is_a_gap_with_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(os.path.join(tmp, ".claude", "settings.json"), "{not json")
            verdict, detail = A.check_no_inline_hooks(tmp, ".claude/settings.json")
            self.assertEqual(verdict, "GAP")
            self.assertIn("cannot parse", detail)


# ── unit: index-links-resolve (MEM-04 semantics) ──────────────────────────────────────


class IndexLinks(unittest.TestCase):
    def test_dangling_lines_reported_individually(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(
                os.path.join(tmp, ".claude", "memory", "MEMORY.md"),
                "- [Good](topic.md) — ok\n"
                "- [Web](https://example.com/x.md) — skipped\n"
                "- [Anchor](#section) — skipped\n"
                "- [Bad](missing.md) — dangling\n"
                "- [Also bad](sub/none.md) — dangling\n",
            )
            _write(os.path.join(tmp, ".claude", "memory", "topic.md"), "x\n")
            verdict, detail = A.check_index_links_resolve(
                tmp, ".claude/memory/MEMORY.md"
            )
            self.assertEqual(verdict, "GAP")
            self.assertIn("line 4", detail)
            self.assertIn("line 5", detail)
            self.assertNotIn("example.com", detail)

    def test_absent_index_is_not_evaluable(self):
        with tempfile.TemporaryDirectory() as tmp:
            verdict, detail = A.check_index_links_resolve(
                tmp, ".claude/memory/MEMORY.md"
            )
            self.assertEqual(verdict, "N/A")
            self.assertIn("index absent", detail)


# ── integration: full runs on fixture repos ───────────────────────────────────────────


class ConformantRepo(unittest.TestCase):
    """TC-001 + TC-003 + TC-004 on the all-pass fixture."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.repo = make_conformant_repo(
            os.path.realpath(os.path.join(cls.tmp.name, "repo"))
        )
        cls.result = assert_read_only(unittest.TestCase(), cls.repo)
        cls.rows = parse_rows(cls.result.stdout)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_rows_pass(self):
        gaps = {i: v for i, v in self.rows.items() if v[0] != "PASS"}
        self.assertEqual(gaps, {}, f"unexpected non-PASS rows: {gaps}")
        self.assertRegex(self.result.stdout, r"\n\d+ pass / 0 gap\s*$")
        self.assertEqual(self.result.returncode, 0)

    def test_every_checklist_area_verdicted(self):
        checklist_ids = {r["id"] for r in A.load_checklists(PLUGIN_ROOT)}
        printed = set(self.rows)
        self.assertTrue(
            checklist_ids <= printed,
            f"checklist rows missing from output: {checklist_ids - printed}",
        )
        self.assertIn("HOOK-01", printed)

    def test_ids_trace_to_standards(self):
        """TC-004: zero self-defined items (HOOK-01 is the sanctioned, decision-sourced
        exception until the hook-composition standard lands)."""
        checklist_ids = {r["id"] for r in A.load_checklists(PLUGIN_ROOT)}
        orphans = set(self.rows) - checklist_ids - {"HOOK-01"}
        self.assertEqual(orphans, set(), f"IDs not sourced from a standard: {orphans}")


class GapClasses(unittest.TestCase):
    """TC-002: one fixture per gap class; exactly the owning row(s) flip to GAP.
    Includes the persisted MEM-01..04 regression matrix for the memory-taxonomy
    standard. Every variant also re-proves TC-003 (read-only)."""

    def _run_variant(self, mutate, expect_gaps, expect_na=()):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_conformant_repo(os.path.realpath(os.path.join(tmp, "repo")))
            mutate(repo)
            r = assert_read_only(self, repo)
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = parse_rows(r.stdout)
            gaps = {i for i, v in rows.items() if v[0] == "GAP"}
            nas = {i for i, v in rows.items() if v[0] == "N/A"}
            self.assertEqual(gaps, set(expect_gaps))
            self.assertEqual(nas, set(expect_na))
            return rows

    def test_missing_meta_operations(self):
        self._run_variant(
            lambda repo: os.rmdir(os.path.join(repo, "_meta", "operations")),
            {"META-04"},
        )

    def test_missing_pr_template(self):
        self._run_variant(
            lambda repo: os.remove(
                os.path.join(repo, ".github", "PULL_REQUEST_TEMPLATE.md")
            ),
            {"GH-05"},
        )

    def test_stray_notes_at_root(self):
        rows = self._run_variant(
            lambda repo: _write(os.path.join(repo, "NOTES.md"), "scratch\n"),
            {"AVOID-03"},
        )
        self.assertIn("NOTES.md", rows["AVOID-03"][1])

    def test_gitignore_with_blanket_meta_ignore(self):
        def mutate(repo):
            # blanket `_meta/` ignore violates track-by-default (ADR-0006)
            _write(
                os.path.join(repo, ".gitignore"),
                ".env*\n!.env*.example\n_meta/\n"
                ".claude/settings.local.json\n.claude/worktrees/\n",
            )

        self._run_variant(
            mutate,
            {
                "IGNORE-02",
                "IGNORE-03",
                "IGNORE-04",
                "IGNORE-05",
                "IGNORE-06",
                # blanket `_meta/` also swallows the scaffolded dirs' .gitkeeps (#34)
                "IGNORE-13",
                "IGNORE-14",
                "IGNORE-15",
                "IGNORE-16",
            },
        )

    def test_plans_doc_missing_purpose(self):
        def mutate(repo):
            _write(
                os.path.join(repo, "_meta", "plans", "fixture-plan.md"),
                PLAN_FRONTMATTER.replace("purpose: fixture\n", ""),
            )

        rows = self._run_variant(mutate, {"PLANS-05"})
        self.assertIn("fixture-plan.md", rows["PLANS-05"][1])
        self.assertIn("purpose", rows["PLANS-05"][1])

    def test_issue_body_exempt_plan_still_gaps(self):
        # owner ruling 2026-07-02 (#45): a staged issue-body.md carries the raw
        # publishable body — exempt from PLANS-01..06. The exemption is
        # filename-scoped: a frontmatter-less plan.md in the same slug dir gaps.
        def mutate(repo):
            _write(
                os.path.join(repo, "_meta", "plans", "slug", "issue-body.md"),
                "## Problem\n\nraw body, no frontmatter\n",
            )
            _write(
                os.path.join(repo, "_meta", "plans", "slug", "plan.md"),
                "# plan without frontmatter\n",
            )

        expected = {f"PLANS-0{i}" for i in range(1, 7)}
        rows = self._run_variant(mutate, expected)
        for rid in sorted(expected):
            self.assertIn("plan.md", rows[rid][1])
            self.assertNotIn("issue-body.md", rows[rid][1])

    def test_inline_hook_flagged(self):
        def mutate(repo):
            _write(
                os.path.join(repo, ".claude", "settings.json"),
                json.dumps(
                    {
                        "hooks": {
                            "Stop": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "echo done && say finished",
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ),
            )

        rows = self._run_variant(mutate, {"HOOK-01"})
        self.assertIn("inline hook command", rows["HOOK-01"][1])

    def test_commands_dir_is_migration_debt_wording(self):
        def mutate(repo):
            os.makedirs(os.path.join(repo, ".claude", "commands"))

        rows = self._run_variant(mutate, {"CLAUDE-07"})
        self.assertIn("migration debt", rows["CLAUDE-07"][1])

    # ── MEM matrix (memory-taxonomy regression fixtures) ──
    def test_mem_no_memory_dir(self):
        # no memory dir fails MEM-01 (+ MEM-02 file, CLAUDE-03 layout); MEM-04 N/A
        self._run_variant(
            lambda repo: shutil.rmtree(os.path.join(repo, ".claude", "memory")),
            {"CLAUDE-03", "MEM-01", "MEM-02"},
            expect_na={"MEM-04"},
        )

    def test_mem_dir_broadly_gitignored_fails_mem03_only(self):
        def mutate(repo):
            with open(os.path.join(repo, ".gitignore"), "a", encoding="utf-8") as fh:
                fh.write(".claude/\n")  # broad ignore, no negation

        # MEM-03 (probe ignored) + the meta-standard's own .claude tracking rows
        self._run_variant(mutate, {"MEM-03", "IGNORE-11", "IGNORE-12"})

    def test_mem_files_without_index_fail_mem02(self):
        def mutate(repo):
            os.remove(os.path.join(repo, ".claude", "memory", "MEMORY.md"))

        rows = self._run_variant(mutate, {"MEM-02"}, expect_na={"MEM-04"})
        self.assertIn("index absent", rows["MEM-04"][1])

    def test_mem_dangling_index_line_fails_mem04(self):
        def mutate(repo):
            with open(
                os.path.join(repo, ".claude", "memory", "MEMORY.md"),
                "a",
                encoding="utf-8",
            ) as fh:
                fh.write("- [Gone](gone-topic.md) — dangling\n")

        rows = self._run_variant(mutate, {"MEM-04"})
        self.assertIn("gone-topic.md", rows["MEM-04"][1])


class ManifestVariance(unittest.TestCase):
    """TC-005 + TC-006: knobs are checked, not just excused; malformed aborts."""

    MANIFEST = (
        "default_branch: dev\n"
        "required_folders:\n  - notebooks/\n"
        "required_files:\n  - justfile\n"
    )

    def test_extras_checked_and_no_false_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_conformant_repo(os.path.realpath(os.path.join(tmp, "repo")))
            _write(os.path.join(repo, "_meta", "mise-en-place.yml"), self.MANIFEST)
            os.makedirs(os.path.join(repo, "notebooks"))
            _write(os.path.join(repo, "justfile"), "default:\n")
            r = assert_read_only(self, repo)
            rows = parse_rows(r.stdout)
            self.assertEqual(rows["VAR-01"][0], "PASS")
            self.assertEqual(rows["VAR-02"][0], "PASS")
            self.assertIn("default_branch=dev", r.stdout)
            self.assertNotIn(" GAP ", r.stdout.replace("| GAP", " GAP "))
            # run 2: remove the extra folder — the manifest knob must now report GAP
            os.rmdir(os.path.join(repo, "notebooks"))
            rows2 = parse_rows(run_audit(repo).stdout)
            self.assertEqual(rows2["VAR-01"][0], "GAP")
            self.assertIn("notebooks", rows2["VAR-01"][1])
            self.assertEqual(rows2["VAR-02"][0], "PASS")

    def test_malformed_manifest_aborts_without_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_conformant_repo(os.path.realpath(os.path.join(tmp, "repo")))
            _write(
                os.path.join(repo, "_meta", "mise-en-place.yml"),
                "default_branch dev\n",
            )
            status_before, hash_before = tree_state(repo)
            r = run_audit(repo)
            self.assertEqual(r.returncode, 2)
            self.assertIn("malformed manifest", r.stderr)
            self.assertEqual(r.stdout, "", "no partial table on error")
            self.assertEqual(tree_state(repo), (status_before, hash_before))


class ErrorPaths(unittest.TestCase):
    """TC-007 + TC-008 + exit-code contract."""

    def test_broken_plugin_root_names_missing_checklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_conformant_repo(os.path.realpath(os.path.join(tmp, "repo")))
            partial = os.path.join(tmp, "partial-plugin")
            # only one of the two standards present → refuse to audit
            shutil.copytree(
                os.path.join(PLUGIN_ROOT, "skills", "repo-meta-structure"),
                os.path.join(partial, "skills", "repo-meta-structure"),
            )
            r = run_audit(repo, plugin_root=partial)
            self.assertEqual(r.returncode, 2)
            self.assertIn("memory-taxonomy", r.stderr)
            self.assertIn("checklist.md", r.stderr)
            self.assertEqual(r.stdout, "")

    def test_no_plugin_root_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_conformant_repo(os.path.realpath(os.path.join(tmp, "repo")))
            env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PLUGIN_ROOT"}
            r = subprocess.run(
                [sys.executable, AUDIT],
                cwd=repo,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("plugin root", r.stderr)

    def test_not_a_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = os.path.realpath(os.path.join(tmp, "plain"))
            os.makedirs(plain)
            r = run_audit(plain)
            self.assertEqual(r.returncode, 2)
            self.assertIn("not a git repository", r.stderr)
            self.assertEqual(r.stdout, "")

    def test_empty_repo_full_table_of_gaps_no_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.realpath(os.path.join(tmp, "empty"))
            subprocess.run(["git", "init", "-q", repo], check=True)
            r = assert_read_only(self, repo)
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = parse_rows(r.stdout)
            checklist_ids = {x["id"] for x in A.load_checklists(PLUGIN_ROOT)}
            self.assertTrue(checklist_ids <= set(rows))
            # every path-exists row is a GAP in an empty repo
            for row in A.load_checklists(PLUGIN_ROOT):
                if row["type"] == "path-exists":
                    self.assertEqual(rows[row["id"]][0], "GAP", row["id"])


if __name__ == "__main__":
    unittest.main()

"""Tests for primitives-core/hooks/config-custody/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only on deny, env-configured knobs) against a
hand-written .claude/atelier.local.md activation file. Stdlib-only; fixtures
build into a tempdir per test, and the environment passed to the subprocess
is built from scratch with only PATH inherited.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

# Sibling helper: `tests/` is on sys.path under `discover -s tests` but not
# under `-t .`, so prime the path the same way the hooks prime `_lib`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worktree_fixture import make_worktree, require_git  # noqa: E402

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "config-custody", "hook.py",
)

_SEQ = itertools.count()


def _session_id():
    return f"custody-session-{next(_SEQ)}"


def _last_log_row(log_path):
    with open(log_path, encoding="utf-8") as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    return json.loads(lines[-1])


class ConfigCustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.log_path = os.path.join(self.tmp.name, "logs", "config-custody.jsonl")
        # Sandbox the partitioned log root for every subprocess in this class.
        # Without it a run that sets no path override resolves the real
        # ~/.local/share/agent-logs and appends synthetic rows to the ledger
        # this machine actually collects.
        self.xdg = os.path.join(self.tmp.name, "xdg")
        self.default_log_path = os.path.join(
            self.xdg, "agent-logs", "claude-code", "atelier", "config-custody.jsonl",
        )

    # -- fixtures ------------------------------------------------------

    def _write_activation(self, mode=None, patterns=None, raw_text=None, project_dir=None):
        project_dir = project_dir or self.cwd
        claude_dir = os.path.join(project_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        path = os.path.join(claude_dir, "atelier.local.md")
        if raw_text is None:
            lines = ["---"]
            if mode is not None:
                lines.append("enforce: {0}".format(mode))
            if patterns:
                lines.append("protected:")
                lines.extend("  - {0}".format(p) for p in patterns)
            lines.append("---")
            raw_text = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw_text)
        return path

    def _payload(self, file_path=None, notebook_path=None, agent_id="agent-1",
                 cwd=None, tool_name="Edit", session_id=None):
        tool_input = {}
        if file_path is not None:
            tool_input["file_path"] = file_path
        if notebook_path is not None:
            tool_input["notebook_path"] = notebook_path
        payload = {
            "session_id": session_id or _session_id(),
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": self.cwd if cwd is None else cwd,
        }
        if agent_id is not None:
            payload["agent_id"] = agent_id
            payload["agent_type"] = "builder"
        return payload

    def _run_hook(self, payload, set_log_env=True, log_path=None, stdin_text=None,
                  project_dir=None, env_extra=None):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # HOME as well as XDG_DATA_HOME: expanduser("~") falls back to the
            # passwd entry when HOME is unset, so unsetting alone does not
            # contain a write.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": self.xdg,
        }
        if project_dir is not None:
            env["CLAUDE_PROJECT_DIR"] = project_dir
        if set_log_env:
            env["ATELIER_CUSTODY_LOG_PATH"] = log_path if log_path is not None else self.log_path
        env.update(env_extra or {})
        stdin_text = json.dumps(payload) if stdin_text is None else stdin_text
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def _assert_denied(self, result):
        self.assertEqual(result.returncode, 0)
        self.assertNotEqual(result.stdout.strip(), "", "hook stayed silent, expected a deny")
        hso = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "deny")
        return hso

    def _assert_silent(self, result):
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    # -- tests -----------------------------------------------------------

    def test_strict_subagent_protected_path_denies(self):
        self._write_activation(mode="strict", patterns=["Makefile"])
        hso = self._assert_denied(self._run_hook(self._payload(file_path="Makefile")))
        self.assertIn("protected pattern 'Makefile'", hso["permissionDecisionReason"])

    def test_strict_main_session_never_restricted(self):
        self._write_activation(mode="strict", patterns=["Makefile"])
        payload = self._payload(file_path="Makefile", agent_id=None)
        self._assert_silent(self._run_hook(payload))

    def test_advisory_logs_without_denying(self):
        self._write_activation(mode="advisory", patterns=["Makefile"])
        log_path = os.path.join(self.tmp.name, "logs", "advisory.jsonl")
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile"), log_path=log_path))
        row = _last_log_row(log_path)
        self.assertFalse(row["denied"])
        self.assertEqual(row["mode"], "advisory")

    def test_off_and_absent_activation_are_both_silent(self):
        # (a) explicit enforce: off
        self._write_activation(mode="off", patterns=["Makefile"])
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile")))

        # (b) activation file absent entirely (fresh project dir)
        bare_cwd = os.path.join(self.tmp.name, "bare")
        os.makedirs(bare_cwd, exist_ok=True)
        payload = self._payload(file_path="Makefile", cwd=bare_cwd)
        self._assert_silent(self._run_hook(payload))

    def test_garbage_activation_file_fails_open(self):
        self._write_activation(raw_text="not even yaml, just noise\n")
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile")))

    def test_glob_star_crosses_separators(self):
        self._write_activation(mode="strict", patterns=["configs/*"])
        payload = self._payload(file_path="configs/deep/nested/app.yaml")
        self._assert_denied(self._run_hook(payload))

    def test_absolute_path_vs_relative_pattern_and_outside_project(self):
        self._write_activation(mode="strict", patterns=["Makefile"])
        abs_path = os.path.join(self.cwd, "Makefile")
        self._assert_denied(self._run_hook(self._payload(file_path=abs_path)))
        self._assert_silent(self._run_hook(self._payload(file_path="/etc/hosts")))

    def test_notebook_edit_notebook_path_protected(self):
        self._write_activation(mode="strict", patterns=["notebooks/*"])
        payload = self._payload(
            notebook_path="notebooks/analysis.ipynb", tool_name="NotebookEdit",
        )
        self._assert_denied(self._run_hook(payload))

    def test_malformed_stdin_fails_open(self):
        result = self._run_hook(None, set_log_env=False, stdin_text="not json")
        self._assert_silent(result)

    def test_no_stray_writes_outside_configured_log_path(self):
        """With no path override the ledger goes to the partitioned root, and
        the project tree keeps exactly the file the test put there."""
        activation_path = self._write_activation(mode="strict", patterns=["Makefile"])
        result = self._run_hook(self._payload(file_path="Makefile"), set_log_env=False)
        self._assert_denied(result)

        found = set()
        for root, _dirs, files in os.walk(self.cwd):
            for name in files:
                found.add(os.path.relpath(os.path.join(root, name), self.cwd))
        self.assertEqual(found, {os.path.relpath(activation_path, self.cwd)})
        self.assertTrue(
            os.path.isfile(self.default_log_path),
            "row did not land in the partitioned root",
        )

    def test_default_row_carries_the_identity_envelope(self):
        """Envelope is asserted on a real written row, not on a literal."""
        self._write_activation(mode="strict", patterns=["Makefile"])
        self._assert_denied(
            self._run_hook(self._payload(file_path="Makefile"), set_log_env=False)
        )
        row = _last_log_row(self.default_log_path)
        self.assertEqual(row["stream"], "config-custody")
        self.assertEqual(row["plugin"], "atelier")
        self.assertEqual(row["harness"], "claude-code")
        self.assertEqual(row["v"], 1)
        self.assertEqual(row["project"], self.cwd)
        self.assertRegex(row["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")
        # payload survives alongside the envelope
        self.assertEqual(row["path"], "Makefile")
        self.assertTrue(row["denied"])


    # -- worktree resolution ---------------------------------------------

    def test_linked_worktree_follows_main_checkout_activation(self):
        """A subagent working in a linked worktree is still bound by the
        custody file that lives, gitignored, in the main checkout."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        main_dir, worktree_dir = make_worktree(
            base,
            files={".claude/atelier.local.md": "---\nenforce: strict\nprotected:\n  - Makefile\n---\n"},
        )
        self.assertFalse(
            os.path.exists(os.path.join(worktree_dir, ".claude", "atelier.local.md")),
            "fixture leaked the activation file into the worktree",
        )

        payload = self._payload(file_path="Makefile", cwd=worktree_dir)
        hso = self._assert_denied(self._run_hook(payload))
        self.assertIn("protected pattern 'Makefile'", hso["permissionDecisionReason"])

        # Control: resolution imports the patterns, not a blanket denial.
        self._assert_silent(
            self._run_hook(self._payload(file_path="notes.md", cwd=worktree_dir))
        )
        # Control: the main checkout itself is unaffected.
        self._assert_denied(
            self._run_hook(self._payload(file_path="Makefile", cwd=main_dir))
        )

    def test_worktrees_own_tracked_activation_wins(self):
        """Resolution is lazy: a tracked activation file is read at the
        version committed on the worktree's branch, not at the main
        checkout's working-tree version."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        main_dir, worktree_dir = make_worktree(
            base,
            tracked={".claude/atelier.local.md": "---\nenforce: off\nprotected:\n  - Makefile\n---\n"},
        )
        # Main checkout arms custody after the commit the worktree branched from.
        self._write_activation(mode="strict", patterns=["Makefile"], project_dir=main_dir)

        self._assert_denied(self._run_hook(self._payload(file_path="Makefile", cwd=main_dir)))
        self._assert_silent(
            self._run_hook(self._payload(file_path="Makefile", cwd=worktree_dir))
        )

    def test_non_worktree_cwd_without_git_is_unchanged(self):
        """A plain directory that is not a repo resolves to itself: absent
        activation file stays absent, no deny, no crash."""
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain, exist_ok=True)
        self._assert_silent(self._run_hook(self._payload(file_path="Makefile", cwd=plain)))

    # -- jurisdiction inside a worktree ------------------------------------
    #
    # Claude Code sets CLAUDE_PROJECT_DIR on the HOOK process even when the
    # worker's own shell has none, and it points at the MAIN checkout. So the
    # activation file is found at the direct path and the worktree fallback
    # never fires — while the edited path relativizes to
    # `.claude/worktrees/agent-<id>/Makefile`, which no project-relative
    # pattern can match. Policy comes from the main checkout; jurisdiction has
    # to be the tree the edited file actually lives in.

    def _repo(self, patterns=("Makefile",)):
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        main_dir, _worktree_dir = make_worktree(base)
        self._write_activation(mode="strict", patterns=list(patterns),
                               project_dir=main_dir)
        return main_dir

    def _add_worktree(self, main_dir, relpath, branch):
        """A second linked worktree, at a path this test chooses.

        Local rather than in `worktree_fixture`, which fixes the layout: these
        cases turn on WHERE the worktree sits relative to the project root.
        """
        path = os.path.join(main_dir, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        proc = subprocess.run(
            ["git", "worktree", "add", "-q", path, "-b", branch],
            cwd=main_dir, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.isfile(os.path.join(path, ".git")),
                        "a linked worktree's .git must be a file")
        return path

    def test_edit_inside_a_worktree_is_judged_against_the_worktree_root(self):
        """The live defect: with the project dir anchored on the main
        checkout, every path a worktree-isolated worker touches relativizes
        to `.claude/worktrees/...`, so no `protected:` pattern can match."""
        main_dir = self._repo()
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-x", "wt-x")

        payload = self._payload(
            file_path=os.path.join(worktree, "Makefile"), cwd=worktree,
        )
        hso = self._assert_denied(self._run_hook(payload, project_dir=main_dir))
        self.assertIn("protected pattern 'Makefile'", hso["permissionDecisionReason"])
        self.assertIn("'Makefile'", hso["permissionDecisionReason"])

    def test_a_worktree_at_a_non_default_location_is_found_by_its_git_file(self):
        """Found by walking to the first `.git` that is a FILE, never by a
        hardcoded `.claude/worktrees/` path shape."""
        main_dir = self._repo()
        worktree = self._add_worktree(main_dir, "tools/scratch-tree", "wt-scratch")

        payload = self._payload(
            file_path=os.path.join(worktree, "Makefile"), cwd=worktree,
        )
        self._assert_denied(self._run_hook(payload, project_dir=main_dir))

    def test_a_nested_ordinary_repo_is_not_a_jurisdiction(self):
        """Only a LINKED worktree relocates jurisdiction. A vendored sub-repo
        has a `.git` DIRECTORY, and treating it as a worktree root would
        re-anchor `vendor/thing/Makefile` to `Makefile` and deny it."""
        main_dir = self._repo()
        nested = os.path.join(main_dir, "vendor", "thing")
        os.makedirs(nested, exist_ok=True)
        proc = subprocess.run(["git", "init", "-q", "."], cwd=nested,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(os.path.isdir(os.path.join(nested, ".git")))

        payload = self._payload(file_path=os.path.join(nested, "Makefile"),
                                cwd=nested)
        self._assert_silent(self._run_hook(payload, project_dir=main_dir))

    def test_an_edit_in_the_main_checkout_is_unchanged(self):
        main_dir = self._repo()
        payload = self._payload(file_path=os.path.join(main_dir, "Makefile"),
                                cwd=main_dir)
        self._assert_denied(self._run_hook(payload, project_dir=main_dir))

    def test_patterns_stay_project_relative_not_basename_matches(self):
        """`Makefile` must not start matching `docs/Makefile` — in the main
        checkout or inside a worktree."""
        main_dir = self._repo()
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-y", "wt-y")
        os.makedirs(os.path.join(main_dir, "docs"), exist_ok=True)
        os.makedirs(os.path.join(worktree, "docs"), exist_ok=True)

        for label, root in (("main checkout", main_dir), ("worktree", worktree)):
            with self.subTest(label):
                payload = self._payload(
                    file_path=os.path.join(root, "docs", "Makefile"), cwd=root,
                )
                self._assert_silent(self._run_hook(payload, project_dir=main_dir))

    # -- whose policy governs ----------------------------------------------

    def _commit_in(self, tree, text):
        """Commit an activation file on the branch checked out in `tree`."""
        relpath = os.path.join(".claude", "atelier.local.md")
        path = os.path.join(tree, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        identity = ["-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false"]
        for args in (["add", "--", relpath], identity + ["commit", "-q", "-m", "policy"]):
            proc = subprocess.run(["git"] + args, cwd=tree, capture_output=True,
                                  text=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
        clean = subprocess.run(["git", "status", "--porcelain"], cwd=tree,
                               capture_output=True, text=True, timeout=60)
        self.assertEqual(clean.stdout, "", "clean tree: on-disk is the committed version")
        return path

    def test_a_worktrees_committed_activation_governs_that_worktree(self):
        """Production shape: CLAUDE_PROJECT_DIR names the MAIN checkout while the
        edited file lives in a linked worktree whose committed copy drops a
        pattern the main checkout still lists."""
        main_dir = self._repo(patterns=("Makefile", "docs/*"))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-z", "wt-z")
        self._commit_in(worktree, "---\nenforce: strict\nprotected:\n  - docs/*\n---\n")

        self._assert_silent(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))
        # Control: the worktree's own patterns are read, not a blanket exemption.
        self._assert_denied(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "docs", "guide.md"),
                          cwd=worktree),
            project_dir=main_dir,
        ))
        # Control: the main checkout stays governed by its own copy.
        self._assert_denied(self._run_hook(
            self._payload(file_path=os.path.join(main_dir, "Makefile"), cwd=main_dir),
            project_dir=main_dir,
        ))

    def test_the_edited_files_worktree_outranks_the_payload_cwds(self):
        """Two worktrees, opposite policies: the tree the edited file lives in
        decides, whichever tree the call came from."""
        main_dir = self._repo(patterns=("Makefile",))
        open_tree = self._add_worktree(main_dir, ".claude/worktrees/agent-a", "wt-a")
        strict_tree = self._add_worktree(main_dir, ".claude/worktrees/agent-b", "wt-b")
        self._commit_in(open_tree, "---\nenforce: off\n---\n")
        self._commit_in(strict_tree,
                        "---\nenforce: strict\nprotected:\n  - Makefile\n---\n")

        with self.subTest("edit in the strict tree, called from the open one"):
            self._assert_denied(self._run_hook(
                self._payload(file_path=os.path.join(strict_tree, "Makefile"),
                              cwd=open_tree),
                project_dir=main_dir,
            ))
        with self.subTest("edit in the open tree, called from the strict one"):
            self._assert_silent(self._run_hook(
                self._payload(file_path=os.path.join(open_tree, "Makefile"),
                              cwd=strict_tree),
                project_dir=main_dir,
            ))

    def test_a_worktree_policy_never_reaches_the_main_checkout(self):
        """`enforce: off` committed in a worktree un-governs that worktree —
        intended — and nothing else: an absolute edit aimed at the main checkout
        is still judged by the main checkout's copy."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-m", "wt-m")
        self._commit_in(worktree, "---\nenforce: off\n---\n")

        self._assert_silent(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))
        self._assert_denied(self._run_hook(
            self._payload(file_path=os.path.join(main_dir, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))

    def test_an_uncommitted_edit_to_the_worktrees_copy_has_no_effect(self):
        """The committed version governs. Editing the activation file in your
        own worktree is a permitted `Edit` on most boards, and it must not be a
        way to stand custody down for the rest of the session."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-d", "wt-d")
        self._commit_in(worktree, "---\nenforce: strict\nprotected:\n  - Makefile\n---\n")
        self._write_activation(mode="off", project_dir=worktree)

        self._assert_denied(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))

    def test_the_committed_copy_governs_when_the_worktree_is_the_project_dir(self):
        """`CLAUDE_PROJECT_DIR` does not always name the main checkout: it can
        name the worktree, and with it unset the payload `cwd` does. The
        committed copy has to govern in all three shapes."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-p", "wt-p")
        self._commit_in(worktree, "---\nenforce: strict\nprotected:\n  - Makefile\n---\n")
        self._write_activation(mode="off", project_dir=worktree)
        edit = self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree)

        with self.subTest("the project dir is the worktree"):
            self._assert_denied(self._run_hook(edit, project_dir=worktree))
        with self.subTest("no project dir, so the payload cwd is the worktree"):
            self._assert_denied(self._run_hook(edit))
        with self.subTest("jurisdiction is still that tree's root, not a basename"):
            self._assert_silent(self._run_hook(
                self._payload(file_path=os.path.join(worktree, "docs", "Makefile"),
                              cwd=worktree),
                project_dir=worktree,
            ))

    def test_an_oversized_committed_copy_does_not_select_another_policy(self):
        """A selected blob past the size ceiling is invalid; never switch policies."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-big", "wt-big")
        self._commit_in(worktree, "---\nenforce: strict\nprotected:\n  - docs/*\n---\n"
                        + "x" * (256 * 1024))

        self._assert_silent(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))
        self._assert_silent(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "docs", "guide.md"),
                          cwd=worktree),
            project_dir=main_dir,
        ))

    def test_a_committed_copy_deleted_from_disk_still_governs(self):
        """Removing a policy file cannot switch custody away from HEAD's policy."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-g", "wt-g")
        self._commit_in(worktree, "---\nenforce: off\n---\n")
        os.remove(os.path.join(worktree, ".claude", "atelier.local.md"))

        self._assert_silent(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))

    def test_an_empty_committed_copy_disarms_that_worktree(self):
        """Empty or unparseable means "off" for that tree — the same tolerant
        rule the on-disk reader follows, and it is reached only by committing."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-e", "wt-e")
        self._commit_in(worktree, "")

        self._assert_silent(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))

    def test_an_untracked_worktree_copy_does_not_govern(self):
        """AC#1 promises the *tracked* copy. A file that exists only on disk is
        not on the branch, so the main checkout's policy still applies."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-u", "wt-u")
        self._write_activation(mode="off", project_dir=worktree)

        self._assert_denied(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir,
        ))

    def test_a_relative_edit_is_judged_by_one_tree_for_both_questions(self):
        """A relative tool path anchors on the project dir, so the project
        dir's policy is what judges it: policy and jurisdiction resolve to the
        same tree by construction, whatever the payload cwd says."""
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-r", "wt-r")
        self._commit_in(worktree, "---\nenforce: strict\nprotected:\n  - docs/*\n---\n")

        self._assert_denied(self._run_hook(
            self._payload(file_path="Makefile", cwd=worktree), project_dir=main_dir))
        self._assert_silent(self._run_hook(
            self._payload(file_path="docs/guide.md", cwd=worktree), project_dir=main_dir))

    def test_a_foreign_trees_activation_file_never_arms_the_hook(self):
        """Out of jurisdiction is decided before policy is read, so an edit
        outside the project cannot import a stranger's `protected:` list."""
        main_dir = self._repo(patterns=("Makefile",))
        foreign = os.path.join(self.tmp.name, "foreign")
        self._write_activation(mode="strict", patterns=["Makefile", "*"],
                               project_dir=foreign)
        self._assert_silent(self._run_hook(
            self._payload(file_path=os.path.join(foreign, "Makefile"), cwd=foreign),
            project_dir=main_dir,
        ))

    def test_the_activation_override_outranks_every_tree(self):
        main_dir = self._repo(patterns=("Makefile",))
        worktree = self._add_worktree(main_dir, ".claude/worktrees/agent-o", "wt-o")
        self._commit_in(worktree, "---\nenforce: off\n---\n")
        override = os.path.join(self.tmp.name, "override.md")
        with open(override, "w", encoding="utf-8") as fh:
            fh.write("---\nenforce: strict\nprotected:\n  - Makefile\n---\n")

        self._assert_denied(self._run_hook(
            self._payload(file_path=os.path.join(worktree, "Makefile"), cwd=worktree),
            project_dir=main_dir, env_extra={"ATELIER_ACTIVATION_FILE": override},
        ))


if __name__ == "__main__":
    unittest.main()

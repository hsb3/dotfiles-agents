"""Tests for .claude/hooks/no-main-checkout/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a JSON
line on stdout only on deny) against tempdir fixtures. Stdlib-only; the
environment passed to the subprocess is built from scratch with only PATH
inherited, so the host's own CLAUDE_PROJECT_DIR never leaks in.

The guarded repo is a fixture directory, not this tree: a bare `.git` entry is
enough for the hook's walk-up fallback, and no git binary is invoked. The
fallback case runs a COPY of the hook planted at its real relative depth inside
the fixture (`<root>/.claude/hooks/no-main-checkout/hook.py`), which is what
makes the "resolve the root from the hook's own location" path testable without
depending on where this checkout lives.

Directory awareness is the thing under test (card twhq): the same command text
must deny inside the guarded repo and stay silent outside it, with `cd` and
`git -C` moving the effective directory, and an unresolvable directory failing
safe toward "inside".
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", ".claude", "hooks",
    "no-main-checkout", "hook.py",
)

# Fragments of the deny text that must survive the fix (AC#2).
REASON_HEAD = "Blocked: `git checkout` targeting `main`"
REASON_BODY = "`main` is the CI-published distribution branch"


class NoMainCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(self.repo, ".git"), exist_ok=True)
        # A sibling whose path is a string prefix of nothing but shares the stem:
        # `/…/repo-other` must not read as "inside /…/repo".
        self.sibling = os.path.join(self.tmp.name, "repo-other")
        os.makedirs(os.path.join(self.sibling, ".git"), exist_ok=True)
        self.outside = os.path.join(self.tmp.name, "other-repo")
        os.makedirs(os.path.join(self.outside, ".git"), exist_ok=True)

    # -- harness -------------------------------------------------------

    def _run(self, command, cwd=None, root=None, hook=HOOK_PATH, run_in=None):
        """Feed one PreToolUse payload to the hook; return its parsed output or None."""
        payload = {"tool_input": {"command": command}}
        if cwd is not None:
            payload["cwd"] = cwd
        env = {"PATH": os.environ.get("PATH", "")}
        if root is not None:
            env["CLAUDE_PROJECT_DIR"] = root
        proc = subprocess.run(
            [sys.executable, hook],
            input=json.dumps(payload), text=True, capture_output=True,
            env=env, cwd=run_in or self.tmp.name, timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout.strip()
        return json.loads(out) if out else None

    def _assert_denied(self, out, head=REASON_HEAD):
        self.assertIsNotNone(out, "expected a deny, got silence")
        block = out["hookSpecificOutput"]
        self.assertEqual(block["permissionDecision"], "deny")
        self.assertIn(head, block["permissionDecisionReason"])
        self.assertIn(REASON_BODY, block["permissionDecisionReason"])

    def _plant_copy(self):
        """Copy the hook into the fixture repo at its real depth; return its path."""
        dest = os.path.join(
            self.repo, ".claude", "hooks", "no-main-checkout", "hook.py")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(HOOK_PATH, dest)
        return dest

    # -- the reported bug (AC#1, AC#3) ---------------------------------

    def test_checkout_main_outside_the_guarded_repo_is_allowed(self):
        self.assertIsNone(
            self._run("git checkout main", cwd=self.outside, root=self.repo))

    def test_cd_out_then_checkout_main_is_allowed(self):
        self.assertIsNone(self._run(
            f"cd {self.outside} && git checkout main",
            cwd=self.repo, root=self.repo))

    def test_sibling_directory_sharing_the_root_prefix_is_outside(self):
        self.assertIsNone(
            self._run("git checkout main", cwd=self.sibling, root=self.repo))

    def test_git_dash_c_pointing_outside_is_allowed(self):
        self.assertIsNone(self._run(
            f"git -C {self.outside} checkout main", cwd=self.repo, root=self.repo))

    # -- still refused inside (AC#2) -----------------------------------

    def test_checkout_main_inside_the_guarded_repo_is_refused(self):
        self._assert_denied(
            self._run("git checkout main", cwd=self.repo, root=self.repo))

    def test_switch_main_inside_the_guarded_repo_is_refused(self):
        self._assert_denied(
            self._run("git switch main", cwd=self.repo, root=self.repo),
            head="Blocked: `git switch` targeting `main`")

    def test_cd_back_into_the_guarded_repo_is_refused(self):
        self._assert_denied(self._run(
            f"cd {self.repo} && git checkout main",
            cwd=self.outside, root=self.repo))

    def test_git_dash_c_pointing_into_the_guarded_repo_is_refused(self):
        self._assert_denied(self._run(
            f"git -C {self.repo} checkout main", cwd=self.outside, root=self.repo))

    def test_git_dash_c_override_applies_to_that_invocation_only(self):
        # The `-C` hop must not leak into the next segment's effective directory.
        self._assert_denied(self._run(
            f"git -C {self.outside} status && git checkout main",
            cwd=self.repo, root=self.repo))

    def test_a_linked_worktree_of_this_repo_counts_as_inside(self):
        wt = os.path.join(self.repo, ".claude", "worktrees", "agent-1")
        os.makedirs(wt, exist_ok=True)
        self._assert_denied(self._run("git checkout main", cwd=wt, root=self.repo))

    # -- unresolvable directories fail safe toward "inside" ------------

    def test_unexpanded_variable_in_cd_target_is_treated_as_inside(self):
        self._assert_denied(self._run(
            "cd $SOME_DIR && git checkout main", cwd=self.outside, root=self.repo))

    def test_tilde_in_cd_target_is_treated_as_inside(self):
        self._assert_denied(self._run(
            "cd ~/somewhere && git checkout main", cwd=self.outside, root=self.repo))

    def test_nonexistent_relative_cd_target_is_treated_as_inside(self):
        self._assert_denied(self._run(
            "cd nope/deeper && git checkout main", cwd=self.outside, root=self.repo))

    def test_bare_cd_is_treated_as_inside(self):
        self._assert_denied(self._run(
            "cd && git checkout main", cwd=self.outside, root=self.repo))

    def test_existing_relative_cd_target_is_resolved(self):
        os.makedirs(os.path.join(self.outside, "sub"), exist_ok=True)
        self.assertIsNone(self._run(
            "cd sub && git checkout main", cwd=self.outside, root=self.repo))

    # -- the guard's existing surface, unchanged (AC#5) ----------------

    def test_worktree_add_against_origin_main_still_passes(self):
        self.assertIsNone(self._run(
            "git worktree add /tmp/x origin/main", cwd=self.repo, root=self.repo))

    def test_show_of_origin_main_path_still_passes(self):
        self.assertIsNone(self._run(
            "git show origin/main:AGENTS.md", cwd=self.repo, root=self.repo))

    def test_branch_main_inside_the_guarded_repo_is_still_refused(self):
        self._assert_denied(
            self._run("git branch main", cwd=self.repo, root=self.repo),
            head="Blocked: `git branch` creating local `main`")

    def test_branch_delete_main_still_passes(self):
        self.assertIsNone(
            self._run("git branch -D main", cwd=self.repo, root=self.repo))

    def test_branch_main_outside_the_guarded_repo_is_allowed(self):
        self.assertIsNone(
            self._run("git branch main", cwd=self.outside, root=self.repo))

    def test_non_git_command_naming_main_still_passes(self):
        self.assertIsNone(
            self._run("echo checkout main", cwd=self.repo, root=self.repo))

    # -- root and cwd resolution fallbacks ------------------------------

    def test_root_falls_back_to_the_hooks_own_repo_when_env_is_unset(self):
        hook = self._plant_copy()
        self._assert_denied(self._run("git checkout main", cwd=self.repo, hook=hook))
        self.assertIsNone(self._run("git checkout main", cwd=self.outside, hook=hook))

    def test_cwd_falls_back_to_the_process_directory_when_absent(self):
        self._assert_denied(
            self._run("git checkout main", root=self.repo, run_in=self.repo))
        self.assertIsNone(
            self._run("git checkout main", root=self.repo, run_in=self.outside))

    # -- fail-open invariant -------------------------------------------

    def test_malformed_payload_is_silent_and_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, HOOK_PATH], input="not json", text=True,
            capture_output=True, env={"PATH": os.environ.get("PATH", "")},
            cwd=self.tmp.name, timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()

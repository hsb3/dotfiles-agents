"""Cross-worktree edits: the repo's own hooks are allow-or-deny, never a silent no-op.

Two W1-C builders reported that an Edit aimed at the dispatcher's worktree
"reported success and applied nothing". A live probe on Claude Code 2.1.263
(2026-09-07) could not reproduce that: the harness refuses the call loudly with
a `tool_use_error` naming the agent's worktree, and nothing is written on
either side. The trap that most likely produced the report is a RELATIVE
`file_path`, which resolves against the agent's own worktree and therefore
succeeds somewhere the dispatcher never looks (`docs/gotchas.md`, "Method").

The harness is not ours. What is ours is the pair of PreToolUse hooks in the
edit path, and this module pins their side of the invariant against the day the
harness does go quiet: for an Edit or Write from nested worktree B aimed at a
path under dispatcher worktree A, a repo-owned hook emits either NOTHING (allow)
or a visible `permissionDecision: deny` carrying a reason. Never a silent
suppression, and never an `updatedInput` rewrite. If a silent no-op is ever seen
again, these tests are the evidence that it did not come from here.

The layout matches the measured one: a linked worktree A, and B created from
inside A at `A/.claude/worktrees/agent-<id>`. `CLAUDE_PROJECT_DIR` is passed
empty by default, which is what a nested worktree actually saw.
"""

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

HOOKS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "primitives-core", "hooks",
)
CUSTODY_HOOK = os.path.join(HOOKS_DIR, "config-custody", "hook.py")
ISOLATION_HOOK = os.path.join(HOOKS_DIR, "worktree-isolation", "hook.py")

# Both hooks armed, as this repo arms them: an isolation hook that is inert
# would pass its test below for the wrong reason.
ACTIVATION = """---
enforce: strict
protected:
  - docs/*
isolate: writers
---
"""

TARGET = os.path.join("docs", "target.md")


class NestedWorktreeEditTests(unittest.TestCase):
    def setUp(self):
        require_git()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.main_dir, self.tree_a = make_worktree(
            self.tmp.name,
            tracked={
                os.path.join(".claude", "atelier.local.md"): ACTIVATION,
                TARGET: "original\n",
            },
            branch="dispatcher",
        )
        # B is nested under A exactly where the harness puts it, and is created
        # from inside A so its `.git` file points at the shared git dir the same
        # way the measured one did.
        self.tree_b = os.path.join(self.tree_a, ".claude", "worktrees", "agent-b")
        subprocess.run(
            ["git", "worktree", "add", "-q", self.tree_b, "-b", "builder-b"],
            cwd=self.tree_a, capture_output=True, text=True, timeout=60, check=True,
        )

        self.custody_log = os.path.join(self.tmp.name, "logs", "config-custody.jsonl")
        self.isolation_log = os.path.join(self.tmp.name, "logs", "worktree-isolation.jsonl")

    # -- helpers ---------------------------------------------------------

    def _run(self, hook_path, payload, project_dir=""):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # HOME as well as XDG_DATA_HOME: expanduser("~") falls back to the
            # passwd entry when HOME is unset, so unsetting alone does not
            # contain a write.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": os.path.join(self.tmp.name, "xdg"),
            "ATELIER_CUSTODY_LOG_PATH": self.custody_log,
            "WORKTREE_ISOLATION_LOG_PATH": self.isolation_log,
            # Empty by default, not absent: this is what a nested worktree was
            # measured to have, and both hooks then fall back to the payload cwd.
            "CLAUDE_PROJECT_DIR": project_dir,
        }
        return subprocess.run(
            [sys.executable, hook_path],
            input=json.dumps(payload), capture_output=True, text=True,
            env=env, timeout=30,
        )

    def _edit_payload(self, file_path, tool_name="Edit", cwd=None):
        return {
            "session_id": "nested-worktree-session",
            "agent_id": "agent-1",
            "agent_type": "builder",
            "cwd": self.tree_b if cwd is None else cwd,
            "tool_name": tool_name,
            "tool_input": {
                "file_path": file_path,
                "old_string": "original",
                "new_string": "edited",
            },
        }

    def _assert_allow_or_visible_deny(self, result, label):
        """The invariant: nothing, or a deny that carries a reason. Never a rewrite."""
        self.assertEqual(result.returncode, 0, "{0}: exit {1}".format(label, result.returncode))
        if not result.stdout.strip():
            return None
        payload = json.loads(result.stdout)
        hso = payload.get("hookSpecificOutput", {})
        self.assertNotIn("updatedInput", hso, "{0}: rewrote the edit".format(label))
        self.assertEqual(hso.get("permissionDecision"), "deny",
                         "{0}: {1}".format(label, result.stdout))
        self.assertTrue(hso.get("permissionDecisionReason", "").strip(),
                        "{0}: deny carried no reason".format(label))
        return hso

    # -- tests -----------------------------------------------------------

    def test_worktree_isolation_never_touches_an_edit(self):
        """It matches the `Agent` tool; an Edit payload must leave it silent."""
        result = self._run(ISOLATION_HOOK, self._edit_payload(os.path.join(self.tree_a, TARGET)))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self.assertFalse(os.path.exists(self.isolation_log), "wrote a decision row for an Edit")

    def test_config_custody_is_inert_across_the_worktree_boundary(self):
        """A path under A is outside B's jurisdiction, so custody stays silent.

        Pinned as INERT, not deny, and the empty anchor is what makes it so:
        with no `CLAUDE_PROJECT_DIR`, jurisdiction is the payload cwd (B), and a
        path under A relativizes to a `..` prefix — out of jurisdiction. Custody
        governs the tree the agent stands in; the boundary itself is the
        harness's to enforce. Anchored at A instead, custody does reach the same
        edit — and denies it out loud, which the next test pins.
        """
        result = self._run(CUSTODY_HOOK, self._edit_payload(os.path.join(self.tree_a, TARGET)))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        self.assertFalse(os.path.exists(self.custody_log), "logged an out-of-jurisdiction edit")

    def test_config_custody_denies_visibly_when_the_anchor_covers_both_trees(self):
        """Same cross-worktree edit, anchored at A: reachable, and loud when it acts."""
        hso = self._assert_allow_or_visible_deny(
            self._run(CUSTODY_HOOK, self._edit_payload(os.path.join(self.tree_a, TARGET)),
                      project_dir=self.tree_a),
            "custody cross-boundary, anchored at A",
        )
        self.assertIsNotNone(hso, "custody was inert for a protected path it could reach")
        self.assertIn("docs/*", hso["permissionDecisionReason"])

    def test_config_custody_denies_visibly_inside_the_worktree(self):
        """Control for the test above: armed, reachable from B, and loud when it acts."""
        result = self._run(CUSTODY_HOOK, self._edit_payload(os.path.join(self.tree_b, TARGET)))
        hso = self._assert_allow_or_visible_deny(result, "custody in-tree")
        self.assertIsNotNone(hso, "custody was inert for a protected path in its own tree")
        self.assertIn("docs/*", hso["permissionDecisionReason"])
        self.assertIn("docs/target.md", hso["permissionDecisionReason"])

    def test_no_repo_hook_can_silently_swallow_a_cross_worktree_write(self):
        for hook_path in (ISOLATION_HOOK, CUSTODY_HOOK):
            for tool_name in ("Edit", "Write"):
                for target_root in (self.tree_a, self.main_dir):
                    label = "{0} {1} -> {2}".format(
                        os.path.basename(os.path.dirname(hook_path)), tool_name, target_root,
                    )
                    with self.subTest(hook=hook_path, tool=tool_name, target=target_root):
                        result = self._run(hook_path, self._edit_payload(
                            os.path.join(target_root, TARGET), tool_name=tool_name,
                        ))
                        self._assert_allow_or_visible_deny(result, label)
                        self.assertEqual(result.stderr.strip(), "", label)


if __name__ == "__main__":
    unittest.main()

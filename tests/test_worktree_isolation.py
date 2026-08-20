"""Tests for primitives-core/hooks/worktree-isolation/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a JSON
line on stdout only when a dispatch is rewritten) against a hand-written
.claude/atelier.local.md activation file. Stdlib-only; fixtures build into a
tempdir per test, and the environment passed to the subprocess is built from
scratch with only PATH inherited.

The project fixture is a git repo only because the hook stands down outside one
— a bare `.git` directory is enough, so no git binary is invoked.
"""

import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks",
    "worktree-isolation", "hook.py",
)

_SEQ = itertools.count()


def _session_id():
    return f"worktree-isolation-session-{next(_SEQ)}"


class WorktreeIsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(os.path.join(self.cwd, ".git"), exist_ok=True)
        self.xdg = os.path.join(self.tmp.name, "xdg")
        self.log_path = os.path.join(
            self.xdg, "agent-logs", "claude-code", "atelier",
            "worktree-isolation.jsonl",
        )

    # -- fixtures ------------------------------------------------------

    def _write_activation(self, isolate=None, raw_text=None, project_dir=None):
        project_dir = project_dir or self.cwd
        claude_dir = os.path.join(project_dir, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        path = os.path.join(claude_dir, "atelier.local.md")
        if raw_text is None:
            lines = ["---"]
            if isolate is not None:
                lines.append("isolate: {0}".format(isolate))
            lines.append("---")
            raw_text = "\n".join(lines) + "\n"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(raw_text)
        return path

    def _payload(self, cwd=None, tool_name="Agent", tool_input=None):
        if tool_input is None:
            tool_input = {"description": "d", "prompt": "p", "subagent_type": "builder"}
        return {
            "session_id": _session_id(),
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": self.cwd if cwd is None else cwd,
        }

    def _run_hook(self, stdin_text):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # Sandbox the partitioned log root. Without this the hook's own
            # decision rows land in the real ~/.local/share/agent-logs ledger;
            # HOME too, since expanduser("~") falls back to the passwd entry
            # when HOME is merely unset.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": self.xdg,
        }
        return subprocess.run(
            [sys.executable, HOOK_PATH],
            input=stdin_text,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )

    def _assert_silent(self, result):
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def _rewrite(self, payload):
        """Run the hook and return the updatedInput it emitted."""
        result = self._run_hook(json.dumps(payload))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip(), "expected a rewrite, got silence")
        body = json.loads(result.stdout)
        hso = body["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        return body, hso["updatedInput"]

    # -- the rewrite ---------------------------------------------------

    def test_writers_mode_isolates_builder(self):
        self._write_activation(isolate="writers")
        body, updated = self._rewrite(self._payload())
        self.assertEqual(updated["isolation"], "worktree")
        # The rest of the dispatch survives the rewrite untouched.
        self.assertEqual(updated["prompt"], "p")
        self.assertEqual(updated["subagent_type"], "builder")
        self.assertIn("worktree-isolation", body["systemMessage"])

    def test_rewrite_never_denies(self):
        """Forcing isolation is a correction, not a refusal."""
        self._write_activation(isolate="writers")
        body, _ = self._rewrite(self._payload())
        self.assertNotIn("permissionDecision", body.get("hookSpecificOutput", {}))
        self.assertNotIn("decision", body)
        self.assertNotIn("continue", body)

    def test_manager_and_general_purpose_are_writers(self):
        self._write_activation(isolate="writers")
        for agent_type in ("manager", "general-purpose"):
            with self.subTest(agent_type=agent_type):
                payload = self._payload(tool_input={
                    "prompt": "p", "subagent_type": agent_type,
                })
                _, updated = self._rewrite(payload)
                self.assertEqual(updated["isolation"], "worktree")

    def test_plugin_namespaced_type_matches_bare_form(self):
        self._write_activation(isolate="writers")
        payload = self._payload(tool_input={"prompt": "p", "subagent_type": "atelier:builder"})
        _, updated = self._rewrite(payload)
        self.assertEqual(updated["isolation"], "worktree")

    def test_absent_subagent_type_is_treated_as_general_purpose(self):
        """An omitted type resolves to general-purpose, which can write."""
        self._write_activation(isolate="writers")
        _, updated = self._rewrite(self._payload(tool_input={"prompt": "p"}))
        self.assertEqual(updated["isolation"], "worktree")

    # -- read-only roles keep the live working tree --------------------

    def test_read_only_types_are_never_isolated(self):
        self._write_activation(isolate="writers")
        for agent_type in ("scout", "reviewer", "Explore", "Plan", "fork", "atelier:scout"):
            with self.subTest(agent_type=agent_type):
                payload = self._payload(tool_input={
                    "prompt": "p", "subagent_type": agent_type,
                })
                self._assert_silent(self._run_hook(json.dumps(payload)))

    def test_explicit_list_cannot_override_the_never_isolate_set(self):
        """Naming scout in the list must not blind it to uncommitted work."""
        self._write_activation(raw_text="---\nisolate: [scout, builder]\n---\n")
        self._assert_silent(self._run_hook(json.dumps(self._payload(
            tool_input={"prompt": "p", "subagent_type": "scout"},
        ))))
        _, updated = self._rewrite(self._payload(
            tool_input={"prompt": "p", "subagent_type": "builder"},
        ))
        self.assertEqual(updated["isolation"], "worktree")

    # -- activation forms ----------------------------------------------

    def test_block_list_arms_exactly_those_types(self):
        self._write_activation(
            raw_text="---\nenforce: strict\nisolate:\n  - custom-writer\n---\n",
        )
        _, updated = self._rewrite(self._payload(
            tool_input={"prompt": "p", "subagent_type": "custom-writer"},
        ))
        self.assertEqual(updated["isolation"], "worktree")
        # builder is not in the list, so the built-in set is not implied.
        self._assert_silent(self._run_hook(json.dumps(self._payload())))

    def test_quoted_value_with_trailing_comment(self):
        self._write_activation(raw_text='---\nisolate: "writers"  # armed\n---\n')
        _, updated = self._rewrite(self._payload())
        self.assertEqual(updated["isolation"], "worktree")

    def test_inert_activation_forms(self):
        for label, raw in (
            ("absent key", "---\nenforce: strict\n---\n"),
            ("off", "---\nisolate: off\n---\n"),
            ("unknown scalar", "---\nisolate: everything\n---\n"),
            ("empty inline list", "---\nisolate: []\n---\n"),
            ("bare key, no items", "---\nisolate:\n---\n"),
            ("bare key then another key", "---\nisolate:\nenforce: strict\n---\n"),
            ("no frontmatter", "just prose, no fences\n"),
            ("unclosed frontmatter", "---\nisolate: writers\n"),
        ):
            with self.subTest(form=label):
                self._write_activation(raw_text=raw)
                self._assert_silent(self._run_hook(json.dumps(self._payload())))

    def test_activation_absent_is_silent(self):
        bare = os.path.join(self.tmp.name, "bare")
        os.makedirs(os.path.join(bare, ".git"), exist_ok=True)
        self._assert_silent(self._run_hook(json.dumps(self._payload(cwd=bare))))

    # -- the other inert paths -----------------------------------------

    def test_other_tools_are_ignored(self):
        self._write_activation(isolate="writers")
        payload = self._payload(tool_name="Bash", tool_input={"command": "ls"})
        self._assert_silent(self._run_hook(json.dumps(payload)))

    def test_existing_isolation_is_left_alone(self):
        """Including remote, which must not be downgraded to worktree."""
        self._write_activation(isolate="writers")
        for existing in ("worktree", "remote"):
            with self.subTest(isolation=existing):
                payload = self._payload(tool_input={
                    "prompt": "p", "subagent_type": "builder", "isolation": existing,
                })
                self._assert_silent(self._run_hook(json.dumps(payload)))

    def test_cwd_param_blocks_the_rewrite(self):
        """cwd is documented as mutually exclusive with isolation: worktree."""
        self._write_activation(isolate="writers")
        payload = self._payload(tool_input={
            "prompt": "p", "subagent_type": "builder", "cwd": "/somewhere/else",
        })
        self._assert_silent(self._run_hook(json.dumps(payload)))

    def test_non_git_project_is_inert(self):
        """Forcing isolation outside a repo is a hard error, not a no-op."""
        nogit = os.path.join(self.tmp.name, "nogit")
        os.makedirs(nogit, exist_ok=True)
        self._write_activation(isolate="writers", project_dir=nogit)
        self._assert_silent(self._run_hook(json.dumps(self._payload(cwd=nogit))))

    def test_git_file_counts_as_a_repo(self):
        """A worktree or submodule has .git as a file, not a directory."""
        linked = os.path.join(self.tmp.name, "linked")
        os.makedirs(linked, exist_ok=True)
        with open(os.path.join(linked, ".git"), "w", encoding="utf-8") as fh:
            fh.write("gitdir: /elsewhere/.git/worktrees/x\n")
        self._write_activation(isolate="writers", project_dir=linked)
        _, updated = self._rewrite(self._payload(cwd=linked))
        self.assertEqual(updated["isolation"], "worktree")

    def test_git_root_found_from_a_subdirectory(self):
        nested = os.path.join(self.cwd, "packages", "app")
        os.makedirs(nested, exist_ok=True)
        self._write_activation(isolate="writers", project_dir=nested)
        _, updated = self._rewrite(self._payload(cwd=nested))
        self.assertEqual(updated["isolation"], "worktree")

    # -- fail-open ------------------------------------------------------

    def test_malformed_stdin_fails_open_and_writes_nothing_into_the_project(self):
        """Fail-open, no state file, nothing written into the project tree.

        The error row itself goes to the partitioned log root, which is why
        this walks self.cwd and not the whole tempdir: a crash that leaves no
        trace anywhere is the failure mode the ledger exists to end.
        """
        result = self._run_hook("not json")
        self._assert_silent(result)

        found = []
        for root, _dirs, files in os.walk(self.cwd):
            found.extend(os.path.join(root, f) for f in files)
        self.assertEqual(found, [], "hook must write nothing into the project")

        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["reason"], "error")
        self.assertFalse(rows[0]["isolated"])

    # -- ledger ---------------------------------------------------------

    def _rows(self):
        """Rows the hook really wrote, from the sandboxed partitioned root."""
        if not os.path.isfile(self.log_path):
            return []
        with open(self.log_path, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh if ln.strip()]

    def test_rewrite_is_recorded(self):
        """The defect this closes: the hook silently rewrote a dispatch and
        left no record that it had."""
        self._write_activation(isolate="writers")
        self._rewrite(self._payload())

        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["isolated"])
        self.assertEqual(rows[0]["agent_type"], "builder")
        self.assertEqual(rows[0]["stream"], "worktree-isolation")
        self.assertEqual(rows[0]["project"], self.cwd)
        self.assertIsNone(rows[0]["reason"])

    def test_dispatch_left_alone_is_recorded_with_a_reason(self):
        self._write_activation(isolate="writers")
        # scout is read-only: an armed project, deliberately not isolated.
        payload = self._payload(tool_input={"subagent_type": "scout"})
        self._assert_silent(self._run_hook(json.dumps(payload)))

        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["isolated"])
        self.assertEqual(rows[0]["reason"], "agent type not armed")
        self.assertEqual(rows[0]["agent_type"], "scout")

    def test_unactivated_project_writes_no_ledger_at_all(self):
        """An un-adopted hook stays silent rather than opening a ledger the
        project never asked for — the rule config-custody already follows."""
        self._assert_silent(self._run_hook(json.dumps(self._payload())))
        self.assertEqual(self._rows(), [])

    def test_non_dict_payloads_fail_open(self):
        for raw in ("[]", '"str"', "null", ""):
            with self.subTest(payload=raw):
                self._assert_silent(self._run_hook(raw))

    def test_non_dict_tool_input_fails_open(self):
        self._write_activation(isolate="writers")
        payload = self._payload()
        payload["tool_input"] = "not a dict"
        self._assert_silent(self._run_hook(json.dumps(payload)))

    def test_missing_cwd_is_inert(self):
        payload = self._payload()
        del payload["cwd"]
        self._assert_silent(self._run_hook(json.dumps(payload)))

    def test_oversized_activation_file_is_inert(self):
        self._write_activation(
            raw_text="---\nisolate: writers\n---\n" + ("x" * (256 * 1024 + 1)),
        )
        self._assert_silent(self._run_hook(json.dumps(self._payload())))


if __name__ == "__main__":
    unittest.main()

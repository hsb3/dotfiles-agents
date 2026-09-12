"""Tests for primitives-core/hooks/worktree-isolation/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a JSON
line on stdout only when a dispatch is rewritten) against a hand-written
.claude/atelier.local.md activation file. Stdlib-only; fixtures build into a
tempdir per test, and the environment passed to the subprocess is built from
scratch with only PATH inherited.

The project fixture is a git repo only because the hook stands down outside one
— a bare `.git` directory is enough, so no git binary is invoked. The
worktree-resolution tests at the bottom are the exception: they need a real
linked worktree, so they shell out to a real `git` and skip without one.
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
from worktree_fixture import _git, make_worktree, require_git  # noqa: E402

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

    def test_claude_routing_does_not_require_codex_toml_parser(self):
        self._write_activation(isolate="writers")
        result = subprocess.run(
            [sys.executable, "-c", "import runpy,sys; sys.modules['tomllib']=None; "
             "runpy.run_path(sys.argv[1],run_name='__main__')", HOOK_PATH],
            input=json.dumps(self._payload()), capture_output=True, text=True,
            env={"PATH": os.environ.get("PATH", ""), "HOME": self.tmp.name,
                 "XDG_DATA_HOME": self.xdg}, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]
                         ["updatedInput"]["isolation"], "worktree")

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

    # -- worktree resolution -------------------------------------------

    def test_linked_worktree_follows_main_checkout_activation(self):
        """A session running inside a linked worktree still forces isolation
        on the writers the main checkout's activation file named."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        _main_dir, worktree_dir = make_worktree(
            base, files={".claude/atelier.local.md": "---\nisolate: writers\n---\n"},
        )
        _body, updated = self._rewrite(self._payload(cwd=worktree_dir))
        self.assertEqual(updated["isolation"], "worktree")

    def test_worktrees_own_tracked_activation_wins(self):
        """Resolution is lazy: a tracked activation file in the worktree is
        read at its committed version, not replaced by the main checkout's."""
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        main_dir, worktree_dir = make_worktree(
            base, tracked={".claude/atelier.local.md": "---\nisolate: off\n---\n"},
        )
        self._write_activation(isolate="writers", project_dir=main_dir)
        self._assert_silent(self._run_hook(json.dumps(self._payload(cwd=worktree_dir))))

    # -- nesting -------------------------------------------------------
    #
    # A manager that was itself isolated dispatches its writers from inside a
    # linked worktree. Nesting is the intended outcome (see the README), so
    # the rewrite still happens; what the dispatcher gets is the integrate
    # step, at dispatch time rather than at stray-branch-audit time.

    def _armed_worktree(self):
        require_git()
        base = os.path.join(self.tmp.name, "repo")
        os.makedirs(base, exist_ok=True)
        return make_worktree(
            base, files={".claude/atelier.local.md": "---\nisolate: writers\n---\n"},
        )

    def test_nested_dispatch_is_still_isolated_and_names_the_integrate_step(self):
        _main_dir, worktree_dir = self._armed_worktree()
        body, updated = self._rewrite(self._payload(cwd=worktree_dir))
        self.assertEqual(updated["isolation"], "worktree")

        message = body["systemMessage"]
        self.assertIn("NESTED", message)
        # The exact pair the integration test below drives, so the advertised
        # step and the tested one cannot drift apart.
        self.assertIn("git cherry HEAD <branch>", message)
        self.assertIn("git cherry-pick", message)
        self.assertIn("git worktree remove", message)
        self.assertIn("git branch -D", message)
        remove_at = message.index("git worktree remove")
        for requirement in (
            "worker is complete and no longer live",
            "tracked, untracked, and ignored files",
            "merged, patch-equivalent, superseded, or preserved on a reviewed remote branch",
            "preserve uncommitted, untracked, and ignored work plus durable evidence",
        ):
            self.assertLess(message.index(requirement), remove_at)

        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["isolated"])
        self.assertTrue(rows[0]["nested"])

    def test_a_main_checkout_dispatch_message_is_unchanged(self):
        """The non-nested notice must not grow an integrate step it does not
        need — the baseline the nested clause is measured against."""
        self._write_activation(isolate="writers")
        body, _updated = self._rewrite(self._payload())
        self.assertEqual(
            body["systemMessage"],
            "atelier worktree-isolation: 'builder' dispatched with isolation:worktree "
            "(isolate: writers in the selected atelier.local.md). It gets its own checkout, "
            "so uncommitted work in this tree is NOT visible to it.",
        )
        self.assertFalse(self._rows()[0]["nested"])

    def test_a_subdirectory_of_a_main_checkout_is_not_nested(self):
        """`--git-common-dir` answers a relative `../../.git` from a
        subdirectory, so a string test against `.git` calls an ordinary
        subdirectory a worktree and tells the dispatcher to cherry-pick from
        worktrees that do not exist."""
        main_dir, _worktree_dir = self._armed_worktree()
        subdir = os.path.join(main_dir, "scripts", "deep")
        os.makedirs(subdir, exist_ok=True)
        body, _updated = self._rewrite(self._payload(cwd=subdir))
        self.assertNotIn("NESTED", body["systemMessage"])
        self.assertFalse(self._rows()[0]["nested"])

    def test_a_symlinked_path_is_resolved_before_comparing(self):
        """git resolves one side of the comparison already, so an unresolved
        compare mismatches wherever the path runs through a symlink — and a
        mismatch is read as "linked worktree"."""
        main_dir, worktree_dir = self._armed_worktree()
        os.makedirs(os.path.join(main_dir, "scripts"), exist_ok=True)
        links = os.path.join(self.tmp.name, "links")
        os.makedirs(links, exist_ok=True)
        main_link = os.path.join(links, "main")
        worktree_link = os.path.join(links, "worktree")
        os.symlink(main_dir, main_link)
        os.symlink(worktree_dir, worktree_link)

        for label, cwd, expected in (
            ("main subdir via symlink", os.path.join(main_link, "scripts"), False),
            ("worktree via symlink", worktree_link, True),
        ):
            with self.subTest(label):
                self._run_hook(json.dumps(self._payload(cwd=cwd)))
                self.assertEqual(self._rows()[-1]["nested"], expected)

    # -- the integrate step, run for real ------------------------------

    def _integration_fixture(self, branch="worktree-agent-x"):
        """A dispatcher checkout with a worker branch beside it.

        Returns three callables: commit a file as the worker, run the notice's
        integrate step as the dispatcher, and read the dispatcher's commit
        subjects newest-first.
        """
        require_git()
        base = os.path.join(self.tmp.name, "integrate")
        os.makedirs(base, exist_ok=True)
        main_dir, worktree_dir = make_worktree(base, branch=branch)
        # Config lives in the shared git dir, so this covers the worktree too.
        for key, value in (("user.name", "fixture"),
                           ("user.email", "fixture@example.invalid"),
                           ("commit.gpgsign", "false")):
            _git(main_dir, "config", key, value)

        def worker_commit(name):
            with open(os.path.join(worktree_dir, name), "w", encoding="utf-8") as fh:
                fh.write(name)
            _git(worktree_dir, "add", "--", name)
            _git(worktree_dir, "commit", "-q", "-m", "worker " + name)

        def run(*args):
            return subprocess.run(
                ["git"] + list(args),
                cwd=main_dir, capture_output=True, text=True, timeout=60,
            )

        def integrate(target=branch):
            """The two steps the notice hands the dispatcher, as argv.

            No shell: the notice is deliberately two commands a human reads
            between, so a shell string is not the thing under test — and
            running one would test `sh` word-splitting the dispatcher's zsh
            does not do. A failed listing is returned as-is rather than read
            as "nothing to pick", which is the whole reason the `+` lines are
            read before anything is applied.
            """
            listing = run("cherry", "HEAD", target)
            if listing.returncode != 0:
                return listing
            picks = [line.split()[1] for line in listing.stdout.splitlines()
                     if line.startswith("+ ")]
            return run("cherry-pick", *picks) if picks else listing

        def subjects():
            return _git(main_dir, "log", "--format=%s").splitlines()

        return worker_commit, integrate, subjects

    def test_integrate_step_is_safe_to_repeat(self):
        """The defect, measured by hand: the old `git cherry-pick HEAD..<branch>`
        step exits 128 with `error: empty commit set passed` the moment a round
        has nothing new — the range still spans round one's originals (picking
        them changed their SHAs), and cherry-pick's own patch-id filter then
        empties it. What is asserted here is the replacement: reading `git
        cherry` and picking only the `+` SHAs applies each commit exactly once,
        however many rounds a worker reports over."""
        worker_commit, integrate, subjects = self._integration_fixture()

        worker_commit("a.txt")
        worker_commit("b.txt")
        first = integrate()
        self.assertEqual(first.returncode, 0, first.stderr)
        after_first = subjects()
        self.assertEqual(after_first[:2], ["worker b.txt", "worker a.txt"])

        # A round with nothing new: applies nothing, exits 0, no empty-set fatal.
        second = integrate()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(subjects(), after_first)

        # The next round takes exactly what the worker added since, once.
        worker_commit("c.txt")
        third = integrate()
        self.assertEqual(third.returncode, 0, third.stderr)
        self.assertEqual(subjects(), ["worker c.txt"] + after_first)

    def test_a_branch_that_cannot_be_listed_is_not_a_quiet_no_op(self):
        """A stale or mistyped branch name must fail, not report success with
        nothing integrated — the trap in guarding on an empty pick set."""
        worker_commit, integrate, subjects = self._integration_fixture()
        worker_commit("a.txt")
        result = integrate(target="worktree-agent-typo")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(subjects(), ["fixture"])


if __name__ == "__main__":
    unittest.main()

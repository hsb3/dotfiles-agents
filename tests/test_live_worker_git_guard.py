"""Tests for primitives-core/hooks/live-worker-git-guard/hook.py.

Runs the hook as a subprocess (its real invocation shape: JSON on stdin, a
JSON line on stdout only on deny/override, env-configured ledger paths)
against a fixture that mirrors Claude Code's real on-disk layout:

    <projects>/<slug>/<session_id>.jsonl                            parent transcript
    <projects>/<slug>/<session_id>/subagents/agent-<id>.meta.json   sidecar
    <projects>/<slug>/<session_id>/subagents/agent-<id>.jsonl       subagent transcript

The pending set is the same one subagent-telemetry computes for its stall
rows: sidecars present minus the agent_ids the delegation ledger has already
settled. Stdlib-only; fixtures build into a tempdir per test, and the
subprocess environment is built from scratch with only PATH inherited.
"""

import importlib.util
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HOOKS_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "primitives-core", "hooks")
HOOK_PATH = os.path.join(HOOKS_ROOT, "live-worker-git-guard", "hook.py")

sys.path.insert(0, os.path.join(HOOKS_ROOT, "_lib"))
import pending  # noqa: E402  (path must be primed before this import)

# Sibling helper: `tests/` is on sys.path under `discover -s tests` but not
# under `-t .`, so prime the path the same way the hooks prime `_lib`.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worktree_fixture import make_worktree, require_git  # noqa: E402


def _load_hook():
    """The hook as a module, for the tests that read its verb set directly.

    Importing runs only module-level definitions — `main()` is behind the
    `__main__` guard — so nothing decides anything at import time.
    """
    spec = importlib.util.spec_from_file_location("_lwgg_hook", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOOK = _load_hook()

_SEQ = itertools.count()


def _session_id():
    return "git-guard-session-{0}".format(next(_SEQ))


def _read_rows(log_path):
    if not os.path.exists(log_path):
        return []
    with open(log_path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh.read().splitlines() if ln.strip()]


class LiveWorkerGitGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.path.join(self.tmp.name, "cwd")
        os.makedirs(self.cwd, exist_ok=True)
        self.session_id = _session_id()
        self.projects = os.path.join(self.tmp.name, "projects", "-slug")
        self.transcript_path = os.path.join(
            self.projects, "{0}.jsonl".format(self.session_id))
        self.subagents_dir = os.path.join(
            self.projects, self.session_id, "subagents")
        os.makedirs(self.projects, exist_ok=True)
        with open(self.transcript_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "assistant"}) + "\n")
        # The delegation ledger the guard READS (subagent-telemetry writes it)
        # and the guard's OWN ledger. Both sandboxed into the tempdir.
        self.delegation_log = os.path.join(self.tmp.name, "logs", "delegation.jsonl")
        self.guard_log = os.path.join(
            self.tmp.name, "logs", "live-worker-git-guard.jsonl")

    # -- fixtures ------------------------------------------------------

    def _sidecar(self, agent_id, agent_type="atelier:builder",
                 description="Do a bounded slice", worktree_path=None):
        """A started delegation: its sidecar, as Claude Code writes it."""
        os.makedirs(self.subagents_dir, exist_ok=True)
        meta = {
            "agentType": agent_type,
            "description": description,
            "toolUseId": "toolu_{0}".format(agent_id),
            "spawnDepth": 1,
        }
        if worktree_path is not None:
            meta["worktreePath"] = worktree_path
            meta["worktreeBranch"] = "agent/{0}".format(agent_id)
        path = os.path.join(
            self.subagents_dir, "agent-{0}.meta.json".format(agent_id))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(meta))
        return agent_id

    def _settle(self, agent_id):
        """A delegation row in the ledger — the agent stopped."""
        os.makedirs(os.path.dirname(self.delegation_log), exist_ok=True)
        with open(self.delegation_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "v": 1, "plugin": "atelier", "harness": "claude-code",
                "stream": "delegation", "ts": "2026-08-20T15:37:08.666Z",
                "project": self.cwd, "session_id": self.session_id,
                "agent_id": agent_id, "agent_type": "atelier:builder",
                "model": "claude-sonnet-5", "ctx_tokens": 1234,
            }) + "\n")

    def _payload(self, command, tool_name="Bash", transcript_path=None,
                 agent_id=None):
        payload = {
            "session_id": self.session_id,
            "transcript_path": self.transcript_path
            if transcript_path is None else transcript_path,
            "cwd": self.cwd,
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command},
        }
        if agent_id is not None:
            # Present only when the call comes from inside a subagent.
            payload["agent_id"] = agent_id
            payload["agent_type"] = "atelier:manager"
        return payload

    def _run(self, payload, stdin_text=None, extra_env=None):
        env = {
            "PATH": os.environ.get("PATH", ""),
            # HOME as well as XDG_DATA_HOME: expanduser("~") falls back to the
            # passwd entry when HOME is unset, so unsetting alone does not
            # contain a write to the real ~/.local/share/agent-logs ledger.
            "HOME": os.path.join(self.tmp.name, "home"),
            "XDG_DATA_HOME": os.path.join(self.tmp.name, "xdg"),
            "SUBAGENT_TELEMETRY_LOG_PATH": self.delegation_log,
            "LIVE_WORKER_GIT_GUARD_LOG_PATH": self.guard_log,
        }
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            [sys.executable, HOOK_PATH],
            input=json.dumps(payload) if stdin_text is None else stdin_text,
            capture_output=True, text=True, env=env, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def _assert_silent(self, result):
        self.assertEqual(result.stdout.strip(), "", result.stdout)
        self.assertEqual(_read_rows(self.guard_log), [], "silent paths log nothing")
        return result

    def _assert_denied(self, result):
        payload = json.loads(result.stdout)
        hso = payload["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        return hso["permissionDecisionReason"]

    # -- the guard fires on mutating git while a worker is live -----------

    def test_commit_with_one_pending_child_is_denied_and_names_the_agent(self):
        self._sidecar("a1111111111111111", agent_type="atelier:builder",
                      description="Rewrite the roster guard")
        reason = self._assert_denied(
            self._run(self._payload('git commit -m "wip"')))
        self.assertIn("commit", reason)
        self.assertIn("a1111111111111111", reason)
        self.assertIn("atelier:builder", reason)
        self.assertIn("Rewrite the roster guard", reason)

    def test_reason_explains_the_shared_tree_and_the_override_policy(self):
        session = self._repo("session-repo")
        self._sidecar("a2222222222222222")
        reason = self._assert_denied(
            self._run_in("git commit -am wip", session, session))
        self.assertIn("ATELIER_GIT_GUARD_OVERRIDE=1", reason)
        # The stopgap's known failure mode: a blocked agent stashes by hand and
        # reintroduces the exact window the guard closes.
        self.assertIn("stash", reason.lower())
        self.assertIn("Restructure the operation to avoid an override first.", reason)
        self.assertIn(
            "only legitimate for a git write whose target is provably outside "
            "every live worker tree", reason)
        self.assertIn(
            "never for this project repository or any of its worktrees", reason)
        self.assertIn("report the exact command and cwd", reason)
        self.assertIn("explain why that target is not shared", reason)

    def test_pull_checkout_and_stash_are_denied(self):
        self._sidecar("a3333333333333333")
        for command, verb in (
            ("git pull --ff-only origin dev", "pull"),
            ("git checkout dev", "checkout"),
            ("git stash", "stash"),
            ("git switch dev", "switch"),
            ("git rebase origin/dev", "rebase"),
            ("git reset --hard origin/dev", "reset"),
            ("git restore Makefile", "restore"),
            ("git -C /repo commit -m x", "commit"),
            # An absolute path is the same program: matching the bare word
            # only would put the guard one `/usr/bin/` away from off.
            ("/usr/bin/git commit -m x", "commit"),
        ):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn(verb, reason)

    def test_compound_command_is_denied_on_its_first_mutating_verb(self):
        self._sidecar("a4444444444444444")
        reason = self._assert_denied(
            self._run(self._payload("git checkout dev && git pull --ff-only")))
        self.assertIn("checkout", reason)

    def test_up_to_four_agents_are_named(self):
        for index in range(6):
            self._sidecar("b{0}".format(index) * 8,
                          description="slice {0}".format(index))
        reason = self._assert_denied(self._run(self._payload("git commit")))
        named = sum(1 for index in range(6)
                    if "b{0}".format(index) * 8 in reason)
        self.assertEqual(named, 4, reason)
        self.assertIn("6", reason)  # the total is still stated

    # -- when it must stay out of the way ---------------------------------

    def test_read_only_git_is_silent_even_with_a_pending_child(self):
        self._sidecar("c1111111111111111")
        for command in (
            "git status --short",
            "git diff --cached",
            "git log --oneline -5",
            "git show HEAD",
            "git branch",
            "git rev-list --count origin/dev..HEAD",
            "git rev-parse HEAD",
            "git ls-files",
            "git fetch origin",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_settled_child_no_longer_blocks(self):
        self._sidecar("c2222222222222222")
        self._settle("c2222222222222222")
        self._assert_silent(self._run(self._payload("git commit -m done")))

    def test_worktree_isolated_child_never_blocks(self):
        self._sidecar("c3333333333333333",
                      worktree_path="/tmp/worktrees/agent-c3333333333333333")
        self._assert_silent(self._run(self._payload("git commit -m x")))

    def test_no_children_at_all_is_silent(self):
        os.makedirs(self.subagents_dir, exist_ok=True)
        self._assert_silent(self._run(self._payload("git commit -m x")))

    def test_non_bash_tool_is_silent(self):
        self._sidecar("c4444444444444444")
        payload = self._payload("git commit -m x", tool_name="Edit")
        self._assert_silent(self._run(payload))

    def test_missing_subagents_dir_is_silent(self):
        self._assert_silent(self._run(self._payload("git commit -m x")))

    def test_no_transcript_path_is_silent(self):
        self._sidecar("c5555555555555555")
        payload = self._payload("git commit -m x")
        del payload["transcript_path"]
        self._assert_silent(self._run(payload))

    def test_malformed_stdin_is_silent(self):
        self._sidecar("c6666666666666666")
        self._assert_silent(self._run(None, stdin_text="{not json"))
        self._assert_silent(self._run(None, stdin_text=""))
        self._assert_silent(self._run(None, stdin_text="[1, 2, 3]"))

    def test_a_quoted_git_word_is_not_a_git_call(self):
        self._sidecar("c7777777777777777")
        self._assert_silent(self._run(self._payload(
            'echo "remember to git commit when the builder reports"')))
        # The second form needs real quote handling, not a whitespace split:
        # split on spaces, `"cleanup;` ends in a separator and the next token
        # reads as a command in position.
        self._assert_silent(self._run(self._payload(
            'echo "cleanup; git commit -m x"')))
        self._assert_silent(self._run(self._payload(
            "man git commit")))

    def test_unreadable_ledger_fails_open_rather_than_blocking(self):
        # An unreadable ledger makes the settled set unknowable, not empty.
        # Rendering it as empty would report every agent this session ever
        # started as live and deny on all of them; the hook stays silent.
        self._sidecar("c8888888888888888")
        self._settle("c8888888888888888")
        os.chmod(self.delegation_log, 0o000)
        self.addCleanup(os.chmod, self.delegation_log, 0o644)
        if os.access(self.delegation_log, os.R_OK):
            self.skipTest("running as a user that ignores file modes")
        self._assert_silent(self._run(self._payload("git commit -m x")))

    # -- when the caller is itself a subagent ------------------------------

    def test_a_delegating_subagent_is_guarded_against_its_own_children(self):
        # A manager holding live builders is the same shared-tree hazard as a
        # root session holding them.
        self._sidecar("f1111111111111111", agent_type="atelier:manager")
        self._sidecar("f2222222222222222", agent_type="atelier:builder")
        reason = self._assert_denied(self._run(self._payload(
            "git commit -m wave", agent_id="f1111111111111111")))
        self.assertIn("f2222222222222222", reason)
        # ...but it is never named as live to itself.
        self.assertNotIn("f1111111111111111", reason)

    def test_the_caller_alone_pending_is_silent(self):
        self._sidecar("f3333333333333333", agent_type="atelier:manager")
        self._assert_silent(self._run(self._payload(
            "git commit -m x", agent_id="f3333333333333333")))

    def test_a_caller_in_its_own_worktree_is_exempt(self):
        # It is not looking at this tree, so this tree's occupants are not its
        # problem — even though a non-isolated sibling is live here.
        self._sidecar("f4444444444444444", agent_type="atelier:builder",
                      worktree_path="/tmp/worktrees/agent-f4444444444444444")
        self._sidecar("f5555555555555555")
        self._assert_silent(self._run(self._payload(
            "git commit -m x", agent_id="f4444444444444444")))

    # -- the override ------------------------------------------------------

    def test_override_lets_the_command_through_with_a_system_message(self):
        self._sidecar("d1111111111111111", agent_type="atelier:scout")
        result = self._run(self._payload(
            'ATELIER_GIT_GUARD_OVERRIDE=1 git commit -m "unrelated work"'))
        payload = json.loads(result.stdout)
        self.assertNotIn("hookSpecificOutput", payload)
        message = payload["systemMessage"]
        self.assertIn("ATELIER_GIT_GUARD_OVERRIDE", message)
        self.assertIn("d1111111111111111", message)

    def test_override_without_pending_children_says_nothing_but_is_recorded(self):
        os.makedirs(self.subagents_dir, exist_ok=True)
        result = self._run(self._payload(
            "ATELIER_GIT_GUARD_OVERRIDE=1 git commit -m x"))
        self.assertEqual(result.stdout.strip(), "", result.stdout)
        rows = _read_rows(self.guard_log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["decision"], "override")
        self.assertEqual(rows[0]["pending"], [])

    def test_override_after_the_git_word_does_not_count(self):
        self._sidecar("d2222222222222222")
        self._assert_denied(self._run(self._payload(
            "git commit -m ATELIER_GIT_GUARD_OVERRIDE=1")))

    def test_override_prefix_on_an_earlier_command_does_not_count(self):
        self._sidecar("d3333333333333333")
        self._assert_denied(self._run(self._payload(
            "ATELIER_GIT_GUARD_OVERRIDE=1 echo hi && git commit -m x")))

    def test_override_on_the_line_before_does_not_count(self):
        # A newline ends a command as `;` does, so a bare assignment on its
        # own line is a shell variable, not the git call's env prefix.
        self._sidecar("d4444444444444444")
        for command in ("ATELIER_GIT_GUARD_OVERRIDE=1\ngit push",
                        "env ATELIER_GIT_GUARD_OVERRIDE=1\ngit push"):
            with self.subTest(command=command):
                self._assert_denied(self._run(self._payload(command)))

    def test_read_only_forms_of_mutating_verbs_are_silent(self):
        self._sidecar("d4444444444444444")
        for command in ("git stash list", "git stash show -p stash@{0}",
                        "git apply --check fix.diff", "git apply --stat fix.diff",
                        # The read form carried a glued separator: the verb
                        # strip fixed the VERB, not the args compared here.
                        "git stash list; ls",
                        "for f in a b; do git stash list; done",
                        # `--help` is orientation, whatever the verb.
                        "git commit --help", "git rebase --help",
                        "git stash --help", "git push -h"):
            result = self._run(self._payload(command))
            self.assertEqual(result.returncode, 0, command)
            self.assertEqual(result.stdout, "", command)

    def test_write_forms_of_those_verbs_still_deny(self):
        self._sidecar("d5555555555555555")
        for command in ("git stash", "git stash pop", "git stash list && git stash",
                        "git apply fix.diff"):
            with self.subTest(command=command):
                self._assert_denied(self._run(self._payload(command)))

    # -- the widened verb set (card p03n) ----------------------------------

    def test_verbs_that_take_a_tracked_file_off_this_tree_are_denied(self):
        # Each row was measured silent on 2026-09-08, and each does what the
        # hook's opening line describes.
        self._sidecar("e1111111111111111")
        for command, verb in (
            ("git rm stale_module.py", "rm"),
            # All forms: carving the index-only one out would make the guard
            # parse flags to decide a milder mutation is acceptable.
            ("git rm --cached stale_module.py", "rm"),
            ("git mv old_name.py new_name.py", "mv"),
            ("git bisect start HEAD HEAD~10", "bisect"),
            ("git bisect reset", "bisect"),
            ("git bisect run make ci", "bisect"),
            ("git submodule update --init --recursive", "submodule"),
            ("git submodule deinit -f vendor/lib", "submodule"),
            ("git sparse-checkout set src", "sparse-checkout"),
            ("git sparse-checkout disable", "sparse-checkout"),
            ("git update-ref refs/heads/dev HEAD", "update-ref"),
            ("git read-tree -u -m HEAD", "read-tree"),
            ("git checkout-index -a -f", "checkout-index"),
        ):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn(verb, reason)

    def test_the_read_forms_of_the_widened_verbs_stay_silent(self):
        # A read that starts denying is a regression: the guard's premise is
        # that orientation stays cheap.
        self._sidecar("e2222222222222222")
        for command in (
            "git rm --dry-run stale_module.py",
            "git rm -n stale_module.py",
            "git mv -n old_name.py new_name.py",
            "git mv --dry-run old_name.py new_name.py",
            "git bisect log",
            "git bisect view",
            "git bisect visualize",
            "git bisect terms",
            "git bisect help",
            "git submodule status",
            "git submodule summary",
            "git sparse-checkout list",
            "git sparse-checkout check-rules",
            "git read-tree -n -m HEAD",
            "git read-tree --dry-run -m HEAD",
            # `--help` is orientation on the new verbs too.
            "git rm --help", "git update-ref -h", "git submodule --help",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_a_subcommand_verb_with_no_subcommand_writes_nothing(self):
        # Measured 2026-09-08: bare `git submodule` is `status` (exit 0), bare
        # `git bisect` and `git sparse-checkout` print usage (exit 129).
        # `stash` is the exception below — bare means push.
        self._sidecar("e3333333333333333")
        for command in ("git submodule", "git bisect", "git sparse-checkout"):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))
        self._assert_denied(self._run(self._payload("git stash")))

    def test_index_only_writes_are_deliberately_not_denied(self):
        # Nothing leaves the disk, and every path from a dirty index to lost
        # work runs through a verb already in the set.
        self._sidecar("e4444444444444444")
        for command in ("git add -A", "git add -p src/",
                        "git update-index --refresh"):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_ref_writes_with_an_everyday_read_spelling_stay_out(self):
        # Telling these from their read forms needs the per-verb flag parser
        # this guard refuses to build, and none takes a file off disk.
        self._sidecar("e5555555555555555")
        for command in ("git branch -D old", "git tag -a v1 -m x",
                        "git symbolic-ref --short HEAD", "git notes add -m x",
                        "git remote add up https://example.invalid/r.git",
                        "git reflog expire --expire=now --all"):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_an_option_value_is_not_read_as_a_subcommand(self):
        """`git stash -m list` is `stash push` with a message. Taking the first
        bare token as the subcommand read `list` and let a real stash through."""
        self._sidecar("e6666666666666666")
        for command in ("git stash -m list", "git stash -m show",
                        "git stash --message list"):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn("stash", reason)

    def test_a_double_dash_ends_the_options_a_read_form_could_hide_in(self):
        """Past `--` every token is a path: `git rm -- -n` deletes a file NAMED
        `-n`, and matching the dry-run flag anywhere made that silent."""
        self._sidecar("e7777777777777777")
        for command, verb in (("git rm -- -n", "rm"),
                              ("git mv -- -n other", "mv"),
                              ("git stash -- show", "stash")):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn(verb, reason)

    def test_a_help_flag_that_is_an_option_value_is_not_a_help_call(self):
        """`git commit -m -h` commits with the message `-h`."""
        self._sidecar("e8888888888888888")
        for command in ("git commit -m -h", "git commit -m --help",
                        "git commit --message --help"):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn("commit", reason)

    def test_a_help_call_is_still_a_help_call(self):
        self._sidecar("e9999999999999999")
        for command in ("git commit --help", "git rm -h", "git submodule --help",
                        "git bisect --help log"):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_the_git_word_is_matched_case_insensitively(self):
        """macOS filesystems are case-insensitive, so `GIT rm` runs git."""
        self._sidecar("ea111111111111111")
        for command, verb in (("GIT rm src/x.py", "rm"),
                              ("Git commit -m x", "commit"),
                              ("/usr/bin/GIT push", "push")):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn(verb, reason)

    def test_a_read_form_glued_to_a_separator_is_still_a_read(self):
        """shlex leaves `status|grep` one token, so the read form no longer
        matched and an orientation command started denying."""
        self._sidecar("ea222222222222222")
        for command in ("git submodule status|grep vendor",
                        "git bisect log;git status",
                        "git submodule status&&echo ok",
                        "git submodule status||true",
                        "git submodule status>/tmp/x",
                        "git sparse-checkout list|wc -l"):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_a_write_form_glued_to_a_separator_still_denies(self):
        self._sidecar("ea333333333333333")
        for command, verb in (("git submodule update|tee /tmp/x", "submodule"),
                              ("git pull;git status", "pull")):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn(verb, reason)

    # -- the tree the command targets --------------------------------------

    def _repo(self, name):
        """A real git repo under the tempdir.

        realpath'd because on macOS a tempdir is reached through a symlink and
        git reports the resolved path, so an unresolved fixture path would make
        every comparison in these tests spuriously unequal.
        """
        require_git()
        root = os.path.realpath(os.path.join(self.tmp.name, name))
        os.makedirs(root, exist_ok=True)
        subprocess.run(["git", "init", "-q", root],
                       capture_output=True, check=True, timeout=60)
        return root

    def _run_in(self, command, cwd, project_dir, agent_id=None):
        """Run the hook for a command issued in `cwd`, with the session's main
        checkout advertised as `project_dir` — CLAUDE_PROJECT_DIR, which Claude
        Code sets on the hook process."""
        payload = self._payload(command, agent_id=agent_id)
        payload["cwd"] = cwd
        env = {} if project_dir is None else {"CLAUDE_PROJECT_DIR": project_dir}
        return self._run(payload, extra_env=env)

    def test_a_mutating_command_in_an_unrelated_repo_is_not_blocked(self):
        # The field case: a manager dispatched from this session works in a
        # checkout of a DIFFERENT repo. The workers occupy this session's tree,
        # which that command cannot reach.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("g1111111111111111")
        self._assert_silent(self._run_in("git push origin dev", other, session))

    def test_the_session_tree_still_denies_when_both_sides_resolve(self):
        session = self._repo("session-repo")
        self._sidecar("g2222222222222222")
        reason = self._assert_denied(
            self._run_in("git push origin dev", session, session))
        self.assertIn("g2222222222222222", reason)

    def test_a_subdirectory_of_the_session_tree_still_denies(self):
        session = self._repo("session-repo")
        deep = os.path.join(session, "a", "b")
        os.makedirs(deep, exist_ok=True)
        self._sidecar("g3333333333333333")
        self._assert_denied(self._run_in("git commit -m x", deep, session))

    def test_a_linked_worktree_of_the_session_repo_is_not_blocked(self):
        # Same repository, different WORKING TREE: a mutating call here writes
        # this tree's index and the shared refs, and takes no file off disk in
        # the tree the workers hold.
        require_git()
        main_dir, worktree_dir = make_worktree(self.tmp.name)
        self._sidecar("g4444444444444444")
        self._assert_silent(
            self._run_in("git commit -m x", worktree_dir, main_dir))

    def test_dash_c_aims_the_check_at_the_named_repo(self):
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("g5555555555555555")
        self._assert_silent(self._run_in(
            "git -C {0} commit -m x".format(other), session, session))
        reason = self._assert_denied(self._run_in(
            "git -C {0} commit -m x".format(session), other, session))
        self.assertIn("g5555555555555555", reason)

    def test_a_git_dir_or_work_tree_flag_fails_closed(self):
        # Both flags relocate the working tree by a rule this hook does not
        # reimplement, so the target is unknowable and the guard denies.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("g6666666666666666")
        for command in (
            "git --git-dir={0}/.git commit -m x".format(other),
            "git --work-tree {0} commit -m x".format(other),
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run_in(command, other, session))

    def test_a_cd_before_the_git_word_fails_closed(self):
        # The payload cwd is then stale, so the target is unknowable — the
        # same answer the two tree-aiming flags get.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("j1111111111111111")
        for command in (
            "cd {0} && git commit -m x".format(session),
            "( cd {0} ; git commit -m x )".format(session),
            "pushd {0} && git commit -m x".format(session),
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run_in(command, other, session))

    def test_a_git_tree_env_assignment_fails_closed(self):
        # GIT_WORK_TREE and GIT_DIR are the same relocation `--work-tree` and
        # `--git-dir` spell as flags, so they get the same answer.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("j2222222222222222")
        for command in (
            "GIT_WORK_TREE={0} git -C {1} commit -m x".format(session, other),
            "GIT_DIR={0}/.git git commit -m x".format(session),
            "GIT_COMMON_DIR={0}/.git git commit -m x".format(session),
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run_in(command, other, session))

    def test_a_cd_word_that_is_not_a_command_still_compares(self):
        # `cd` only moves the cwd in command position; as an argument it is
        # just a word, and over-denying on it would be noise.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("j3333333333333333")
        self._assert_silent(
            self._run_in("echo cd && git commit -m x", other, session))

    def test_a_non_string_cwd_fails_closed(self):
        session = self._repo("session-repo")
        self._sidecar("j4444444444444444")
        for bad in ({"a": 1}, 123, ["x"]):
            with self.subTest(cwd=bad):
                self._assert_denied(self._run_in("git commit -m x", bad, session))

    def test_a_cwd_outside_any_repo_fails_closed(self):
        session = self._repo("session-repo")
        self._sidecar("g7777777777777777")
        self._assert_denied(self._run_in("git commit -m x", self.cwd, session))

    def test_an_unset_project_dir_fails_closed(self):
        other = self._repo("other-repo")
        self._sidecar("g8888888888888888")
        self._assert_denied(self._run_in("git commit -m x", other, None))

    def test_a_project_dir_outside_any_repo_fails_closed(self):
        other = self._repo("other-repo")
        self._sidecar("g9999999999999999")
        self._assert_denied(self._run_in("git commit -m x", other, self.cwd))

    def test_a_symlinked_path_on_either_side_still_matches(self):
        session = self._repo("session-repo")
        link = os.path.join(self.tmp.name, "session-link")
        os.symlink(session, link)
        self._sidecar("h1111111111111111")
        self._assert_denied(self._run_in("git commit -m x", link, link))
        self._assert_denied(self._run_in("git commit -m x", session, link))
        self._assert_denied(self._run_in("git commit -m x", link, session))

    def test_init_and_clone_are_not_guarded_verbs(self):
        # Neither is in MUTATING_VERBS, so neither reaches the tree comparison
        # — creating a repo in a fresh directory stays free.
        self._sidecar("h2222222222222222")
        for command in ("git init .", "git clone https://example.invalid/r.git"):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    # -- exec wrappers around the command word ------------------------------

    def test_an_exec_wrapper_does_not_hide_a_mutating_call(self):
        # Measured 2026-09-08: every row but the control was silent, because
        # the `git` word was read only in command position of the raw string.
        # Nobody writes `env git commit` by accident, but `time git push` and
        # `timeout 60 git push` are things a real session writes for real
        # reasons, and each lost its deny with no trace.
        self._sidecar("k1111111111111111")
        for command in (
            "git commit -m x",
            "env git commit -m x",
            "command git commit -m x",
            "nice git commit -m x",
            "time git commit -m x",
            "echo x | xargs git commit -m",
            "timeout 60 git push origin dev",
            "sudo git commit -m x",
            "nohup git push origin dev",
            "stdbuf -oL git push origin dev",
            "setsid git push origin dev",
            "eval git commit -m x",
            "builtin git commit -m x",
            "exec git push origin dev",
            "exec -a mygit git commit -m x",
            "nice time git commit -m x",
        ):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn("live-worker-git-guard", reason)

    def test_the_coreutils_g_spelling_of_a_wrapper_is_the_same_wrapper(self):
        # Homebrew's coreutils ship these `g`-prefixed and both spellings sit
        # on PATH on a Mac, so `gtimeout 60 git push` is the same real shape.
        self._sidecar("k9999999999999999")
        for command in (
            "gtimeout 60 git push origin dev",
            "gnice -n 10 git commit -m x",
            "genv -u GIT_DIR git commit -m x",
            "echo x | gxargs -n 1 git commit -m",
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run(self._payload(command)))
        # Not a blanket `g`-prefix rule: only the wrappers that have such a
        # spelling, so an ordinary command starting with `g` is untouched.
        # (stdout only — the denies above have already written ledger rows.)
        self.assertEqual(
            self._run(self._payload("gh pr merge && ls")).stdout.strip(), "")

    def test_an_exec_wrapped_cd_still_stales_the_payload_cwd(self):
        # The other half of the same defect: with the call issued from an
        # unrelated repo, only the `cd` check can produce a deny, and a wrapper
        # around the `cd` hid it.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("k2222222222222222")
        for command in (
            "cd {0} && git commit -m x",
            "builtin cd {0} && git commit -m x",
            "command cd {0} && git commit -m x",
            "eval cd {0} && git commit -m x",
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run_in(
                    command.format(session), other, session))

    def test_a_wrapper_flag_that_moves_the_tree_fails_closed(self):
        # `env -C` / `sudo -D` relocate the tree by a rule this hook does not
        # reimplement, so the target is unknowable — the same answer
        # `--work-tree` gets, and never a silent skip past the flag.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("k3333333333333333")
        for command in (
            "env -C {0} git commit -m x",
            "env --chdir={0} git commit -m x",
            "env -S '-C {0}' git commit -m x",
            "env --split-string='-C {0}' git commit -m x",
            "sudo -D {0} git commit -m x",
            "sudo --chdir={0} git commit -m x",
            # `man sudo` here: `[-D directory] ... [-R directory]` — both
            # relocate, so both are unknowable rather than resolvable.
            "sudo -R {0} git commit -m x",
            "sudo --chroot={0} git commit -m x",
            # The glued short spelling the docstring names.
            "env -C{0} git commit -m x",
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run_in(
                    command.format(other), other, session))

    def test_a_wrapper_flag_value_is_not_read_as_the_command(self):
        # Each of these has a value token between the wrapper and `git`; a
        # naive "first non-flag token is the command" rule reads the value as
        # the command and loses the deny. `timeout`'s duration is a BARE
        # positional, not a flag value.
        self._sidecar("k4444444444444444")
        for command in (
            "env -u GIT_DIR git commit -m x",
            "env --unset=GIT_DIR git commit -m x",
            "env FOO=bar git commit -m x",
            "nice -n 10 git commit -m x",
            "nice -5 git commit -m x",
            "time -o /tmp/t.log git commit -m x",
            "echo x | xargs -n 1 -P 2 git commit -m",
            "echo x | xargs -I {} git commit -m {}",
            # `-i`/`-e`/`-l` take an OPTIONAL argument, which must be glued —
            # reading the next token as their value swallows the `git` word.
            "echo x | xargs -i git commit -m",
            "echo x | xargs -l git commit -m",
            "timeout --kill-after 5 60 git push origin dev",
            "sudo -u someone git commit -m x",
            # BSD spellings, verified against this machine's man pages:
            # xargs `-J replstr` `-R replacements` `-S replsize`,
            # sudo `-T timeout`, env `-P altpath`, GNU env `-a, --argv0=ARG`.
            "echo x | xargs -J % git commit -m %",
            "echo x | xargs -I % -R 2 git commit -m %",
            "echo x | xargs -I % -S 300 git commit -m %",
            "echo x | xargs -I % git commit -m %",
            "sudo -T 30 git commit -m x",
            "sudo --command-timeout 30 git commit -m x",
            "env -P /usr/bin git commit -m x",
            "env -a foo git commit -m x",
            "env --argv0=foo git commit -m x",
            # Optional-argument long spellings: the value must be glued, so
            # reading the next token as it swallows the command word.
            "echo x | xargs --replace git commit -m",
            "echo x | xargs --eof git commit -m",
            "echo x | xargs --replace=% git commit -m %",
            # git's own `--exec-path[=<path>]` is optional-argument too.
            "git --exec-path commit -m x",
            "git --exec-path=/usr/libexec commit -m x",
            # Glued spellings, which the README claims are NOT a ceiling.
            "nice -n10 git commit -m x",
            "env -uGIT_DIR git commit -m x",
            "echo x | xargs -I% git commit -m %",
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run(self._payload(command)))

    def test_the_override_survives_a_wrapper(self):
        # Unwrapping moves the `git` word, and the override run is read
        # BACKWARDS from it: read from the wrong end, the sanctioned escape
        # hatch turns into a deny.
        self._sidecar("k5555555555555555", agent_type="atelier:scout")
        for command in (
            "ATELIER_GIT_GUARD_OVERRIDE=1 nice git commit -m x",
            "ATELIER_GIT_GUARD_OVERRIDE=1 timeout 60 git push",
            "env ATELIER_GIT_GUARD_OVERRIDE=1 git commit -m x",
        ):
            with self.subTest(command=command):
                result = self._run(self._payload(command))
                payload = json.loads(result.stdout)
                self.assertNotIn("hookSpecificOutput", payload, command)
                self.assertIn("k5555555555555555", payload["systemMessage"])

    def test_a_wrapper_does_not_widen_the_guard_onto_reads(self):
        # The over-denial surface of the unwrap: a wrapped read is still a
        # read, a lookup is not a call, and a wrapper NAME appearing as an
        # argument is just a word.
        self._sidecar("k6666666666666666")
        for command in (
            "nice git status --short",
            "time git log --oneline -5",
            "env -u GIT_DIR git diff",
            "timeout 5 git fetch origin",
            "command -v git",
            "command -V git",
            "which git",
            "echo time git commit",
            "ls env nice time",
            "timeout 60 echo git commit",
            "nice git stash list",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_a_wrapper_flag_on_an_earlier_command_does_not_fail_closed(self):
        # `env -C` binds the command IT wraps. Applied to something that is
        # not the git call, it says nothing about where the git call points.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("k7777777777777777")
        self._assert_silent(self._run_in(
            "env -C {0} true && git commit -m x".format(session),
            other, session))

    # -- shell keywords in front of the command word ------------------------

    def test_a_shell_keyword_does_not_hide_a_mutating_call(self):
        # The same displacement the exec wrappers caused, spelled as grammar:
        # after `do` or `then` the next word IS a command, and a session
        # writes loops and conditionals for real reasons.
        self._sidecar("m1111111111111111")
        for command in (
            "for f in *; do git commit -m x; done",
            "while read f; do git push origin dev; done",
            "if true; then git commit -m x; fi",
            "if git commit -m x; then echo ok; fi",
            "while git pull; do sleep 1; done",
            # Pre-existing miss the keyword rows surfaced: the VERB carried the
            # glued separator, so `pull;` never matched the verb set.
            "git commit; echo done",
            "git stash; ls",
            "until git push origin dev; do sleep 1; done",
            "if false; then echo no; else git commit -m x; fi",
            "if false; then echo no; elif true; then git commit -m x; fi",
            "if a; then b; elif git commit -m x; then c; fi",
            "! git commit -m x",
            "for f in *; do nice git commit -m x; done",
        ):
            with self.subTest(command=command):
                reason = self._assert_denied(self._run(self._payload(command)))
                self.assertIn("live-worker-git-guard", reason)

    def test_a_keyword_before_a_cd_still_stales_the_payload_cwd(self):
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("m2222222222222222")
        for command in (
            "for d in a b; do cd {0} && git commit -m x; done",
            "if true; then cd {0} && git commit -m x; fi",
            "while true; do command cd {0} && git commit -m x; done",
            # The way a subshell cd is actually written: glued to the `(`.
            "(cd {0} && git commit -m x)",
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run_in(
                    command.format(session), other, session))

    def test_the_keyword_rule_does_not_widen_onto_reads(self):
        self._sidecar("m3333333333333333")
        for command in (
            "for f in *; do git status --short; done",
            "if true; then git log --oneline -5; fi",
            "while read f; do git show HEAD; done",
            "grep -r then .",
            'echo "do git commit"',
            "for f in *; do nice git status; done",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_a_bare_keyword_as_an_argument_over_denies_deliberately(self):
        # Accepted over-denial, pinned rather than hidden: `do` is `echo`'s
        # argument here, but the rule cannot tell that without a parser, and
        # a false deny costs one override while a miss costs a worker's files.
        self._sidecar("m4444444444444444")
        reason = self._assert_denied(
            self._run(self._payload("echo do git commit")))
        self.assertIn("commit", reason)
        # A quoted keyword is one token, so it stays inert: this denies on the
        # real `commit` in command position, never on the string's `push`.
        reason = self._assert_denied(self._run(self._payload(
            'git commit -m "then git push"')))
        self.assertIn("`git commit`", reason)
        self.assertNotIn("`git push`", reason)

    def test_a_trailing_comment_does_not_open_command_position(self):
        # `#` never opened command position; a keyword one token later must not
        # either, or every trailing comment mentioning a git command denies.
        self._sidecar("n1111111111111111")
        for command in (
            "make ci  # then git commit",
            "python3 -m unittest tests.foo  # if git commit fails, retry",
            "ls -la  # do git push after this",
            "sleep 1  # while git pull runs",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_a_separator_inside_a_comment_still_opens_command_position(self):
        # Going inert suspends the KEYWORD rule only. A separator behaves as it
        # always did, so this over-denial is unchanged rather than introduced —
        # pinned because both prose surfaces claim exactly that.
        self._sidecar("n3333333333333333")
        self._assert_denied(self._run(self._payload(
            "ls  # note; git commit -m x")))

    def test_a_heredoc_body_with_a_keyword_stays_invisible(self):
        # Both prose surfaces promise heredoc bodies are not read. A keyword in
        # the body must not reopen command position, or writing a shell script
        # about git blocks the session writing it.
        self._sidecar("n2222222222222222")
        for command in (
            "cat > release.sh <<'EOF'\nfor f in *; do git commit -m x; done\nEOF",
            "cat >> notes.md <<'EOF'\nthen git push origin dev\nEOF",
            "cat > release.sh <<'EOF'\ngit commit -m x\nEOF",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_a_separator_in_a_heredoc_body_does_not_reopen_command_position(self):
        # The body is dropped before the scan, so a `&&` or `|` in a note being
        # written reopens nothing, whatever the delimiter's quoting.
        self._sidecar("n4444444444444444")
        for command in (
            "cat > /tmp/x.md <<EOF\nrun: git -C /tmp/wt fetch origin && "
            "git -C /tmp/wt rebase origin/main\nEOF",
            "cat > /tmp/x.md <<'EOF'\nrun: git -C /tmp/wt fetch origin && "
            "git -C /tmp/wt rebase origin/main\nEOF",
            "cat <<EOF\necho a | git rebase main\nEOF",
            "cat <<-EOF\n\techo a && git rebase main\n\tEOF",
            "cat <<EOF\nsee git rebase main\nEOF",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    def test_a_git_call_after_the_heredoc_terminator_is_read(self):
        self._sidecar("n5555555555555555")
        for command in (
            "cat > /tmp/x <<EOF\nhello\nEOF\ngit rebase main",
            "cat <<-EOF\n\thello\n\tEOF\ngit rebase main",
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run(self._payload(command)))

    def test_an_unquoted_newline_opens_command_position(self):
        # A newline ends a command exactly as `;` does, and a `#` comment ends
        # with its line.
        self._sidecar("n6666666666666666")
        for command in (
            "echo hi\ngit commit -m x",
            "make ci  # comment\ngit commit -m x",
            "for f in *\ndo git commit -m x\ndone",
        ):
            with self.subTest(command=command):
                self._assert_denied(self._run(self._payload(command)))

    def test_a_heredoc_opener_counts_only_outside_quotes_and_comments(self):
        # A `<<WORD` in a comment, a quoted string (even one opened on an
        # earlier line) or an arithmetic shift opens no heredoc, so the lines
        # up to a later line equal to WORD are still commands.
        cases = (
            ("# write the notes file with <<EOF below\n"
             "git add x && git commit -m y\ncat > notes.md <<EOF\nbody\nEOF",
             "commit"),
            ("grep -q '<<EOF' gen.sh &&\n  git push\ncat > f <<EOF\nbody\nEOF",
             "push"),
            ("echo $(( 1 <<3 ))\ngit push\n3", "push"),
            ('echo "a\n<<EOF"\ngit push\nEOF', "push"),
            # A `#` right after a separator is a comment; `$'...'` escapes a
            # quote with a backslash.
            ('echo "<<Z" ;# <<A\ngit push\nA', "push"),
            ("echo \"<<Z\" $'a\\' <<A'\ngit push\nA", "push"),
            ("ls;# it's\ngit push", "push"),
            ("echo $'it\\'s'\ngit push", "push"),
        )
        for command, verb in cases:
            with self.subTest(command=command):
                self.assertEqual(
                    HOOK._first_mutating_verb(HOOK._tokens(command))[0], verb)

    def test_newline_reading_at_the_token_level(self):
        cases = (
            ('git commit -m "a\nb"', "commit"),
            ("echo 'a\ngit commit'", None),
            ("echo hi\ngit commit -m x", "commit"),
            ("cat <<EOF\nsee git rebase main\nEOF", None),
            # An unmatched `<<` (a shift, a herestring) drops nothing.
            ("echo $((1 << 3))\ngit commit -m x", "commit"),
            ("cat <<< hi\ngit commit -m x", "commit"),
            ("cat <<EOF\ngit commit -m x", "commit"),
            # A backslash-newline continues the line; a body line ending in
            # one still strips with its terminator.
            ("git \\\ncommit -m x", "commit"),
            ("make ci \\\n  && git commit -m x", "commit"),
            ("cat <<EOF\necho a && git rebase main \\\nEOF", None),
            ("cat <<EOF\nhello \\\nEOF\ngit commit -m x", "commit"),
            # An escaped backslash does not continue the line.
            ("echo foo\\\\\ngit push", "push"),
            # A line break clears the inert state of a `<<` or `#`.
            ("cat <<EOF\nx\nEOF\nif true; then git push; fi", "push"),
            ("make ci # note\nfor f in *; do git commit -m x; done", "commit"),
        )
        for command, verb in cases:
            with self.subTest(command=command):
                self.assertEqual(
                    HOOK._first_mutating_verb(HOOK._tokens(command))[0], verb)

    def test_the_tokenizer_ceilings_stay_ceilings(self):
        # Not a wish list: each needs a parser rather than a token scan, and
        # the README names them as things the guard cannot see. A change here
        # is a deliberate widening, not an accident.
        self._sidecar("k8888888888888888")
        for command in (
            'bash -c "git commit -m x"',
            "sh -c 'git commit -m x'",
            "echo $(git commit -m x)",
            "ls&&git commit -m x",
            # Deliberate asymmetry with the cwd check, which DOES strip a
            # leading `(`: a glued COMMAND WORD stays a stated ceiling.
            "(git commit -m x)",
            "env -S 'git commit -m x'",
            "cat <<EOF\ngit commit -m x\nEOF",
        ):
            with self.subTest(command=command):
                self._assert_silent(self._run(self._payload(command)))

    # -- the ledger --------------------------------------------------------

    def test_deny_writes_one_ledger_row(self):
        self._sidecar("e1111111111111111")
        self._sidecar("e2222222222222222")
        self._run(self._payload("git pull"))
        rows = _read_rows(self.guard_log)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["stream"], "live-worker-git-guard")
        self.assertEqual(row["decision"], "deny")
        self.assertEqual(row["verb"], "pull")
        self.assertEqual(sorted(row["pending"]),
                         ["e1111111111111111", "e2222222222222222"])
        self.assertEqual(row["session_id"], self.session_id)

    def test_override_writes_one_ledger_row(self):
        self._sidecar("e3333333333333333")
        self._run(self._payload("ATELIER_GIT_GUARD_OVERRIDE=1 git merge dev"))
        rows = _read_rows(self.guard_log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["decision"], "override")
        self.assertEqual(rows[0]["verb"], "merge")
        self.assertEqual(rows[0]["pending"], ["e3333333333333333"])

    def test_an_override_that_suppressed_nothing_is_still_recorded(self):
        # The scoping fix would otherwise make this exit before the append and
        # leave the use of the override with no trace at all.
        session = self._repo("session-repo")
        other = self._repo("other-repo")
        self._sidecar("h3333333333333333")
        result = self._run_in(
            "ATELIER_GIT_GUARD_OVERRIDE=1 git push origin dev", other, session)
        self.assertEqual(result.stdout.strip(), "", result.stdout)
        rows = _read_rows(self.guard_log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["decision"], "override")
        self.assertEqual(rows[0]["verb"], "push")
        # An empty `pending` is what separates an override that suppressed
        # nothing from one that suppressed a block.
        self.assertEqual(rows[0]["pending"], [])

    def test_an_override_that_suppressed_a_block_names_who_it_freed(self):
        session = self._repo("session-repo")
        self._sidecar("h4444444444444444")
        result = self._run_in(
            "ATELIER_GIT_GUARD_OVERRIDE=1 git push origin dev", session, session)
        self.assertIn("h4444444444444444",
                      json.loads(result.stdout)["systemMessage"])
        rows = _read_rows(self.guard_log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["decision"], "override")
        self.assertEqual(rows[0]["pending"], ["h4444444444444444"])

    def test_an_override_prefix_on_a_read_only_git_call_writes_no_row(self):
        # The stream must stay a record of contested commands, not one row per
        # Bash call that happens to carry the prefix.
        self._sidecar("h5555555555555555")
        self._assert_silent(self._run(self._payload(
            "ATELIER_GIT_GUARD_OVERRIDE=1 git status --short")))
        self._assert_silent(self._run(self._payload(
            "ATELIER_GIT_GUARD_OVERRIDE=1 ls -la")))


class VerbRulingTableTests(unittest.TestCase):
    """The README's ruling table is the verb set, checked against the code.

    Card p03n's failure mode was a verb left out with no stated reason and a
    comment that no longer described the set. Pinning the table to
    `MUTATING_VERBS` and `READ_FORMS` means a verb cannot move in the code
    without its row moving with it, in either direction.
    """

    SECTION = "## The verb set, verb by verb"

    def setUp(self):
        readme = os.path.join(
            HOOKS_ROOT, "live-worker-git-guard", "README.md")
        with open(readme, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(self.SECTION, text, "the ruling table is missing")
        section = text.split(self.SECTION, 1)[1].split("\n## ", 1)[0]
        self.rows = [
            [cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in section.splitlines() if line.startswith("| `")
        ]
        self.assertTrue(self.rows, "no ruled rows in the table")

    @staticmethod
    def _terms(cell):
        """The backticked tokens in a cell; `bare` is the no-subcommand call,
        which READ_FORMS spells as the empty string."""
        return {"" if term == "bare" else term
                for term in re.findall(r"`([^`]+)`", cell)}

    def _ruled(self, ruling):
        verbs = set()
        for row in self.rows:
            if row[1] == ruling:
                verbs |= self._terms(row[0])
        return verbs

    def test_the_table_names_exactly_the_verbs_the_hook_denies(self):
        self.assertEqual(self._ruled("denied"), set(HOOK.MUTATING_VERBS))

    def test_the_table_publishes_exactly_the_carve_outs_the_hook_honours(self):
        self.assertEqual(set(HOOK.READ_FORMS) - self._ruled("denied"), set())
        for row in self.rows:
            if row[1] != "denied":
                continue
            for verb in self._terms(row[0]):
                self.assertEqual(self._terms(row[2]),
                                 set(HOOK.READ_FORMS.get(verb, ())), verb)

    def test_no_verb_the_table_excludes_is_denied_in_the_code(self):
        excluded = self._ruled("not denied")
        self.assertTrue(excluded, "the table records no exclusion")
        self.assertEqual(excluded & set(HOOK.MUTATING_VERBS), set())

    def test_every_ruling_states_a_reason(self):
        # An omission with no stated reason is what produced card p03n.
        for row in self.rows:
            self.assertGreater(len(row[3]), 20, row[0])

    def test_a_subcommand_verb_is_one_whose_carve_outs_are_subcommands(self):
        for verb in HOOK.SUBCOMMAND_VERBS:
            self.assertIn(verb, HOOK.READ_FORMS, verb)
            self.assertFalse(
                [f for f in HOOK.READ_FORMS[verb] if f.startswith("-")], verb)


class SharedLedgerTests(unittest.TestCase):
    """The guard reads the ledger subagent-telemetry writes.

    Each hook binds its own stream name as a literal (the agentlog gate wants
    it bound where it is claimed), so `_lib/pending.py` and the telemetry hook
    hold two copies of one string. Nothing else notices if they drift: the
    guard would read an empty ledger, see every delegation as pending, and deny
    forever.
    """

    def _bound(self, name):
        path = os.path.join(HOOKS_ROOT, "subagent-telemetry", "hook.py")
        with open(path, encoding="utf-8") as fh:
            found = re.findall(
                r'^{0} = "([^"]+)"'.format(name), fh.read(), re.M)
        self.assertEqual(len(found), 1, "{0} bound {1} time(s)".format(
            name, len(found)))
        return found[0]

    def test_stream_the_guard_reads_is_the_one_telemetry_writes(self):
        self.assertEqual(self._bound("LOG_STREAM"), pending.LEDGER_STREAM)

    def test_path_override_the_guard_reads_is_the_one_telemetry_writes(self):
        self.assertEqual(self._bound("LOG_PATH_ENV"), pending.LEDGER_PATH_ENV)


if __name__ == "__main__":
    unittest.main()

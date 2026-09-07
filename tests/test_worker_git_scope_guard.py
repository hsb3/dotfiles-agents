"""Tests for primitives-core/hooks/worker-git-scope-guard/hook.py.

`decide()` takes its three resolvers (branch, tree-kind, protected set) as arguments, so
every behavioural case below runs with no git repo and no activation file at all. The two
resolvers that DO touch disk get their own fixtures: tempdir activation files for the
loader, real throwaway repos for the tree-kind probe.
"""

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK_PATH = os.path.join(
    REPO_ROOT, "primitives-core", "hooks", "worker-git-scope-guard", "hook.py")

_spec = importlib.util.spec_from_file_location("worker_git_scope_guard_hook", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

WORKER = {"agent_id": "agent-1", "cwd": "/repo"}
SHARED = True
OWN_WORKTREE = False
UNKNOWN = None


def call(command, branch="feature", protected=("main",), shared=SHARED,
         payload=None, branches=None, trees=None):
    """One decide() call. `branches`/`trees` override the flat default per directory."""
    data = dict(payload or WORKER, tool_input={"command": command})
    btable = branches or {}
    ttable = trees or {}
    return hook.decide(
        data,
        lambda cwd: btable.get(cwd, branch),
        lambda cwd: ttable.get(cwd, shared),
        frozenset(protected),
    )


def blocked(*a, **kw):
    return call(*a, **kw) is not None


def reason(*a, **kw):
    out = call(*a, **kw)
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


class StashInASharedTreeTests(unittest.TestCase):
    """The observed loss: peer builders sharing one checkout, one of them stashing."""

    def test_bare_stash_in_a_shared_tree_is_denied(self):
        self.assertTrue(blocked("git stash"))

    def test_every_listed_mutating_stash_form_is_denied(self):
        for form in ("push", "pop", "apply", "drop", "clear", "branch wip",
                     "save wip", "create", "store abc123"):
            with self.subTest(form=form):
                self.assertTrue(blocked("git stash " + form))

    def test_stash_with_only_flags_is_still_the_push_form(self):
        self.assertTrue(blocked("git stash -u"))
        self.assertTrue(blocked("git stash --include-untracked -m wip"))

    def test_stash_is_denied_regardless_of_branch_and_protected_list(self):
        """Ruling D: the stash half does not depend on the key or on where HEAD is."""
        self.assertTrue(blocked("git stash", branch="feature", protected=()))
        self.assertTrue(blocked("git stash", branch=None, protected=()))

    def test_stash_reads_are_never_denied(self):
        self.assertFalse(blocked("git stash list"))
        self.assertFalse(blocked("git stash show -p"))

    def test_stash_in_the_workers_own_worktree_is_allowed(self):
        self.assertFalse(blocked("git stash", shared=OWN_WORKTREE))

    def test_stash_where_the_tree_kind_is_unknown_is_allowed(self):
        """Not a repo, no git, a bare repo, a submodule: no grounds to block."""
        self.assertFalse(blocked("git stash", shared=UNKNOWN))

    def test_the_main_session_may_stash(self):
        self.assertFalse(blocked("git stash", payload={"cwd": "/repo"}))

    def test_a_worker_identified_only_by_agent_type_is_still_a_worker(self):
        self.assertTrue(blocked("git stash", payload={"agent_type": "builder",
                                                      "cwd": "/repo"}))

    def test_the_tree_kind_is_resolved_per_directory_not_per_session(self):
        table = {"/repo/.claude/worktrees/agent-x": OWN_WORKTREE, "/repo": SHARED}
        self.assertFalse(blocked(
            "cd /repo/.claude/worktrees/agent-x && git stash", trees=table))
        self.assertTrue(blocked("git -C /repo stash", trees=table))

    def test_the_deny_names_the_hazard_and_an_alternative(self):
        text = reason("git stash")
        self.assertIn("stash", text)
        self.assertIn("commit", text)


class ProtectedBranchTests(unittest.TestCase):
    def test_a_write_on_a_protected_branch_is_denied(self):
        for sub in ("commit -m wip", "merge feature", "rebase dev",
                    "cherry-pick abc123", "revert abc123", "am patch.mbox"):
            with self.subTest(sub=sub):
                self.assertTrue(blocked("git " + sub, branch="main"))

    def test_no_verify_does_not_slip_past(self):
        self.assertTrue(blocked("git commit --no-verify -m wip", branch="main"))

    def test_a_write_on_an_unprotected_branch_is_allowed(self):
        self.assertFalse(blocked("git commit -m wip", branch="feature"))

    def test_the_protected_set_is_never_hardcoded(self):
        """No `{main, master}` default: only what the key names is protected."""
        self.assertTrue(blocked("git commit -m wip", branch="dev", protected=("dev",)))
        self.assertFalse(blocked("git commit -m wip", branch="master", protected=("dev",)))

    def test_an_empty_protected_list_makes_the_branch_half_inert(self):
        self.assertFalse(blocked("git commit -m wip", branch="main", protected=()))
        self.assertFalse(blocked("git push", branch="main", protected=()))

    def test_a_detached_head_is_not_protected(self):
        self.assertFalse(blocked("git commit -m wip", branch=None))

    def test_push_at_a_protected_refspec_is_denied(self):
        self.assertTrue(blocked("git push origin HEAD:main", branch="feature"))
        self.assertTrue(blocked("git push origin :main", branch="feature"))
        self.assertTrue(blocked("git push origin feature main", branch="feature"))

    def test_push_with_no_refspec_falls_back_to_the_current_branch(self):
        self.assertTrue(blocked("git push", branch="main"))
        self.assertTrue(blocked("git push --force", branch="main"))
        self.assertFalse(blocked("git push", branch="feature"))

    def test_an_explicit_unprotected_refspec_wins_over_a_protected_head(self):
        self.assertFalse(blocked("git push -u origin feature", branch="main"))

    def test_the_branch_half_does_not_depend_on_the_tree_being_shared(self):
        """A worktree shares .git and the remote, so its commit lands on the real branch."""
        self.assertTrue(blocked("git commit -m wip", branch="main", shared=OWN_WORKTREE))

    def test_the_main_session_is_untouched(self):
        self.assertFalse(blocked("git commit -m x", branch="main",
                                 payload={"cwd": "/repo"}))

    def test_read_only_git_never_fires(self):
        for command in ("git status", "git log --oneline main", "git diff",
                        "git show HEAD", "git rev-parse HEAD", "git branch -a"):
            with self.subTest(command=command):
                self.assertFalse(blocked(command, branch="main"))

    def test_a_cd_into_a_feature_branch_worktree_moves_the_branch_context(self):
        self.assertFalse(blocked(
            "cd /repo/.claude/worktrees/agent-x && git commit -m x",
            branches={"/repo/.claude/worktrees/agent-x": "agent-x", "/repo": "main"}))
        self.assertTrue(blocked(
            "cd /repo/.claude/worktrees/agent-x && git commit -m x",
            branches={"/repo/.claude/worktrees/agent-x": "main", "/repo": "agent-x"}))


class CommandParsingTests(unittest.TestCase):
    """Carried over from the field-tested implementation this hook was promoted from."""

    def test_a_git_literal_inside_a_quoted_string_is_not_an_invocation(self):
        self.assertFalse(blocked('echo "git stash"'))
        self.assertFalse(blocked("""python3 -c 'print("git push origin main")'""",
                                 branch="main"))

    def test_a_git_literal_inside_a_heredoc_body_is_not_an_invocation(self):
        self.assertFalse(blocked("cat <<'EOF' > notes.md\ngit stash\nEOF"))

    def test_an_unmatched_shift_operator_must_not_swallow_a_real_command(self):
        self.assertTrue(blocked("python3 -c 'print(1 << 3)'\ngit stash"))
        self.assertTrue(blocked('echo "use << foo here"\ngit stash'))

    def test_a_herestring_is_not_a_heredoc(self):
        self.assertTrue(blocked("grep -q x <<< done\ngit stash\ndone"))

    def test_an_unresolvable_cd_target_falls_back_to_the_base_cwd(self):
        for target in ("$TARGET", "~", "..", "../..", "'/repo/a;b'"):
            with self.subTest(target=target):
                self.assertTrue(blocked(
                    "cd {0} && git stash".format(target),
                    trees={"/repo": SHARED}, shared=UNKNOWN))

    def test_a_bare_newline_separated_cd_still_sets_the_directory(self):
        self.assertFalse(blocked(
            "echo hi\ncd /repo/.claude/worktrees/agent-x\ngit stash",
            trees={"/repo/.claude/worktrees/agent-x": OWN_WORKTREE, "/repo": SHARED}))

    def test_git_c_overrides_the_directory(self):
        self.assertTrue(blocked(
            "git -C /repo commit -m x",
            branches={"/repo": "main"}, branch="feature"))

    def test_a_second_invocation_after_an_allowed_one_is_still_seen(self):
        self.assertTrue(blocked("git status && git stash"))


class ProtectedBranchesKeyTests(unittest.TestCase):
    """`protected-branches:` in the activation file — the loader, on disk."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = self.tmp.name
        os.makedirs(os.path.join(self.project, ".claude"))
        saved = {n: os.environ.pop(n, None)
                 for n in ("CLAUDE_PROJECT_DIR", "ATELIER_ACTIVATION_FILE")}

        def restore():
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.addCleanup(restore)

    def write(self, text):
        path = os.path.join(self.project, ".claude", "atelier.local.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def load(self):
        return hook._load_protected_branches(self.project)

    def test_absent_file_is_inert(self):
        self.assertEqual(self.load(), frozenset())

    def test_absent_key_is_inert(self):
        self.write("---\nenforce: strict\n---\n")
        self.assertEqual(self.load(), frozenset())

    def test_block_list_form(self):
        self.write("---\nprotected-branches:\n  - main\n  - release\n---\n")
        self.assertEqual(self.load(), frozenset({"main", "release"}))

    def test_inline_list_form(self):
        self.write('---\nprotected-branches: ["main", release]\n---\n')
        self.assertEqual(self.load(), frozenset({"main", "release"}))

    def test_an_empty_list_is_inert(self):
        self.write("---\nprotected-branches: []\n---\n")
        self.assertEqual(self.load(), frozenset())

    def test_a_trailing_comment_on_the_bare_key_line_empties_the_list(self):
        """Same trap `protected:` has, and the same answer: keep the key line bare."""
        self.write("---\nprotected-branches:  # publish only\n  - main\n---\n")
        self.assertEqual(self.load(), frozenset())

    def test_no_frontmatter_is_inert(self):
        self.write("notes\n\n---\nprotected-branches:\n  - main\n---\n")
        self.assertEqual(self.load(), frozenset())

    def test_no_closing_fence_is_inert(self):
        self.write("---\nprotected-branches:\n  - main\n")
        self.assertEqual(self.load(), frozenset())

    def test_it_does_not_read_the_file_path_key(self):
        """The two keys are distinct: file paths must never become branch names."""
        self.write("---\nprotected:\n  - Makefile\n  - .github/workflows/*\n---\n")
        self.assertEqual(self.load(), frozenset())

    def test_both_keys_coexist_without_bleeding_into_each_other(self):
        self.write("---\nenforce: strict\nprotected:\n  - Makefile\n"
                   "protected-branches:\n  - main\nisolate: writers\n---\n")
        self.assertEqual(self.load(), frozenset({"main"}))

        spec = importlib.util.spec_from_file_location(
            "coexist_config_custody",
            os.path.join(REPO_ROOT, "primitives-core", "hooks", "config-custody",
                         "hook.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        mode, patterns = module._load_activation(self.project)
        self.assertEqual(mode, "strict")
        self.assertEqual(patterns, ["Makefile"])

    def test_the_env_override_points_the_loader_elsewhere(self):
        other = os.path.join(self.tmp.name, "elsewhere.md")
        with open(other, "w", encoding="utf-8") as fh:
            fh.write("---\nprotected-branches: [trunk]\n---\n")
        os.environ["ATELIER_ACTIVATION_FILE"] = other
        self.assertEqual(self.load(), frozenset({"trunk"}))

    def test_an_oversized_file_is_inert(self):
        self.write("---\nprotected-branches: [main]\n---\n"
                   + "x" * (hook.ACTIVATION_MAX_BYTES + 1))
        self.assertEqual(self.load(), frozenset())


class TreeKindTests(unittest.TestCase):
    """`shared_tree()` against real git repos — the one resolver that shells out."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.main = os.path.join(cls.tmp.name, "main")
        cls.wt = os.path.join(cls.tmp.name, "wt")
        cls.deep = os.path.join(cls.main, "sub", "deep")
        os.makedirs(cls.deep)
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.path.join(cls.tmp.name, "gitconfig"),
                   GIT_CONFIG_SYSTEM=os.path.join(cls.tmp.name, "gitconfig"),
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        cls.have_git = True
        try:
            for args in (
                ("git", "init", "-q", cls.main),
                ("git", "-C", cls.main, "commit", "-q", "--allow-empty", "-m", "x"),
                ("git", "-C", cls.main, "worktree", "add", "-q", cls.wt, "-b", "wtb"),
            ):
                subprocess.run(args, check=True, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            cls.have_git = False

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        if not self.have_git:
            self.skipTest("git unavailable")

    def test_the_main_checkout_root_is_shared(self):
        self.assertIs(hook.shared_tree(self.main), True)

    def test_a_subdirectory_of_the_main_checkout_is_still_shared(self):
        """The trap: from a subdir `--git-common-dir` is relative, so a naive
        `== ".git"` test reads the shared tree as a worktree and lets a stash through."""
        self.assertIs(hook.shared_tree(self.deep), True)

    def test_a_linked_worktree_is_not_shared(self):
        self.assertIs(hook.shared_tree(self.wt), False)

    def test_a_directory_that_is_not_a_repo_is_unknown(self):
        self.assertIsNone(hook.shared_tree(self.tmp.name))

    def test_a_nonexistent_directory_is_unknown(self):
        self.assertIsNone(hook.shared_tree(os.path.join(self.tmp.name, "nope")))


class WorktreeActivationFallbackTests(unittest.TestCase):
    """A linked worktree is a clean checkout and the activation file is conventionally
    gitignored, so a worker inside one finds no file — while still sharing the `.git` and
    remote that make a commit on a protected branch land on the real branch. The half that
    only matters inside a worktree must not be the half that switches off there.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.main = os.path.join(self.tmp.name, "main")
        self.wt = os.path.join(self.tmp.name, "wt")
        env = dict(os.environ,
                   GIT_CONFIG_GLOBAL=os.path.join(self.tmp.name, "gitconfig"),
                   GIT_CONFIG_SYSTEM=os.path.join(self.tmp.name, "gitconfig"),
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        try:
            for args in (
                ("git", "init", "-q", "-b", "trunk", self.main),
                ("git", "-C", self.main, "commit", "-q", "--allow-empty", "-m", "x"),
                ("git", "-C", self.main, "worktree", "add", "-q", self.wt, "-b", "shipped"),
            ):
                subprocess.run(args, check=True, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git unavailable")

        saved = {n: os.environ.pop(n, None)
                 for n in ("CLAUDE_PROJECT_DIR", "ATELIER_ACTIVATION_FILE")}

        def restore():
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.addCleanup(restore)

    def arm(self, root, *branches):
        os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
        with open(os.path.join(root, ".claude", "atelier.local.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("---\nprotected-branches: [{0}]\n---\n".format(", ".join(branches)))

    def run_main(self, command, cwd):
        stdin, stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(json.dumps(
            {"agent_id": "a", "cwd": cwd, "tool_input": {"command": command}}))
        sys.stdout = io.StringIO()
        try:
            hook.main()
            return sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = stdin, stdout

    def test_a_worker_in_a_bare_worktree_inherits_the_main_checkouts_list(self):
        self.arm(self.main, "trunk", "shipped")
        self.assertEqual(hook._load_protected_branches(self.wt),
                         frozenset({"trunk", "shipped"}))

    def test_a_commit_on_a_protected_branch_from_a_bare_worktree_is_denied(self):
        self.arm(self.main, "shipped")
        out = self.run_main("git commit -m wip", self.wt)
        self.assertIn("protected branch `shipped`", out)

    def test_the_fallback_does_not_leak_into_the_stash_half(self):
        """A worker in its own worktree may still stash, however it resolved the list."""
        self.arm(self.main, "shipped")
        self.assertEqual(self.run_main("git stash", self.wt), "")

    def test_the_worktrees_own_activation_file_wins(self):
        self.arm(self.main, "shipped")
        self.arm(self.wt, "trunk")
        self.assertEqual(hook._load_protected_branches(self.wt), frozenset({"trunk"}))
        self.assertEqual(self.run_main("git commit -m wip", self.wt), "")

    def test_the_env_override_wins_over_both(self):
        self.arm(self.main, "shipped")
        self.arm(self.wt, "shipped")
        elsewhere = os.path.join(self.tmp.name, "elsewhere.md")
        with open(elsewhere, "w", encoding="utf-8") as fh:
            fh.write("---\nprotected-branches: [trunk]\n---\n")
        os.environ["ATELIER_ACTIVATION_FILE"] = elsewhere
        self.assertEqual(hook._load_protected_branches(self.wt), frozenset({"trunk"}))

    def test_the_main_checkout_does_not_walk_anywhere(self):
        """No fallback applies in the main checkout: no file there means inert."""
        self.assertEqual(hook._load_protected_branches(self.main), frozenset())

    def test_a_directory_that_is_not_a_repo_is_inert(self):
        self.assertEqual(hook._load_protected_branches(self.tmp.name), frozenset())


class EntryPointTests(unittest.TestCase):
    """main() end to end: stdin in, at most one JSON object out, always exit 0."""

    def run_main(self, payload, monkey=None):
        stdin, stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(payload if isinstance(payload, str)
                                else json.dumps(payload))
        sys.stdout = io.StringIO()
        saved = {}
        try:
            for name, value in (monkey or {}).items():
                saved[name] = getattr(hook, name)
                setattr(hook, name, value)
            hook.main()
            return sys.stdout.getvalue()
        finally:
            for name, value in saved.items():
                setattr(hook, name, value)
            sys.stdin, sys.stdout = stdin, stdout

    def test_malformed_stdin_is_silent(self):
        self.assertEqual(self.run_main("not json"), "")

    def test_a_non_dict_payload_is_silent(self):
        self.assertEqual(self.run_main("[1, 2]"), "")

    def test_the_main_session_is_silent(self):
        self.assertEqual(
            self.run_main({"cwd": "/repo", "tool_input": {"command": "git stash"}}), "")

    def test_a_deny_prints_one_pretooluse_object(self):
        out = self.run_main(
            {"agent_id": "a", "cwd": "/repo", "tool_input": {"command": "git stash"}},
            monkey={"shared_tree": lambda cwd: True,
                    "_load_protected_branches": lambda project: frozenset()})
        payload = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(payload["hookEventName"], "PreToolUse")
        self.assertEqual(payload["permissionDecision"], "deny")
        self.assertTrue(payload["permissionDecisionReason"])

    def test_a_raising_resolver_fails_open(self):
        def boom(cwd):
            raise RuntimeError("resolver exploded")

        out = self.run_main(
            {"agent_id": "a", "cwd": "/repo", "tool_input": {"command": "git stash"}},
            monkey={"shared_tree": boom,
                    "_load_protected_branches": lambda project: frozenset()})
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()

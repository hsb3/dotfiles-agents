"""Tests for primitives-core/hooks/worker-git-scope-guard/hook.py.

`decide()` takes its resolvers (branch, tree-kind, protected set, ownership) as arguments, so
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
LINKED = False  # a linked worktree; `owned` (default True in `call()`) says whose it is
UNKNOWN = None


def call(command, branch="feature", protected=("main",), shared=SHARED,
         payload=None, branches=None, trees=None, owned=True):
    """One decide() call. `branches`/`trees` override the flat default per directory."""
    data = dict(payload or WORKER, tool_input={"command": command})
    btable = branches or {}
    ttable = trees or {}
    return hook.decide(
        data,
        lambda cwd: btable.get(cwd, branch),
        lambda cwd: ttable.get(cwd, shared),
        frozenset(protected),
        lambda cwd: owned,
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
        self.assertFalse(blocked("git stash", shared=LINKED))

    def test_stash_where_the_tree_kind_is_unknown_is_allowed(self):
        """Not a repo, no git, a bare repo, a submodule: no grounds to block."""
        self.assertFalse(blocked("git stash", shared=UNKNOWN))

    def test_the_main_session_may_stash(self):
        self.assertFalse(blocked("git stash", payload={"cwd": "/repo"}))

    def test_a_worker_identified_only_by_agent_type_is_still_a_worker(self):
        self.assertTrue(blocked("git stash", payload={"agent_type": "builder",
                                                      "cwd": "/repo"}))

    def test_the_tree_kind_is_resolved_per_directory_not_per_session(self):
        table = {"/repo/.claude/worktrees/agent-x": LINKED, "/repo": SHARED}
        self.assertFalse(blocked(
            "cd /repo/.claude/worktrees/agent-x && git stash", trees=table))
        self.assertTrue(blocked("git -C /repo stash", trees=table))

    def test_the_deny_names_the_hazard_and_an_alternative(self):
        text = reason("git stash")
        self.assertIn("stash", text)
        self.assertIn("commit", text)


class StashInALinkedWorktreeTests(unittest.TestCase):
    """refs/stash is repo-wide: every worktree of the repo reads and writes one stack."""

    FIVE = ("push -u", "pop", "apply", "drop stash@{0}", "clear")

    def test_a_linked_worktree_the_worker_does_not_own_denies_every_form(self):
        for form in self.FIVE + ("", "save wip", "branch wip"):
            with self.subTest(form=form):
                self.assertTrue(blocked("git stash " + form, shared=LINKED, owned=False))

    def test_the_stack_destroying_forms_are_denied_even_in_the_workers_own_worktree(self):
        for form in ("pop", "drop stash@{0}", "clear", "branch wip"):
            with self.subTest(form=form):
                self.assertTrue(blocked("git stash " + form, shared=LINKED, owned=True))

    def test_pushing_and_applying_in_the_workers_own_worktree_is_allowed(self):
        for form in ("", "push -u", "-u", "apply", "save wip"):
            with self.subTest(form=form):
                self.assertFalse(blocked("git stash " + form, shared=LINKED, owned=True))

    def test_the_main_checkout_denies_every_form_whoever_owns_what(self):
        for form in self.FIVE:
            with self.subTest(form=form):
                self.assertTrue(blocked("git stash " + form, shared=SHARED, owned=True))

    def test_an_unknown_tree_denies_the_destroying_forms(self):
        """The stack is repo-wide, so tree kind is irrelevant to a destroying form."""
        for form in ("pop", "drop", "clear", "branch wip"):
            with self.subTest(form=form):
                self.assertTrue(blocked("git stash " + form, shared=UNKNOWN, owned=False))

    def test_an_unknown_tree_still_allows_the_push_form(self):
        self.assertFalse(blocked("git stash push", shared=UNKNOWN, owned=False))

    def test_reads_are_never_denied_in_an_unowned_linked_worktree(self):
        self.assertFalse(blocked("git stash list", shared=LINKED, owned=False))
        self.assertFalse(blocked("git stash show -p", shared=LINKED, owned=False))

    def test_the_main_session_is_untouched_in_a_linked_worktree(self):
        self.assertFalse(blocked("git stash drop", shared=LINKED, owned=False,
                                 payload={"cwd": "/repo"}))

    def test_the_deny_says_the_stack_is_repo_wide_and_offers_a_non_stash_route(self):
        text = reason("git stash pop", shared=LINKED, owned=True)
        self.assertIn("every worktree", text)
        self.assertIn("git apply -R", text)
        self.assertIn("`git stash list` and `git stash show` are reads", text)


class ShellWrapperAndAltGitFormsTests(unittest.TestCase):
    """`invocations()` must reach a stash destroyer behind a shell `-c` string or an
    absolute git path, and catch the two non-`stash` subcommands that reach the same
    repo-wide ref. A quoted prose string must still read as no invocation at all.
    """

    def test_bash_dash_c_wrapping_a_stash_destroyer_is_denied(self):
        self.assertTrue(blocked("bash -c 'git stash drop'"))

    def test_sh_dash_c_wrapping_a_stash_destroyer_is_denied(self):
        self.assertTrue(blocked('sh -c "git stash clear"'))

    def test_zsh_dash_c_wrapping_a_stash_destroyer_is_denied(self):
        self.assertTrue(blocked("zsh -c 'git stash pop'"))

    def test_a_flag_cluster_dash_c_is_still_recognised(self):
        self.assertTrue(blocked("bash -lc 'git stash drop'"))

    def test_an_absolute_git_path_is_still_git(self):
        self.assertTrue(blocked("/usr/bin/git stash drop"))

    def test_update_ref_deleting_the_stash_ref_is_denied(self):
        self.assertTrue(blocked("git update-ref -d refs/stash"))

    def test_update_ref_m_message_value_matching_stash_is_allowed(self):
        self.assertFalse(blocked("git update-ref -m stash refs/heads/x abc123"))

    def test_reflog_delete_on_a_stash_entry_is_denied(self):
        self.assertTrue(blocked("git reflog delete refs/stash@{0}"))

    def test_a_quoted_prose_string_is_not_an_invocation(self):
        self.assertFalse(blocked('echo "git stash drop"'))

    def test_a_read_form_inside_a_shell_c_still_reads_as_a_read(self):
        self.assertFalse(blocked("bash -c 'git stash list'"))

    def test_reflog_show_on_the_stash_ref_is_a_read(self):
        self.assertFalse(blocked("git reflog show refs/stash"))

    def test_an_apostrophe_in_a_comment_does_not_hide_the_next_line(self):
        self.assertTrue(blocked("git log --oneline # what's new\ngit stash drop"))

    def test_a_separator_inside_a_comment_is_not_a_command(self):
        self.assertFalse(blocked("echo hi # a && git stash drop"))

    def test_an_ansi_c_quoted_dash_c_string_is_decoded(self):
        self.assertTrue(blocked("bash -c $'git stash drop'"))
        self.assertTrue(blocked("bash -c $'echo hi\\ngit stash drop'"))

    def test_a_backgrounded_command_does_not_hide_the_next(self):
        self.assertTrue(blocked("git stash list & git stash drop"))

    def test_a_subshell_or_substitution_is_still_read(self):
        self.assertTrue(blocked("(git stash drop)"))
        self.assertTrue(blocked("echo $(git stash drop)"))

    def test_a_redirect_ampersand_is_not_a_command(self):
        self.assertFalse(blocked("git stash list 2>&1 &>/dev/null"))

    def test_a_shell_word_after_git_is_an_argument_not_a_wrapper(self):
        # PR 587 review: `-C sh` / `-C ./zsh` must not turn the outer git call into a
        # recursion into git's own `-c` config value
        self.assertTrue(blocked("git -C sh -c a.b=1 stash drop"))
        self.assertTrue(blocked("git -C ./zsh -c a.b=1 stash drop"))
        self.assertTrue(blocked("git -C sh -c a.b=1 commit -m x", branch="main"))

    def test_update_ref_saving_the_stash_as_a_branch_is_allowed(self):
        self.assertFalse(blocked("git update-ref refs/heads/rescue stash"))

    def test_a_long_option_before_dash_c_is_skipped(self):
        self.assertTrue(blocked("bash --norc -c 'git stash drop'"))

    def test_dash_o_consumes_its_value_before_dash_c(self):
        self.assertTrue(blocked("bash -o pipefail -c 'git stash drop'"))

    def test_an_uppercase_git_is_still_git(self):
        self.assertTrue(blocked("GIT stash drop"))

    def test_reflog_expire_all_reaches_the_stash_ref(self):
        self.assertTrue(blocked("git reflog expire --expire=now --all"))

    def test_a_separator_inside_the_dash_c_string_is_still_denied(self):
        for command in (
            "bash -c 'cd /tmp && git stash drop'",
            "bash -c 'git stash list; git stash drop'",
            'sh -c "git fetch || git stash pop"',
            'bash -c "git stash drop && echo done"',
            "bash -c 'git stash drop\necho x'",  # a real newline inside plain '...' quotes
        ):
            with self.subTest(command=command):
                self.assertTrue(blocked(command))

    def test_a_prefix_before_the_shell_word_does_not_hide_the_wrapper(self):
        for command in (
            "env bash -c 'git stash drop'",
            "sudo bash -c 'git stash drop'",
            "exec bash -c 'git stash drop'",
            "nohup sh -c 'git stash drop'",
            "timeout 5 bash -c 'git stash drop'",
        ):
            with self.subTest(command=command):
                self.assertTrue(blocked(command))

    def test_dash_c_dashdash_still_finds_the_string(self):
        self.assertTrue(blocked("bash -c -- 'git stash drop'"))

    def test_value_taking_shell_options_before_dash_c_are_skipped(self):
        for command in (
            "bash -O extglob -c 'git stash drop'",
            "bash --rcfile /dev/null -c 'git stash drop'",
        ):
            with self.subTest(command=command):
                self.assertTrue(blocked(command))


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
        self.assertTrue(blocked("git commit -m wip", branch="main", shared=LINKED))

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

    def test_a_heredoc_opener_counts_only_outside_quotes_and_comments(self):
        # Each has a later line equal to the word, so a raw-text match would
        # drop the real `git stash` line in between.
        for command in (
            "# write the notes file with <<EOF below\n"
            "git stash\ncat > notes.md <<EOF\nbody\nEOF",
            "grep -q '<<EOF' gen.sh &&\n  git stash\ncat > f <<EOF\nbody\nEOF",
            "echo $(( 1 <<3 ))\ngit stash\n3",
            'echo "a\n<<EOF"\ngit stash\nEOF',
            "echo $(( 1 << n ))\ngit stash\nn",
            "(( y = 1 << n ))\ngit stash\nn",
        ):
            with self.subTest(command=command):
                self.assertTrue(blocked(command))

    def test_a_comment_after_a_separator_and_an_ansi_c_string_open_no_heredoc(self):
        for command in ('echo "<<Z" ;# <<A\ngit push\nA',
                        "echo \"<<Z\" $'a\\' <<A'\ngit push\nA"):
            with self.subTest(command=command):
                self.assertEqual(
                    [v for v, _, _ in hook.invocations(command, "/tmp")], ["push"])

    def test_a_herestring_is_not_a_heredoc(self):
        self.assertTrue(blocked("grep -q x <<< done\ngit stash\ndone"))

    def test_an_unresolvable_cd_target_falls_back_to_the_base_cwd(self):
        for target in ("$TARGET", "~", "..", "../.."):
            with self.subTest(target=target):
                self.assertTrue(blocked(
                    "cd {0} && git stash".format(target),
                    trees={"/repo": SHARED}, shared=UNKNOWN))

    def test_a_quoted_cd_target_with_a_separator_character_is_one_argument(self):
        """A quote-aware split must not fragment the quoted `cd` target on the `;`
        inside it — that would carry the old raw-text-split bug into `cd` resolution
        too. The resolved target is an absolute path, so `_cd_resolves` trusts it
        as-is, same as any other absolute `cd` target."""
        self.assertEqual(
            [w for _, _, w in hook.invocations("cd '/repo/a;b' && git stash", "/repo")],
            ["/repo/a;b"])

    def test_an_ansi_c_quoted_separator_does_not_split(self):
        self.assertEqual(hook._split_commands("echo $'a;b' && git stash"),
                         ["echo $'a;b' ", " git stash"])

    def test_a_bare_newline_separated_cd_still_sets_the_directory(self):
        self.assertFalse(blocked(
            "echo hi\ncd /repo/.claude/worktrees/agent-x\ngit stash",
            trees={"/repo/.claude/worktrees/agent-x": LINKED, "/repo": SHARED}))

    def test_git_c_overrides_the_directory(self):
        self.assertTrue(blocked(
            "git -C /repo commit -m x",
            branches={"/repo": "main"}, branch="feature"))

    def test_a_relative_git_c_resolves_against_the_payload_cwd(self):
        lane = "/repo/main/../lane"
        self.assertEqual(
            [w for _, _, w in hook.invocations("git -C ../lane stash push", "/repo/main")],
            [lane])
        self.assertFalse(blocked("git -C ../lane stash push",
                                 payload={"agent_id": "a", "cwd": "/repo/main"},
                                 trees={lane: LINKED}, shared=SHARED))

    def test_a_relative_git_c_after_a_cd_resolves_against_the_cd(self):
        self.assertEqual(
            [w for _, _, w in hook.invocations("cd /a && git -C b stash", "/repo")],
            ["/a/b"])

    def test_an_absolute_git_c_stays_absolute(self):
        self.assertEqual(
            [w for _, _, w in hook.invocations("git -C /x stash", "/repo")], ["/x"])

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

    def test_a_trailing_comment_on_the_bare_key_line_still_reads_the_list(self):
        """A comment where the value belongs is not a value.

        This answer INVERTED when the seven private parsers were consolidated onto
        `_lib/atelier_local.py` (card ef7m): this hook used to read `# publish only`
        as the key's value, so the block never opened and the list came back empty,
        while the handoff hooks and context-watermark already read the same shape as
        an empty value. One rule now, and it is YAML's.
        """
        self.write("---\nprotected-branches:  # publish only\n  - main\n---\n")
        self.assertEqual(self.load(), frozenset({"main"}))

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
        saved = hook.owned_worktree
        hook.owned_worktree = lambda data: os.path.realpath(self.wt)
        try:
            self.assertEqual(self.run_main("git stash", self.wt), "")
        finally:
            hook.owned_worktree = saved

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


class OwnedWorktreeCodexBranchTests(unittest.TestCase):
    """`owned_worktree()`'s Codex path: the registry record, never the native sidecar."""

    def setUp(self):
        saved_is_codex, saved_lookup = hook.codex_workers.is_codex, hook.codex_workers.lookup
        self.addCleanup(setattr, hook.codex_workers, "is_codex", saved_is_codex)
        self.addCleanup(setattr, hook.codex_workers, "lookup", saved_lookup)
        hook.codex_workers.is_codex = lambda data: True

    def test_a_registry_worktree_resolves_to_its_realpath(self):
        with tempfile.TemporaryDirectory() as tmp:
            hook.codex_workers.lookup = lambda data: {"worktree": tmp}
            self.assertEqual(hook.owned_worktree({}), os.path.realpath(tmp))

    def test_no_registry_record_is_not_ownership(self):
        hook.codex_workers.lookup = lambda data: None
        self.assertIsNone(hook.owned_worktree({}))


class StashOwnershipEndToEndTests(unittest.TestCase):
    """main() against a real linked worktree and a real sidecar layout.

    The sidecar is where Claude Code records `worktreePath` for an isolation: worktree
    dispatch; without it the subagent is a guest in whatever linked tree it runs in.
    """

    FIVE = ("push -u", "pop", "apply", "drop stash@{0}", "clear")

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
                ("git", "init", "-q", self.main),
                ("git", "-C", self.main, "commit", "-q", "--allow-empty", "-m", "x"),
                ("git", "-C", self.main, "worktree", "add", "-q", self.wt, "-b", "lane"),
            ):
                subprocess.run(args, check=True, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("git unavailable")
        project = os.path.join(self.tmp.name, "projects", "slug")
        self.subagents = os.path.join(project, "sess", "subagents")
        os.makedirs(self.subagents)
        self.transcript = os.path.join(project, "sess.jsonl")

        saved = {n: os.environ.pop(n, None)
                 for n in ("CLAUDE_PROJECT_DIR", "ATELIER_ACTIVATION_FILE",
                           "ATELIER_HARNESS")}

        def restore():
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.addCleanup(restore)

    def sidecar(self, **extra):
        with open(os.path.join(self.subagents, "agent-x.meta.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(dict({"agentType": "pb-builder"}, **extra), fh)

    def payload(self, command, cwd):
        return json.dumps(
            {"agent_id": "x", "agent_type": "pb-builder", "cwd": cwd or self.wt,
             "transcript_path": self.transcript, "hook_event_name": "PreToolUse",
             "tool_name": "Bash", "tool_input": {"command": command}})

    def run_subprocess(self, command, cwd):
        """The hook as its own process, whose cwd (/) is NOT the payload cwd."""
        return subprocess.run([sys.executable, HOOK_PATH], cwd="/",
                              input=self.payload(command, cwd), capture_output=True,
                              text=True, timeout=30).stdout

    def run_main(self, command, cwd=None):
        stdin, stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(self.payload(command, cwd))
        sys.stdout = io.StringIO()
        try:
            hook.main()
            return sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = stdin, stdout

    def assert_denied(self, out):
        payload = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(payload["permissionDecision"], "deny")
        self.assertIn("every worktree", payload["permissionDecisionReason"])

    def test_a_sidecar_without_worktree_path_denies_every_form(self):
        self.sidecar()
        for form in self.FIVE:
            with self.subTest(form=form):
                self.assert_denied(self.run_main("git stash " + form))

    def test_no_sidecar_at_all_denies_every_form(self):
        for form in self.FIVE:
            with self.subTest(form=form):
                self.assert_denied(self.run_main("git stash " + form))

    def test_a_sidecar_naming_another_tree_is_not_ownership(self):
        self.sidecar(worktreePath=self.main)
        self.assert_denied(self.run_main("git stash push -u"))

    def test_the_owned_worktree_may_push_and_apply_but_not_destroy(self):
        self.sidecar(worktreePath=self.wt)
        for form in ("push -u", "apply"):
            with self.subTest(form=form):
                self.assertEqual(self.run_main("git stash " + form), "")
        for form in ("pop", "drop stash@{0}", "clear"):
            with self.subTest(form=form):
                self.assert_denied(self.run_main("git stash " + form))

    def test_a_subdirectory_of_the_owned_worktree_is_still_owned(self):
        self.sidecar(worktreePath=self.wt)
        sub = os.path.join(self.wt, "sub")
        os.makedirs(sub)
        self.assertEqual(self.run_main("git stash push", cwd=sub), "")

    def test_a_relative_git_c_resolves_against_the_payload_cwd_not_the_process_cwd(self):
        self.sidecar(worktreePath=self.wt)
        self.assert_denied(self.run_subprocess("git -C ../wt stash drop", self.main))
        self.assertEqual(self.run_subprocess("git -C ../wt stash push", self.main), "")

    def test_a_worktree_of_a_bare_repo_still_denies_the_destroying_forms(self):
        bare = os.path.join(self.tmp.name, "bare.git")
        bwt = os.path.join(self.tmp.name, "bwt")
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.path.join(self.tmp.name, "gitconfig"),
                   GIT_CONFIG_SYSTEM=os.path.join(self.tmp.name, "gitconfig"))
        for args in (("git", "clone", "-q", "--bare", self.main, bare),
                     ("git", "-C", bare, "worktree", "add", "-q", bwt, "-b", "blane")):
            subprocess.run(args, check=True, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertIsNone(hook.shared_tree(bwt))  # the premise: tree kind unknown
        for form in ("drop", "clear"):
            with self.subTest(form=form):
                self.assert_denied(self.run_subprocess("git stash " + form, bwt))


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

    def test_an_uppercase_git_still_loads_protected_branches(self):
        """The precheck gating `_load_protected_branches` must not be case-sensitive,
        or `GIT push origin main` skips the load and the branch stays unprotected."""
        out = self.run_main(
            {"agent_id": "a", "cwd": "/repo", "tool_input": {"command": "GIT push origin main"}},
            monkey={"current_branch": lambda cwd: "main",
                    "_load_protected_branches": lambda project: frozenset({"main"})})
        payload = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(payload["permissionDecision"], "deny")

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

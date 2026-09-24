"""Differential test: both git-guard parsers against a real bash.

Each probe command runs under every bash found (`/bin/bash`, and `bash` on PATH
when it resolves elsewhere; no version assumed) with a fake `git` first on PATH
that logs its argv as one JSON line and exits 0. Every logged argv whose verb is
in that guard's fixed write set (`WRITES`, independent of the guard's own
classifier) must make the guard flag the probe as written. A guard that flags
while bash ran nothing is conservative and passes; the reverse is not asserted.

The guards are read through their pure parser entry points, so no payload,
sidecar or worktree state is needed:

- live-worker-git-guard: `_first_mutating_verb(_tokens(command))`.
- worker-git-scope-guard: `decide()` with the most restrictive resolvers (every
  tree shared, every branch protected), so it flags every call it could ever deny.

Probes never reach the real git: `{GIT}` is replaced with the fake's absolute
path, PATH is `<fake dir>:/usr/bin:/bin`, GIT_DIR names no repo, and the fake dir
also shadows `bash` and `zsh` with the bash under test, so `zsh -c` needs no zsh
installed. `sh` is not shadowed: it is the system `/bin/sh`, which still finds the
fake git on PATH.
Stdlib-only.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HOOKS_ROOT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "primitives-core", "hooks")


def _load(name, subdir):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(HOOKS_ROOT, subdir, "hook.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LIVE = _load("_diff_live_git_guard", "live-worker-git-guard")
SCOPE = _load("_diff_scope_git_guard", "worker-git-scope-guard")


class _Everything:
    """A protected-branch set that holds every name: arms the push/write half for
    every call, so `decide` reports every call it could deny."""

    def __contains__(self, _name):
        return True

    def __bool__(self):
        return True


def live_flags(command):
    return LIVE._first_mutating_verb(LIVE._tokens(command))[0] is not None


def scope_flags(command, cwd="/tmp"):
    data = {"agent_id": "differential", "cwd": cwd,
            "tool_input": {"command": command}}
    return SCOPE.decide(data, branch_of=lambda _d: "main",
                        shared_of=lambda _d: True, protected=_Everything(),
                        owns=lambda _d: False) is not None


GUARDS = {"live": live_flags, "scope": scope_flags}

# Write verbs each guard must catch, as an argv prefix after git's global options.
# Deliberately not read from the hooks, so a guard that goes blind fails here.
_COMMON_WRITES = [("commit",), ("push",), ("rebase",), ("merge",), ("stash", "push"),
                  ("stash", "drop"), ("stash", "clear"), ("stash", "pop"),
                  ("stash", "apply"), ("update-ref",)]
WRITES = {
    "live": _COMMON_WRITES + [("reset",), ("checkout",)],
    "scope": _COMMON_WRITES + [("reflog", "delete"), ("reflog", "expire")],
}


def _subcommand(argv):
    """argv after git's global options; a bare `stash` is `stash push`."""
    i = 0
    while i < len(argv) and argv[i].startswith("-"):
        i += 2 if argv[i] in ("-C", "-c") else 1
    rest = argv[i:]
    return ["stash", "push"] if rest == ["stash"] else rest


def is_write(guard, argv):
    rest = _subcommand(argv)
    return any(rest[:len(w)] == list(w) for w in WRITES[guard])

# (name, command). `{GIT}` becomes the fake git's absolute path; str.replace,
# not format, since probes carry literal braces.
PROBES = [
    # plain
    ("plain_commit", "git commit -m x"),
    ("plain_push", "git push"),
    ("plain_stash_drop", "git stash drop"),
    ("neg_echo_dq", 'echo "git commit"'),
    ("neg_echo_sq", "echo 'git push'"),
    ("neg_status", "git status"),
    # heredocs
    ("hd_quoted_body", "cat <<'EOF'\ngit commit -m x\nEOF"),
    ("hd_quoted_then_git", "cat <<'EOF'\nbody\nEOF\ngit commit -m x"),
    ("hd_dq_word_then_git", 'cat <<"EOF"\nbody\nEOF\ngit push'),
    ("hd_unquoted_body", "cat <<EOF\ngit stash drop\nEOF"),
    ("hd_unquoted_then_git", "cat <<EOF\nbody $HOME\nEOF\ngit commit -m x"),
    ("hd_dash_tabs_then_git", "cat <<-EOF\n\tbody\n\tEOF\ngit commit -m x"),
    ("hd_dash_tabs_body", "cat <<-EOF\n\tgit push\n\tEOF"),
    ("hd_dash_tab_continuation",
     "cat <<-EOF\n\tbody \\\n\tmore\n\tEOF\ngit commit -m x"),
    ("hd_dash_tab_split_terminator",
     "cat <<-EOF\n\tbody\n\tEO\\\n\tF\ngit commit -m x\nEOF"),
    ("hd_split_terminator", "cat <<EOF\nbody\nEO\\\nF\ngit commit -m x"),
    ("hd_split_terminator_quoted",
     "cat <<'EOF'\nbody\nEO\\\nF\ngit commit -m x\nEOF"),
    ("hd_even_backslash", "cat <<EOF\nbody\\\\\nEOF\ngit commit -m x"),
    ("hd_odd_backslash_joins_terminator",
     "cat <<EOF\nbody\\\nEOF\ngit commit -m x\nEOF"),
    ("hd_odd3_backslash", "cat <<EOF\nbody\\\\\\\nEOF\ngit push\nEOF"),
    ("hd_joined_leading_space", "cat <<EOF\nbody\n \\\nEOF\ngit commit -m x\nEOF"),
    ("hd_joined_trailing_space", "cat <<EOF\nbody\nEO\\\nF \ngit commit -m x\nEOF"),
    ("hd_leading_space_terminator", "cat <<EOF\nbody\n EOF\ngit commit -m x\nEOF"),
    ("hd_crlf_opener", "cat <<EOF\r\nbody\r\nEOF\r\ngit commit -m x"),
    ("hd_crlf_opener_lf_terminator",
     "cat <<EOF\r\nbody\nEOF\ngit commit -m x\nEOF\r"),
    ("hd_two_openers_then_git", "cat <<A <<B\na\nA\nb\nB\ngit commit -m x"),
    ("hd_two_openers_git_in_second", "cat <<A <<B\na\nA\ngit push\nB"),
    ("hd_two_openers_git_after_first", "cat <<A <<B\na\nA\ngit push\nB\ngit stash"),
    # a terminator the parser misplaces shows only when a later line hides a call
    ("hd_split_terminator_then_eof", "cat <<EOF\nbody\nEO\\\nF\ngit commit -m x\nEOF"),
    ("hd_dash_tab_backslash_then_eof",
     "cat <<-EOF\n\t\\\n\tEOF\ngit commit -m x\nEOF"),
    ("hd_joined_leading_space_chain",
     "cat <<EOF\n E\\\nOF\ncat <<X\nEOF\ngit commit -m x\nX"),
    ("hd_dash_space_indent_chain", "cat <<-EOF\n  EOF\ncat <<X\nEOF\ngit commit -m x\nX"),
    ("hd_trailing_space_chain", "cat <<EOF\nEOF \ncat <<X\nEOF\ngit commit -m x\nX"),
    ("hd_two_openers_chain", "cat <<A <<B\nx\nA\ncat <<Y\nB\ngit commit -m x\nY"),
    ("hd_crlf_opener_then_eof", "cat <<EOF\r\nbody\nEOF\r\ngit commit -m x\nEOF"),
    ("hd_crlf_line_chain", "cat <<EOF\nEOF\r\ncat <<X\nEOF\ngit commit -m x\nX"),
    ("hd_digit_word", "cat <<1\ngit commit -m x\n1"),
    ("hd_herestring", "cat <<< 'x'\ngit commit -m x"),
    ("hd_unterminated", "cat <<EOF\ngit commit -m x"),
    ("hd_opener_in_sq", "echo 'cat <<EOF'\ngit commit -m x\nEOF"),
    ("hd_opener_in_dq", 'echo "<<EOF"\ngit push\nEOF'),
    ("hd_opener_in_comment", "true # cat <<EOF\ngit commit -m x\nEOF"),
    ("hd_then_separator_git", "cat <<EOF && git push\nbody\nEOF"),
    ("hd_backslash_word_plain", "cat <<\\EOF\nbody\nEOF\ngit commit -m x"),
    # O1 and O2: known gaps, excused below
    ("O1_backslash_word_apostrophe", "cat <<\\EOF\nit's\nEOF\ngit commit -m x"),
    ("O1_partial_quote_apostrophe", 'cat <<E"O"F\nit\'s\nEOF\ngit commit -m x'),
    ("O2_paren_terminator",
     "x=$(cat <<EOF\nbody\nEOF)\ngit commit -m x\nEOF\n)"),
    # arithmetic (PR 580)
    ("arith_cmd_shift", "x=1\n((x<<2))\ngit commit -m x"),
    ("arith_expansion", "echo $((1<<2))\ngit commit -m x"),
    ("arith_cmd_shift_word", "(( y = 1 << EOF ))\ngit commit -m x\nEOF"),
    ("arith_expansion_word", "echo $(( 1 << EOF ))\ngit stash drop\nEOF"),
    ("arith_shift_assign", "y=1\n(( y <<= EOF ))\ngit push\nEOF"),
    # shells, absolute path, stash ref plumbing (PR 587)
    ("sh_bash_c", "bash -c 'git stash drop'"),
    ("sh_sh_c", 'sh -c "git stash clear"'),
    ("sh_zsh_c", "zsh -c 'git stash pop'"),
    # a flag cluster holding -c; never -l, whose profile resets PATH to the real git
    ("sh_bash_ec", "bash -ec 'git commit -m x'"),
    ("sh_env_bash_c", "env bash -c 'git stash drop'"),
    ("sh_bash_c_heredoc_body", "bash -c 'cat <<EOF\ngit stash drop\nEOF\n'"),
    ("sh_bash_c_heredoc_then_git", "bash -c 'cat <<EOF\nx\nEOF\ngit stash drop'"),
    ("abs_git_stash_drop", "{GIT} stash drop"),
    ("abs_git_commit", "{GIT} commit -m x"),
    ("git_C_stash_drop", "git -C . stash drop"),
    ("git_C_sh_c_config", "git -C sh -c k=v stash drop"),
    ("update_ref_stash", "git update-ref -d refs/stash"),
    ("reflog_delete_stash", "git reflog delete refs/stash@{0}"),
    ("reflog_expire_all", "git reflog expire --all"),
    # separators inside vs outside quotes
    ("sep_sq_semicolon", "echo 'a; git commit -m x'"),
    ("sep_dq_and", 'echo "a && git push"'),
    ("sep_sq_pipe", "echo 'a | git push'"),
    ("sep_sq_newline", "echo 'a\ngit commit -m x'"),
    ("sep_dq_newline", 'echo "a\ngit commit -m x"'),
    ("sep_semicolon", "true; git commit -m x"),
    ("sep_and", "true && git push"),
    ("sep_or", "false || git commit -m x"),
    ("sep_pipe", "echo x | git commit -F -"),
    ("sep_newline", "true\ngit stash"),
    ("sep_after_sq_juggle", "echo 'it'\"'\"'s'; git commit -m x"),
    ("sep_after_ansi_c", "echo $'a\\'b'; git commit -m x"),
    ("sep_after_escaped_dq", 'echo "a\\"b"; git push'),
    ("sep_dq_multiline_then_git", 'echo "a\nb;"\ngit push'),
    ("sep_subshell", "( git commit -m x )"),
    ("sep_brace_group", "{ git push; }"),
    ("sep_if_then", "if true; then git commit -m x; fi"),
    ("sep_for_do", "for i in 1; do git stash; done"),
    ("sep_glued", "true&&git commit -m x"),
    ("sep_comment_apostrophe", "true # it's\ngit commit -m x"),
    ("sep_assignment_prefix", "GIT_AUTHOR_NAME=x git commit -m x"),
]

# Known bypasses: (probe, guard) -> where the gap is recorded. Each cell must
# still fail; once a fix makes it pass, delete its entry here.
_O1 = "O1, live-worker-git-guard README (opener not recognized) and ledger 0428"
_O2 = "O2, `EOF)` terminator inside $( ), ledger 0428"
EXCUSED = {
    ("O1_backslash_word_apostrophe", "live"): _O1,
    ("O1_partial_quote_apostrophe", "live"): _O1,
    ("O2_paren_terminator", "live"): _O2,
    ("O2_paren_terminator", "scope"): _O2,
}
# live-worker-git-guard README "What it cannot see": `bash -c "..."` and a command
# word glued to a separator displace the git word.
for _name in ("sh_bash_c", "sh_sh_c", "sh_zsh_c", "sh_bash_ec", "sh_env_bash_c",
              "sh_bash_c_heredoc_then_git"):
    EXCUSED[(_name, "live")] = "live README ceiling: bash -c string"
EXCUSED[("sep_glued", "live")] = "live README ceiling: word glued to a separator"


def _bashes():
    found, seen = [], set()
    for path in ("/bin/bash", shutil.which("bash")):
        if path and os.path.exists(path):
            real = os.path.realpath(path)
            if real not in seen:
                seen.add(real)
                found.append(path)
    return found


BASHES = _bashes()


@unittest.skipUnless(BASHES, "no bash on this machine")
class GitGuardDifferential(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="git-guard-diff-")
        root = cls.tmp.name
        cls.fakedir = os.path.join(root, "bin")
        cls.cwd = os.path.join(root, "cwd")
        cls.log = os.path.join(root, "git.log")
        os.mkdir(cls.fakedir)
        os.mkdir(cls.cwd)
        cls.git = os.path.join(cls.fakedir, "git")
        with open(cls.git, "w") as f:
            f.write("#!{0} -IS\nimport json, sys\n"
                    "with open({1!r}, 'a') as f:\n"
                    "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                    .format(sys.executable, cls.log))
        os.chmod(cls.git, 0o755)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _run(self, bash, command):
        """The argv lists the fake git logged while `bash -c command` ran."""
        for shell in ("bash", "zsh"):
            link = os.path.join(self.fakedir, shell)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(bash, link)
        open(self.log, "w").close()
        env = {"PATH": self.fakedir + ":/usr/bin:/bin", "HOME": self.tmp.name,
               "GIT_CEILING_DIRECTORIES": self.tmp.name,
               "GIT_DIR": os.path.join(self.tmp.name, "no-repo")}
        subprocess.run([bash, "-c", command], env=env, cwd=self.cwd,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=10)
        with open(self.log) as f:
            return [json.loads(line) for line in f if line.strip()]

    def test_every_guarded_call_bash_runs_is_flagged(self):
        for bash in BASHES:
            for name, probe in PROBES:
                command = probe.replace("{GIT}", self.git)
                ran = self._run(bash, command)
                verdicts = {g: flags(command) for g, flags in GUARDS.items()}
                for guard in GUARDS:
                    missed = not verdicts[guard] and any(
                        is_write(guard, argv) for argv in ran)
                    detail = "\nprobe: {0!r}\nbash: {1}\nbash ran: {2}\nverdicts: {3}".format(
                        command, bash, ran, verdicts)
                    with self.subTest(bash=bash, probe=name, guard=guard):
                        if (name, guard) in EXCUSED:
                            self.assertTrue(missed, "{0} gap now closed ({1}): delete "
                                            "its EXCUSED entry".format(guard, EXCUSED[
                                                (name, guard)]) + detail)
                        else:
                            self.assertFalse(missed, "{0} guard allowed a write bash "
                                             "ran".format(guard) + detail)


if __name__ == "__main__":
    unittest.main()

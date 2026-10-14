"""Differential test: both git-guard parsers against real shells.

Each probe command runs under every bash found (`/bin/bash`, and `bash` on PATH
when it resolves elsewhere; no version assumed), and under `/bin/zsh` when present
(the shell the Bash tool runs on macOS), with a fake `git` first on PATH
that logs its argv as one JSON line and exits 0. Every logged argv whose verb is
in that guard's fixed write set (`WRITES`, independent of the guard's own
classifier) must make the guard flag the probe as written, so a probe the shells
disagree on is flagged if any of them runs the write. A guard that flags while
the shell ran nothing is conservative and passes; the reverse is not asserted.

The guards are read through their pure parser entry points, so no payload,
sidecar or worktree state is needed:

- live-worker-git-guard: `_mutating_call(command)`.
- worker-git-scope-guard: `decide()` with the most restrictive resolvers (every
  tree shared, every branch protected), so it flags every call it could ever deny.

Probes never reach the real git: `{GIT}` is replaced with the fake's absolute
path, PATH is `<fake dir>:/usr/bin:/bin`, GIT_DIR names no repo, and the fake dir
also shadows `bash` and `zsh` with the shell under test, so `zsh -c` needs no zsh
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
    return LIVE._mutating_call(command)[1] is not None


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
    # O1 and O2: bash quoting-in-word and `EOF)` terminator inside $( )
    ("O1_backslash_word_apostrophe", "cat <<\\EOF\nit's\nEOF\ngit commit -m x"),
    ("O1_partial_quote_apostrophe", 'cat <<E"O"F\nit\'s\nEOF\ngit commit -m x'),
    ("O2_paren_terminator",
     "x=$(cat <<EOF\nbody\nEOF)\ngit commit -m x\nEOF\n)"),
    # zsh reads past that `EOF)`: body text bash runs as commands must not hide
    # the call zsh runs after the real terminator
    ("Z_paren_body_heredoc_commit",
     "x=$(cat <<'EOF'\nEOF)\n: <<'X'\nEOF\n)\ngit commit -m x\nX"),
    ("Z_paren_body_apostrophe_commit",
     "x=$(cat <<'EOF'\nEOF)\nit's\nEOF\n) true\ngit commit -m x"),
    ("Z_paren_body_heredoc_stash",
     "x=$(cat <<'EOF'\nEOF)\n: <<'X'\nEOF\n)\ngit stash\nX"),
    # a `$(` inside quotes opens no substitution, so `EOF)` is body
    ("R1_quoted_dollar_paren",
     "echo '$(' ; cat <<EOF\nbody\nEOF)\nit's\nEOF\ngit commit -m x\ntrue # '"),
    ("R1_quoted_dollar_paren_heredoc",
     "echo '$(' ; cat <<EOF\nEOF)\n: <<X\nEOF\ngit commit -m x\nX"),
    ("R1_grep_dollar_paren",
     "grep -c '$(' <<EOF\nfoo $(\nEOF)\nit's\nEOF\ngit push\n: '"),
    # a quoted all-digit word is a heredoc, never a shift
    ("N2_quoted_digit_word", "cat <<'1'\nit's\n1\ngit commit -m x"),
    ("N2_backslash_digit_word", "cat <<\\1\nit's\n1\ngit commit -m x"),
    # `$(` depth: opened inside `"`, carried across lines, clamped at 0. The `: # '`
    # tail balances the body's apostrophe so the whitespace-split fallback finds nothing
    ("hd_dq_subst_odd_quote_body",
     "echo gh pr create --title t --body \"$(cat <<'EOF'\n"
     "A 12\" screen; it's fine\nEOF\n)\"\ngit push"),
    ("hd_subst_terminator_glued_semicolon", "x=$(cat <<'EOF'\nit's\nEOF);git push\n: # '"),
    ("hd_word_glued_semicolon", "cat <<EOF;\nit's\nEOF\ngit push"),
    ("hd_subst_after_subshell_paren",
     "(true); x=$(cat <<'EOF'\nit's\nEOF)\ngit push\n: # '"),
    ("hd_subst_opened_line_before", "x=$(\ncat <<'EOF'\nit's\nEOF)\ngit push\n: # '"),
    ("hd_subst_terminator_space_paren", "x=$(cat <<'EOF'\nit's\nEOF )\ngit push\n: # '"),
    ("hd_subst_after_arith_expansion",
     "echo $((1+2)); x=$(cat <<'EOF'\nit's\nEOF)\ngit push\n: # '"),
    ("hd_subst_nested_terminator", "x=$(echo $(cat <<'EOF'\nit's\nEOF))\ngit push\n: # '"),
    ("hd_subst_nested_terminator_glued_semicolon",
     "x=$(echo $(cat <<'EOF'\nit's\nEOF));git push\n: # '"),
    # a `)` with no `$(` open keeps the opener before it
    ("hd_word_then_subshell", "cat <<'EOF'; (true)\nit's\nEOF\ngit push\n: # '"),
    # bash 3.2 and zsh read no body for a heredoc whose `$(` closes on its own line;
    # bash 5 does
    ("hd_subst_closed_on_opener_line", "x=$(cat <<EOF; true)\ngit push\nEOF"),
    ("hd_subst_closed_on_opener_line_body_read", "x=$(cat <<'EOF' )\nit's\nEOF\ngit push"),
    # a word glued to the `)` closing a multi-line `$(` continues that word, so the
    # command after it is still in command position (zsh runs none of the third)
    ("hd_subst_multiline_glued_word_then_git", "x=$(\necho hi\n)x git push"),
    ("hd_subst_heredoc_glued_word_then_git", "x=$(cat <<'EOF'\nbody\nEOF\n)x git push"),
    ("hd_subst_terminator_glued_word_then_git", "x=$(cat <<'EOF'\nbody\nEOF)x git push"),
    # a newline inside `$(` starts no body opened outside it
    ("hd_outer_body_after_subst_newline", "cat <<EOF; x=$(echo hi\n); git push\nbody\nEOF"),
    ("hd_outer_body_after_dq_subst_newline",
     "cat <<EOF; echo \"$(echo hi\n)\"; git push\nbody\nEOF"),
    ("hd_outer_body_redirect_after_subst_newline",
     "cat <<EOF>/dev/null; x=$(echo hi\n) && git push\nbody\nEOF"),
    ("hd_outer_body_spaced_after_subst_newline",
     "cat <<EOF ; x=$(echo hi\n); git push\nbody\nEOF"),
    ("hd_outer_body_and_after_subst_newline",
     "cat <<'EOF' && x=$(echo hi\n) && git push\nbody\nEOF"),
    # a `$(` the shell never opens must not hold back an outer body: `$(…)#x` is one
    # word, and `$(` inside backticks is not parsed
    ("hd_subst_hash_word_then_arith",
     "cat <<'EOF' ; x=$(echo $(echo a)#x)\nbody\nEOF\necho $((1+2))\ngit push\nEOF"),
    ("hd_subst_hash_word_then_subshell",
     "cat <<'EOF' ; x=$(echo $(echo a)#x)\nbody\nEOF\n(true)\ngit push\nEOF"),
    ("hd_backtick_dollar_paren_then_subshell",
     "cat <<'EOF' ; x=`echo $(`\nbody\nEOF\n(true)\ngit push\nEOF"),
    ("hd_subst_hash_word_two_heredocs",
     "x=$(echo $(echo a)#x)\ncat <<'X' ; (true)\nX )\ncat <<'Y'\nX\ngit push\nY"),
    # a subshell or case `)` inside `$(` does not close it, so a `#` after one is a comment
    ("hd_subshell_hash_comment_in_subst",
     "cat <<'EOF' ; x=$( (true)#it's\n)\nEOF\necho it\\'s\ngit push\nEOF"),
    ("hd_case_hash_comment_in_subst",
     "cat <<'EOF' ; x=$(case a in a)#it's\necho;; esac)\nEOF\necho it\\'s\ngit push\nEOF"),
    # `$(...)#b` is one word to the command splitter too
    ("hd_subst_hash_word_then_git_heredoc",
     "echo $(echo a)#b; git commit -F - <<'EOF'\ngit push\nEOF"),
    ("hd_subst_hash_word_then_subshell_in_subst",
     "echo $(echo a)#b; x=$( (true); cat <<'EOF' )\ngit push\nEOF"),
    # a `)` from `$((`, `<(` or `${...}` inside `$(` does not close it
    ("hd_arith_in_subst_closed_on_opener_line",
     "x=$(echo $((1)); cat <<'EOF'; true)\ngit push\nEOF"),
    ("hd_procsub_in_subst_closed_on_opener_line",
     "x=$(diff <(true) <(true); cat <<'EOF'; true)\ngit push\nEOF"),
    ("hd_ceiling_param_paren_in_subst", "x=$(echo ${y%)}; cat <<'EOF'; true)\ngit push\nEOF"),
    ("hd_ceiling_param_open_paren_in_subst",
     "x=$(echo ${y//(/z}; cat <<'EOF'; true)\ngit push\nEOF"),
    ("hd_ceiling_bash32_paren_line_in_subshell_body",
     "x=$( ('('; '('; cat <<'EOF';)\n)\ngit push\ngit push\nEOF"),
    # bash decides a `)#` site by site, so one command can need both readings
    ("hd_mixed_hash_sites_body_opener",
     "cat <<'EOF' ; x=$(echo $(echo a)#x) ; (true)#it's\ncat <<X\nEOF\ngit push\nX\ntrue # '"),
    ("hd_mixed_hash_sites_stash",
     "cat <<'EOF'; x=$(echo a)#x ; x=$( (true)#it's\ngit stash\nX)\nEOF"),
    ("hd_mixed_hash_sites_in_subst",
     "x=$(cat <<'EOF' ; x=$(echo $(echo a)#x)\nEOF)\n(true)#it's\ngit push\necho it\\'s\nEOF"),
    # a heredoc inside backticks is read by the inner shell
    ("hd_backtick_heredoc_quote_body", "x=`cat <<'EOF'\nit's\nEOF\n`; git push # '"),
    ("hd_backtick_heredoc_then_commit", "x=`cat <<EOF\nit's\nEOF\n`\ngit commit -m x\ntrue # '"),
    ("hd_backtick_heredoc_call_inside", "x=`cat <<X\n\"\nX\ngit stash\n`"),
    # a `<<WORD` that bash reads as quoted text or a comment inside backticks opens nothing
    ("hd_backtick_dq_opener", 'x=`echo "a <<EOF b"`\ngit push\nEOF'),
    ("hd_backtick_sq_opener", "x=`echo 'a <<EOF b'`\ngit push\nEOF"),
    ("hd_backtick_comment_opener", "x=`echo hi # see <<EOF here`\ngit push\nEOF"),
    ("hd_backtick_grep_sq_opener", "n=`grep -c '<<EOF ' notes.md`\ngit push\nEOF"),
    ("hd_backtick_closes_in_body", "`<<'EOF'\n`\nEOF\n#<<EOF\ngit push\nEOF"),
    ("hd_ceiling_zsh_glob_group_spans_lines", "cat <<'EOF'; echo a(\n$(\ngit push\nfoo)\nEOF"),
    ("hd_ceiling_backtick_hash_word_after_body",
     "cat <<EOF;\nit's\nEOF\nx=`echo a)#it's`; git push # '"),
    # a `#` after a case-pattern or backticked `)` is a comment, after any other `)` it
    # is part of the word (`<(...)#x`, `(a)#x`, `$(...)#x`); bash 3.2 reads a quote in it
    ("hash_case_comment_apostrophe", "x=$(case a in a)#it's\necho;; esac)\ngit push # '"),
    ("hash_case_comment_apostrophe_same_line",
     "x=$(case a in a)#it's\necho;; esac); git push # '"),
    ("hash_backtick_subst_case_comment", "x=`echo $(`; case a in a)#it's\n;; esac\ngit push # '"),
    ("hash_backtick_subst_paren_in_backtick", "x=`echo $(`; y=`echo a)#it's`\ngit push # '"),
    ("hash_backtick_paren_in_subshell", "x=$( (echo `echo )`)#it's\n)\ngit push # '"),
    ("hd_glued_word_then_procsub_hash_word", "cat <<EOF;\nit's\nEOF\ncat <(true)#x; git push"),
    ("hd_glued_word_then_regex_group_hash_word",
     "cat <<EOF;\nit's\nEOF\n[[ a =~ (a)#x ]]; git push"),
    ("hd_glued_word_then_backtick_paren_hash_word",
     "cat <<EOF;\nit's\nEOF\nx=$(echo `echo )`)#x; git push"),
    ("hd_nested_subst_hash_word_then_arith_shift",
     "x=$(echo $(echo $(echo a)))#x; (( y = 1 << EOF ))\ngit commit -m x\nEOF"),
    ("hd_bash32_comment_apostrophe_in_subst",
     "x=$(while (false)#it's\ndo )#it\\'s\ncat <<\\EOF; true)\ngit push\nEOF"),
    # a `$(...)` in an unquoted heredoc body, or inside `"`, that the scan loses
    ("hd_ceiling_subst_in_unquoted_body", "cat <<EOF>/dev/null\n$(git push)\nEOF"),
    ("hd_ceiling_dq_subst",
     "x=\"$(cat |\nEOF\ngit push\n)\nx=\"$(cat )\nEOF\nx=\"$(cat <<EOF;\ngit push\nEOF"),
    # a `<<WORD;` opener where the scan has lost the context
    ("hd_ceiling_param_expansion", "echo ${x:-<<EOF;}\ngit push\nEOF"),
    ("hd_ceiling_dollar_bracket", "echo $[1<<EOF|2]\ngit push\nEOF"),
    ("hd_ceiling_arith_spans_lines", "(( x = 1 +\n2<<EOF|3 ))\ngit push\nEOF"),
    ("hd_ceiling_quoted_parens_before_arith",
     "echo '))'; (( y = 1<<EOF|2 ))\ngit push\nEOF"),
    ("hd_ceiling_subshell_in_subst", "x=$( (true); cat <<'EOF'; true)\ngit push\nEOF"),
    ("hd_ceiling_case_in_subst", "x=$(case a in a) cat <<'EOF';; esac)\ngit push\nEOF"),
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
EXCUSED = {}
# live-worker-git-guard README "What it cannot see": `bash -c "..."` and a command
# word glued to a separator displace the git word.
for _name in ("sh_bash_c", "sh_sh_c", "sh_zsh_c", "sh_bash_ec", "sh_env_bash_c",
              "sh_bash_c_heredoc_then_git"):
    EXCUSED[(_name, "live")] = "live README ceiling: bash -c string"
EXCUSED[("sep_glued", "live")] = "live README ceiling: word glued to a separator"
for _name in ("hd_subst_hash_word_then_arith", "hd_subst_hash_word_then_subshell",
              "hd_subst_hash_word_two_heredocs"):
    EXCUSED[(_name, "live")] = "live parity: `#` after a `$(...)` read as a comment, hardening"
EXCUSED[("hd_backtick_dollar_paren_then_subshell", "live")] = (
    "live parity: `$(` counted inside backticks, hardening")
for _name in ("hd_arith_in_subst_closed_on_opener_line",
              "hd_procsub_in_subst_closed_on_opener_line"):
    EXCUSED[(_name, "live")] = (
        "live parity: a `)` from `$((` or `<(` closes `$(` early, hardening")
for _name, _context in (("hd_ceiling_param_expansion", "inside `${...}`"),
                        ("hd_ceiling_dollar_bracket", "inside `$[...]`"),
                        ("hd_ceiling_arith_spans_lines", "inside arithmetic spanning lines"),
                        ("hd_ceiling_quoted_parens_before_arith",
                         "inside `((` after a quoted `))`"),
                        ("hd_ceiling_case_in_subst",
                         "in a case arm after the pattern `)` inside `$(`")):
    EXCUSED[(_name, "live")] = "ceiling: `<<` opener " + _context
EXCUSED[("hd_bash32_comment_apostrophe_in_subst", "live")] = (
    "live parity: bash 3.2 reads an apostrophe in a comment inside `$(` as a quote, hardening")
EXCUSED[("hd_ceiling_subshell_in_subst", "live")] = (
    "ceiling: `<<` opener after a subshell inside `$(`")
EXCUSED[("hd_ceiling_backtick_hash_word_after_body", "live")] = (
    "README ceiling: backtick substitution")
for _name in ("hd_mixed_hash_sites_body_opener", "hd_mixed_hash_sites_stash",
              "hd_mixed_hash_sites_in_subst"):
    EXCUSED[(_name, "live")] = "live parity: `#` after a `$(...)` read as a comment, hardening"
EXCUSED[("hd_ceiling_zsh_glob_group_spans_lines", "live")] = (
    "ceiling: zsh reads `word(` as a glob group spanning lines")
EXCUSED[("hd_ceiling_param_paren_in_subst", "live")] = (
    "ceiling: a `)` inside `${...}` closes `$(` early")
EXCUSED[("hd_ceiling_subst_in_unquoted_body", "live")] = (
    "ceiling: a `$(...)` in an unquoted heredoc body runs, but the body is dropped")
EXCUSED[("hd_ceiling_dq_subst", "live")] = "README ceiling: `$(...)` inside double quotes"


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
ZSH = "/bin/zsh"


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

    def _run(self, shell, command):
        """The argv lists the fake git logged while `shell -c command` ran."""
        for name in ("bash", "zsh"):
            link = os.path.join(self.fakedir, name)
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(shell, link)
        open(self.log, "w").close()
        env = {"PATH": self.fakedir + ":/usr/bin:/bin", "HOME": self.tmp.name,
               "GIT_CEILING_DIRECTORIES": self.tmp.name,
               "GIT_DIR": os.path.join(self.tmp.name, "no-repo")}
        subprocess.run([shell, "-c", command], env=env, cwd=self.cwd,
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=10)
        with open(self.log) as f:
            return [json.loads(line) for line in f if line.strip()]

    def _assert_flagged(self, shells):
        for shell in shells:
            for name, probe in PROBES:
                command = probe.replace("{GIT}", self.git)
                ran = self._run(shell, command)
                verdicts = {g: flags(command) for g, flags in GUARDS.items()}
                for guard in GUARDS:
                    wrote = any(is_write(guard, argv) for argv in ran)
                    missed = not verdicts[guard] and wrote
                    detail = "\nprobe: {0!r}\nshell: {1}\nshell ran: {2}\nverdicts: {3}".format(
                        command, shell, ran, verdicts)
                    with self.subTest(shell=shell, probe=name, guard=guard):
                        # a shell that cannot parse the probe (bash 3.2, zsh on
                        # several `$(` heredoc shapes) runs nothing: no gap to prove
                        if (name, guard) in EXCUSED and wrote:
                            self.assertTrue(missed, "{0} gap now closed ({1}): delete "
                                            "its EXCUSED entry".format(guard, EXCUSED[
                                                (name, guard)]) + detail)
                        else:
                            self.assertFalse(missed, "{0} guard allowed a write the "
                                             "shell ran".format(guard) + detail)

    def test_every_guarded_call_bash_runs_is_flagged(self):
        self._assert_flagged(BASHES)

    @unittest.skipUnless(os.path.exists(ZSH), "no /bin/zsh (Linux CI)")
    def test_every_guarded_call_zsh_runs_is_flagged(self):
        self._assert_flagged([ZSH])

    def test_scope_strip_heredocs_keeps_git_after_backslash_word_body(self):
        # at 630a04ca the apostrophe in the body left the quote open, so the
        # git line after the real terminator was swallowed
        self.assertEqual(
            SCOPE.strip_heredocs("cat <<\\EOF\nit's\nEOF\ngit commit -m x"),
            "cat <<\\EOF\ngit commit -m x")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
live-worker-git-guard — PreToolUse hook.

Denies a MUTATING git command while this session still has delegations it
started and has not seen settle. The working tree is shared with them: a commit
captures their half-applied edits as if they were finished work, and a
pull/checkout/stash/reset takes their uncommitted files off disk underneath a
process that has no idea it happened.

Both halves were observed, neither needed bad judgement. A root session polling
for a green suite committed a tree a builder had temporarily sabotaged. A
routine post-merge `git checkout dev && git pull --ff-only` autostashed five
uncommitted files out of the tree while a manager was live — `Created autostash`
/ `Applied autostash.` reads identically whether or not it raced, so the loss
window leaves no artifact to check afterwards. Prose already told both sessions
to wait; what was missing was anything that noticed.

Read-only git is never touched — `status`, `diff`, `log`, `show`, `branch`,
`rev-list`, `rev-parse`, `ls-files`, `fetch` are how a session orients, and a
guard that made orientation expensive would be turned off.

The verb set is ruled on one verb at a time in the README's table, and the
line it draws is this hazard rather than "writes something": what can remove,
overwrite or swap a tracked file in THIS tree, move the branch the tree sits
on, or capture and publish its half-finished state. What writes only the index
(`add`), only the object database, only a ref that has an everyday read
spelling (`branch`, `tag`, `symbolic-ref`), only another working tree, or only
the files named on the command line (`merge-file`, `mergetool`, which are the
destructive-write case below) is out, with its reason recorded beside it.

Scoped to ONE working tree. The pending set is keyed on the session's
transcript, which says nothing about where a command points, and a session can
hold workers in its own tree while a call runs in a checkout of a different
repo entirely — those workers are unreachable from there. So the tree targeted
(`git rev-parse --show-toplevel` from its cwd, moved by any `-C`) is compared
against the tree the session's non-isolated workers occupy (the same
resolution from CLAUDE_PROJECT_DIR, which Claude Code sets on the hook process
to the session's main checkout). Different trees, no block. `--show-toplevel`
rather than `--git-common-dir` because the hazard is a shared WORKING TREE: a
sibling linked worktree of the same repository has its own index and its own
files, and a commit or push there takes nothing off disk in this one.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PreToolUse):
  - stdin JSON fields consumed: session_id, transcript_path, cwd, tool_name,
    tool_input.command, and agent_id (present ONLY when the call comes from
    inside a subagent). `transcript_path` is used only to locate the
    `subagents/` directory; `cwd` is where the git call runs.
  - env consumed: CLAUDE_PROJECT_DIR (the session's main checkout, for the
    tree comparison), plus the two ledger path overrides below.
  - stdout JSON (exit 0), on a deny only:
      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "permissionDecision": "deny",
                              "permissionDecisionReason": "..."}}
    and on an override only:
      {"systemMessage": "..."}
    An override deliberately emits NO permissionDecision: "allow" would
    short-circuit every other permission check, and this hook's opinion is only
    about live workers.
  - exit 0 always. An exception must never emit a deny.

Fail-open on every error path — no transcript_path, no `subagents/` dir,
unreadable ledger, malformed stdin — because a hook that cannot decide must not
block. The consequence, stated rather than hidden: a session whose records the
hook cannot read is unguarded exactly as it was before this hook existed. Two
deliberate exceptions, both fail-CLOSED, because each is a record that exists
and cannot be read rather than a record that is absent: a sidecar that will not
parse still counts its agent as live (its `worktreePath` is unreadable), and a
tree comparison that does not resolve — no git binary, a cwd outside any
repository, an unset CLAUDE_PROJECT_DIR — decides as the guard did before it
could compare trees at all.

Anything that aims the command away from the payload's cwd by a rule this does
not reimplement is an unresolved comparison rather than a guess, and so counts
the workers: the `--git-dir`/`--work-tree` flags, the same relocation spelled
`GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR`, a `cd`/`pushd`/`popd` before the
git word (wrapped or bare), and a wrapper option that moves the tree the git
call itself runs in (`env -C DIR`, `sudo -D DIR`, `env -S`).

Tokenizer ceiling, stated as a rule rather than a list, because a list of ways
to hide a word invites the belief that it is complete: the `git` word and the
`cd` are read only in COMMAND POSITION of the single command string the hook is
handed, so whatever displaces them is not seen. Two things no longer displace
them. A leading exec wrapper: the named ones in EXEC_WRAPPERS are stepped over,
with their own options and values, so `time git push` and `timeout 60 git push`
are read as the calls they are. And a SHELL_KEYWORDS word, after which command
position resumes, so the call inside `for f in *; do git commit; done` is read
too — but NOT after a `#` comment or a `<<` on the same line, where the
keyword rule is suspended (separators keep opening command position there, as
they always did). A heredoc body is dropped before the scan, up to and
including its terminator line, so nothing in it opens command position and a
call after the terminator is read. An unquoted newline ends a command as `;`
does. An unlisted wrapper still displaces them, and so do `bash -c "..."`, a
`$( )` substitution, a command word glued to a separator (`ls&&git commit`),
and the body of a heredoc whose terminator is never found, which is kept and
read as command lines. Anything that re-parses a STRING is
past the ceiling by construction, including `env -S` and a quoted `eval`. A
`GIT_*` variable exported by an EARLIER Bash call is the same ceiling in
another place — it is not among this command's tokens at all. None of these is
the sanctioned bypass; the override is, and it leaves a row. Seeing through
them means interpreting the command line rather than tokenizing it, with its
own over-denial surface.

The pending set is `_lib/pending.py`, shared with `subagent-telemetry` so the
two cannot disagree about who is live. Agents holding their own checkout
(`worktreePath` on the sidecar) are excluded: they do not share this tree.
Everything else counts, read-only scouts included — a `checkout` or `pull`
changes the tree a scout is reading mid-read.

The guard is NOT main-session-only: a manager holding live builders is the same
hazard as a root session holding them, and the deny text fits it unchanged. A
delegating agent is excluded from its own pending set, and an agent that holds
its own worktree is exempt entirely — it is not looking at this tree.

Not covered: a destructive root-session WRITE (back up a file, break it,
restore it) to a file a live worker owns. That needs an ownership registry
mapping briefs to paths, which does not exist; worktree isolation solves it by
construction.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and
must stay compatible with Python 3.9.
"""

import json
import os
import re
import shlex
import subprocess
import sys

# The shared append path lives beside the hook dirs, at `<hooks-root>/_lib/`.
# That relative hop resolves both here in primitives-core/ and in an installed
# plugin, where `hooks/_lib` is a member of the symlink assembly (ADR 0017).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib")
)
import codex_workers  # noqa: E402
import agentlog  # noqa: E402  (path must be primed before this import)
import pending  # noqa: E402  (same)

LOG_STREAM = "live-worker-git-guard"
LOG_PATH_ENV = "LIVE_WORKER_GIT_GUARD_LOG_PATH"

OVERRIDE_VAR = "ATELIER_GIT_GUARD_OVERRIDE"
OVERRIDE_TRUTHY = ("1", "true", "yes", "on")

# Verbs that can take a tracked file off THIS working tree, move the branch it
# sits on, or publish its half-finished state. What writes only the index
# (`add`), only the object database, only a ref that has an everyday read
# spelling (`branch`, `tag`), or only files named on the command line is
# deliberately out — the README's ruling table gives the reason for every verb,
# in the set or out of it.
MUTATING_VERBS = frozenset((
    "commit", "push", "merge", "pull", "rebase", "checkout", "switch", "stash",
    "reset", "cherry-pick", "revert", "clean", "restore", "am", "apply",
    "rm", "mv", "bisect", "submodule", "sparse-checkout", "update-ref",
    "read-tree", "checkout-index",
))

# git's own global options, the ones that take a SEPARATE value token. Without
# this set `git -C /repo commit` reads `/repo` as the subcommand and the call
# goes unguarded.
GLOBAL_FLAGS_WITH_VALUE = frozenset((
    "-C", "-c", "--git-dir", "--work-tree", "--namespace",
    "--config-env", "--attr-source", "--super-prefix",
))

# ...and the two of those that move the working tree itself, in either
# spelling. They make the targeted tree unknowable rather than wrong.
TREE_AIMING_FLAGS = ("--git-dir", "--work-tree")

# The same relocation spelled as environment, which git honours identically.
TREE_AIMING_VARS = frozenset(("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"))

# Builtins that move the cwd, which makes the payload's cwd stale for any git
# call later in the same command line.
CWD_MOVING_BUILTINS = frozenset(("cd", "pushd", "popd"))

# Wrappers that exec another command, mapped to their OWN options that take a
# separate value token — without which the value reads as the command word.
EXEC_WRAPPERS = {
    "env": frozenset((
        "-u", "--unset", "-C", "--chdir", "-S", "--split-string",
        "-P", "-a", "--argv0")),
    "command": frozenset(),
    "exec": frozenset(("-a",)),
    "builtin": frozenset(),
    "eval": frozenset(),
    "nice": frozenset(("-n", "--adjustment")),
    "time": frozenset(("-o", "--output", "-f", "--format")),
    # `-i`/`-l`/`-e` and their long spellings `--replace`/`--eof` are absent
    # on purpose: an OPTIONAL argument must be glued, so skipping two eats the
    # command word.
    "xargs": frozenset((
        "-n", "--max-args", "-P", "--max-procs", "-I", "-J", "-R", "-S",
        "-L", "--max-lines", "-s", "--max-chars", "-a", "--arg-file",
        "-d", "--delimiter", "-E")),
    "timeout": frozenset(("-s", "--signal", "-k", "--kill-after")),
    "sudo": frozenset((
        "-u", "--user", "-g", "--group", "-C", "--close-from", "-D",
        "--chdir", "-h", "--host", "-p", "--prompt", "-r", "--role",
        "-t", "--type", "-U", "--other-user", "-R", "--chroot",
        "-T", "--command-timeout")),
    "nohup": frozenset(),
    "stdbuf": frozenset(("-i", "--input", "-o", "--output", "-e", "--error")),
    "setsid": frozenset(),
}

# Wrapper options that relocate the tree, or pack a shell string this tokenizer
# cannot read. Per wrapper: `sudo -C` is a file descriptor, `env -C` is a chdir.
TREE_AIMING_WRAPPER_FLAGS = {
    "env": frozenset(("-C", "--chdir", "-S", "--split-string")),
    "sudo": frozenset(("-D", "--chdir", "-R", "--chroot")),
}

# `command -v git` prints where git is; it does not run it. Same exclusion the
# docstring already makes for `which git`.
LOOKUP_FLAGS = {"command": frozenset(("-v", "-V"))}

# Wrappers taking a BARE positional before the command: `timeout 60 git push`.
# A "first non-flag token is the command" rule would read `60` as the command.
BARE_ARG_WRAPPERS = frozenset(("timeout",))

# Homebrew's coreutils/findutils ship these `g`-prefixed and both spellings sit
# on PATH, so `gtimeout` is read as the `timeout` row rather than as a command.
G_PREFIXED_WRAPPERS = frozenset((
    "env", "nice", "time", "timeout", "stdbuf", "nohup", "setsid", "xargs"))

# Per `git rev-parse` call. At most two run, and only once a mutating verb is
# already in hand, so the worst case sits well inside the hook's 10s budget.
GIT_TIMEOUT = 3

# A token ENDING in one of these is a shell separator, so the next token starts
# a fresh command: `a && git commit`, `a; git commit`, `a | git commit`.
SEPARATOR_TAILS = ("&", "|", ";", "(", ")", "{", "}")

# The same characters plus redirection, looked for INSIDE a token: shlex leaves
# `status|grep` and `log;git` whole, so a verb or a read form glued to one
# matched nothing and the call was read as neither.
SEPARATOR_CHARS = "&|;(){}<>"

# A heredoc opener. The lookarounds reject a `<<<` herestring. A shift still
# matches when spaced (`1 << 3` captures `3`); `_scan_line` rejects an all-digit
# word, and any word inside an unclosed `((` (`$(( 1 << n ))`, `(( y <<= n ))`).
HEREDOC_START = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)(\w+)['\"]?(\r?)(?=\s|$)")


class _LineBreak(str):
    """The token an unquoted newline becomes: a `;` to every separator check,
    and told apart from a typed `;` by identity, because a line break also ends
    a `#` comment and the rest of a heredoc opener line, and a `;` ends
    neither."""


LINE_BREAK = _LineBreak(";")

# `git commit --help` opens a man page and touches nothing. Orientation has to
# stay cheap, or the guard is the thing that gets turned off.
HELP_FLAGS = frozenset(("--help", "-h"))

# Keywords a command word follows — the same displacement a wrapper causes.
# `for`/`in` are out (the next word is a loop variable); `done`/`fi` need no row.
SHELL_KEYWORDS = frozenset(("do", "then", "else", "elif", "if", "while",
                            "until", "!"))

# Read-only forms of verbs that otherwise write: `git stash list` is how a
# session orients, `git apply --check` touches nothing. Keyed by verb; a call
# whose first non-option argument (a SUBCOMMAND_VERBS one) or any option (every
# other) is listed here is a read and never fires. `""` is the bare call.
READ_FORMS = {
    "stash": frozenset(("list", "show")),
    "apply": frozenset(("--check", "--stat", "--numstat", "--summary")),
    "bisect": frozenset(("", "log", "view", "visualize", "terms", "help")),
    "submodule": frozenset(("", "status", "summary")),
    "sparse-checkout": frozenset(("", "list", "check-rules")),
    "rm": frozenset(("--dry-run", "-n")),
    "mv": frozenset(("--dry-run", "-n")),
    "read-tree": frozenset(("--dry-run", "-n")),
}

# Verbs whose read forms are subcommands rather than options, so the FIRST bare
# argument decides. Bare is a read for all but `stash`, where bare means push:
# `git submodule` is `status`, and the other two print usage.
SUBCOMMAND_VERBS = frozenset((
    "stash", "bisect", "submodule", "sparse-checkout"))

# Options on the denied verbs that consume the NEXT token, which is therefore
# neither a subcommand nor a help flag: `git stash -m list` stashes for real,
# and `git commit -m -h` commits with the message `-h`. A `--opt=value` needs no
# row. Incomplete by construction, and the README names the residual miss —
# but the failure is one-sided, since an unlisted option can only make a read
# form visible that this set would have hidden.
OPTS_WITH_VALUE = frozenset((
    "-m", "--message", "-F", "--file", "-C", "--reuse-message",
    "-c", "--reedit-message", "--author", "--date", "-t", "--template",
    "--fixup", "--squash", "--cleanup", "--trailer", "--gpg-sign",
    "-s", "--strategy", "-X", "--strategy-option", "--onto", "--exec",
    "-b", "-B", "--orphan", "--conflict", "--source", "--pathspec-from-file",
    "-e", "--exclude", "--whitespace", "--prefix", "--index-output",
    "--separate-git-dir",
))

MAX_NAMED_AGENTS = 4


def _emit(obj):
    """Print the hook's one JSON object without letting a closed stdout turn
    into a nonzero exit: flush inside the guard, and on a broken pipe point
    fd 1 at devnull so the interpreter's shutdown flush has nothing to do."""
    try:
        print(json.dumps(obj))
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Reading the command
# ---------------------------------------------------------------------------

def _scan_line(line, quote):
    """(the heredoc terminators this line opens, each `(word, quoted, dash)`,
    the quote state at its end, whether it ends in a line continuation), given the
    quote state it starts in.

    An opener counts only outside quotes and outside a comment, and never with
    an all-digit word or inside an unclosed `((`, where it is a shift
    (`$(( 1 <<3 ))`, `(( y = 1 << n ))`). A backslash escapes
    the next character outside single quotes, and inside `$'...'` too. A `#`
    at the start of the line, after whitespace or after one of `;&|()` runs to
    the line end, so an apostrophe in a comment opens no quote.
    """
    terminators = []
    i = 0
    while i < len(line):
        char = line[i]
        if quote:
            if char == quote[-1]:
                quote = None
            elif char == "\\" and quote != "'":
                i += 1
        elif char == "\\":
            if i == len(line) - 1:
                return terminators, quote, True
            i += 1
        elif line.startswith("$'", i):
            quote = "$'"
            i += 1
        elif char in "'\"":
            quote = char
        elif char == "#" and (i == 0 or line[i - 1].isspace()
                              or line[i - 1] in ";&|()"):
            break
        elif char == "<":
            m = HEREDOC_START.match(line, i)
            if (m and not m.group(3).isdigit()
                    and line.count("((", 0, i) <= line.count("))", 0, i)):
                # bash keeps a CRLF opener's `\r` in the word
                terminators.append((m.group(3) + m.group(4), bool(m.group(2)),
                                    bool(m.group(1))))
                i = m.end()
                continue
        i += 1
    return terminators, quote, False


def _body_end(lines, j, word, quoted, dash):
    """The index of the line that closes a heredoc body starting at `lines[j]`,
    or None. As in bash, under an unquoted word a line ending in an odd run of
    backslashes joins the next first, and the result must equal the word
    exactly, after only its leading tabs are removed under `<<-`."""
    while j < len(lines):
        line = lines[j]
        while (not quoted and j + 1 < len(lines)
               and (len(line) - len(line.rstrip("\\"))) % 2):
            j += 1
            line = line[:-1] + lines[j]
        if (line.lstrip("\t") if dash else line) == word:
            return j
        j += 1
    return None


def _skip_bodies(lines, i, terminators):
    """The index after the last of the heredoc bodies that `terminators`
    opened on one line, read in order from `lines[i]`; `i` itself when one is
    never closed, since dropping text is a silent fail-open."""
    j = i
    for terminator in terminators:
        j = _body_end(lines, j, *terminator)
        if j is None:
            return i
        j += 1
    return j


def _logical_lines(command):
    """The command split at every newline outside quotes, with heredoc bodies
    and backslash-newlines removed.

    A body runs from the opener's line end through its terminator line, as
    bash finds it (`_body_end`); bodies opened on one line follow in order. They
    are dropped only when every terminator is found: dropping text is a silent
    fail-open, keeping it is at worst an over-deny.
    """
    lines = command.split("\n")
    out, current, quote, pending, i = [], "", None, [], 0
    while i < len(lines):
        line = lines[i]
        i += 1
        terminators, quote, continued = _scan_line(line, quote)
        pending += terminators
        if continued:
            current += line[:-1]
            continue
        current += line
        if quote:
            current += "\n"
            continue
        out.append(current)
        current = ""
        i = _skip_bodies(lines, i, pending)  # each body and its terminator line
        pending = []
    if current:
        out.append(current)
    return out


def _tokens(command):
    """Shell tokens for a Bash command string.

    shlex first, and its quote handling is the point rather than an accident:
    `echo "remember to git commit"` collapses to two tokens, the second of
    which is not `git`, so a mention of a git command inside a string can never
    be read as a call. An unbalanced quote makes shlex raise; the whitespace
    split is the fallback, which is coarser but never worse than nothing.

    Heredoc bodies are dropped, since they are text, and backslash-newlines
    removed (`_logical_lines`). shlex reads a newline as plain whitespace, so
    each logical line is split on its own and the lines are joined with
    LINE_BREAK, which opens command position as a `;` does.
    """
    tokens = []
    for line in _logical_lines(command):
        try:
            words = shlex.split(line)
        except ValueError:
            words = line.split()
        if words:
            if tokens:
                tokens.append(LINE_BREAK)
            tokens.extend(words)
    return tokens


def _is_assignment(token):
    """`NAME=value` — an env prefix, which does not end the command position."""
    name, sep, _value = token.partition("=")
    if not sep or not name:
        return False
    return name.replace("_", "").isalnum() and not name[0].isdigit()


def _opens_command(token, inert):
    """True when the NEXT token is in command position: this one ends a
    command (a separator), prefixes one (an assignment), or is a keyword a
    command follows (`; do git commit`).

    `inert` once the scan has passed a `#` or a `<<` on the current line
    (`_next_inert`). Only the keyword rule is suspended there: separators
    behave as they always did, so `make ci  # then git commit` stays silent. A
    heredoc body never reaches this scan — `_tokens` drops it — so neither a
    keyword nor a separator in one opens command position.
    """
    if token.endswith(SEPARATOR_TAILS) or _is_assignment(token):
        return True
    return not inert and token in SHELL_KEYWORDS


def _next_inert(inert, token):
    """The scan's inert state after `token`: set by a `#` comment or a `<<`
    heredoc redirect, cleared by a line break, which ends both."""
    if token is LINE_BREAK:
        return False
    return inert or token.startswith("#") or token.startswith("<<")


def _relocates(wrapper, token):
    """True when this wrapper option aims its command at another tree, in any
    spelling (`env -C DIR`, `env --chdir=DIR`, `env -C/dir`, `sudo -D DIR`)."""
    for flag in TREE_AIMING_WRAPPER_FLAGS.get(wrapper, ()):
        if token == flag or token.startswith(flag + "="):
            return True
        if len(flag) == 2 and len(token) > 2 and token.startswith(flag):
            return True
    return False


def _unwrap(tokens, start):
    """(index of the real command word at `start`, aimed-elsewhere?), stepping
    over leading exec wrappers.

    A wrapper that execs its argument used to hide the whole call from the
    command-position scan: `time git push` and `timeout 60 git push` are things
    a session writes for real reasons, and each lost its deny silently. The
    index is None when the line runs out, hits a separator, or the wrapper only
    LOOKS the command up (`command -v git`). The flag is True when a wrapper
    option relocates the tree or packs a shell string this tokenizer cannot
    read, which the caller treats as unresolvable rather than skipping past.
    """
    index = start
    relocated = False
    wrapper = None
    positional_pending = False
    while index < len(tokens):
        token = tokens[index]
        if token.endswith(SEPARATOR_TAILS):
            return None, relocated
        if wrapper is None:
            word = os.path.basename(token)
            if word[:1] == "g" and word[1:] in G_PREFIXED_WRAPPERS:
                word = word[1:]
            if word not in EXEC_WRAPPERS:
                return index, relocated
            wrapper = word
            positional_pending = word in BARE_ARG_WRAPPERS
            index += 1
            continue
        if token in LOOKUP_FLAGS.get(wrapper, ()):
            return None, relocated
        if _relocates(wrapper, token):
            relocated = True
        if token.startswith("-") and token != "-":
            index += 2 if token in EXEC_WRAPPERS[wrapper] else 1
            continue
        if _is_assignment(token):
            index += 1
            continue
        if positional_pending:
            positional_pending = False
            index += 1
            continue
        wrapper = None  # a bare token after a wrapper's options: the command
    return None, relocated


def _first_mutating_verb(tokens):
    """(verb, index of the `git` token, index of the command word that leads to
    it) for the first mutating git call, else (None, None, None).

    A `git` token only counts in COMMAND position — first, after a shell
    separator, or after an env assignment — so `man git commit` and
    `which git` are not git calls. An exec wrapper in command position is
    stepped over, so the two indices differ for `nice git commit`; the second
    is where the override prefix has to be read from. `/usr/bin/git` counts: it
    is the same program, and matching the bare word only would make the guard
    one absolute path away from off. After it, git's own global options are
    skipped (including the value of a `-C`-style flag) and the first bare token
    is the subcommand.
    """
    command_position = True
    inert = False
    for index, token in enumerate(tokens):
        if command_position:
            git_at, _relocated = _unwrap(tokens, index)
            # Lowercased: a case-insensitive filesystem runs `GIT rm` as git.
            if git_at is not None and os.path.basename(
                    tokens[git_at]).lower() == "git":
                verb, verb_at = _subcommand(tokens, git_at + 1)
                if verb in MUTATING_VERBS and not _is_read_form(
                        verb, tokens, verb_at + 1):
                    return verb, git_at, index
        inert = _next_inert(inert, token)
        command_position = _opens_command(token, inert)
    return None, None, None


def _head(token):
    """The token up to its first shell separator, glued or trailing:
    `status|grep` and `pull;` are both one shlex token."""
    for index, char in enumerate(token):
        if char in SEPARATOR_CHARS:
            return token[:index]
    return token


def _subcommand(tokens, start):
    """(subcommand, its index) at or after `start`, skipping global options;
    (None, None) when the command ends first."""
    i = start
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("-"):
            return _head(token), i
        if token in GLOBAL_FLAGS_WITH_VALUE:
            i += 2  # the flag and its separate value
            continue
        i += 1
    return None, None


def _call_args(tokens, start):
    """This git call's own argument tokens, with everything that is not one of
    them dropped.

    Three exclusions, each of which was a hole: past a `--` every token is a
    path (`git rm -- -n` deletes a file NAMED `-n`), past a shell separator the
    tokens belong to the next command, and the value of an option that takes
    one is data (`git stash -m list` is a stash, not `stash list`).
    """
    args = []
    for token in tokens[start:]:
        head = _head(token)
        if head == "--":
            break
        if head:
            args.append(head)
        if head != token:
            break
    kept = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        kept.append(arg)
        skip = arg in OPTS_WITH_VALUE
    return kept


def _is_read_form(verb, tokens, start):
    """True when this call of a mutating verb is one of its read-only forms
    (READ_FORMS), judged on the call's own arguments."""
    args = _call_args(tokens, start)
    if any(a in HELP_FLAGS for a in args):
        return True
    forms = READ_FORMS.get(verb)
    if not forms:
        return False
    if verb in SUBCOMMAND_VERBS:
        first = next((a for a in args if not a.startswith("-")), "")
        return first in forms
    return any(a in forms for a in args)


def _is_override(token):
    name, _sep, value = token.partition("=")
    return name == OVERRIDE_VAR and value.strip().lower() in OVERRIDE_TRUTHY


def _override_before(tokens, cmd_start, git_at):
    """True when an `ATELIER_GIT_GUARD_OVERRIDE=1` assignment precedes the git
    call AS ITS ENV PREFIX — the contiguous run of assignments right before the
    command word, or one carried inside the wrapper itself (`env VAR=1 git`).
    The prefix sits before any wrapper, so reading backwards from the `git`
    word rather than from the command word would lose the sanctioned escape
    hatch to a false deny. Position matters: the same string as an argument (a
    commit message, say) is not an override, and neither is a prefix on an
    earlier command in the same line (`OVERRIDE=1 echo hi && git commit`)."""
    if any(_is_override(token) for token in tokens[cmd_start:git_at]):
        return True
    i = cmd_start - 1
    while i >= 0 and _is_assignment(tokens[i]):
        if _is_override(tokens[i]):
            return True
        i -= 1
    return False


# ---------------------------------------------------------------------------
# Which tree the command targets
# ---------------------------------------------------------------------------

def _repo_root(directory):
    """Realpath'd working-tree root containing `directory`, or None when that
    does not resolve.

    realpath because the two sides of the comparison arrive by different
    routes — a payload cwd and an env var — and on macOS the same tree reached
    through a symlink (`/var` for `/private/var`) is spelled two ways.
    """
    if not isinstance(directory, str) or not directory:
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            env=codex_workers.clean_git_env() if codex_workers.is_codex({}) else None,
            capture_output=True, timeout=GIT_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    root = proc.stdout.decode("utf-8", "replace").strip()
    if not root:
        return None
    try:
        return os.path.realpath(root)
    except OSError:
        return None


def _target_directory(tokens, git_at, cwd):
    """The directory this git call resolves paths against, or None when
    something in the line aims it somewhere this hook does not compute.

    Anything BEFORE the git word that invalidates the payload's cwd — a cwd
    -moving builtin in command position (under any exec wrapper: `command cd`
    moves the cwd exactly as `cd` does), a wrapper option that relocates the
    git call's own tree (`env -C DIR`), a tree-aiming environment assignment
    anywhere in the line, since a bare one carries to the rest of it — is
    unresolvable rather than wrong. A relocating option counts only on the
    wrapper chain that leads to the git word: `env -C DIR true && git commit`
    aims `true`, not the git call. After it, `-C` is cumulative and each value
    is taken relative to the one before it, which is exactly `os.path.join`;
    git accepts only the separate-value spelling, so there is no `-C/repo`
    form to handle.
    """
    if not isinstance(cwd, str) or not cwd:
        return None
    command_position = True
    inert = False
    for index, token in enumerate(tokens[:git_at]):
        if command_position:
            word_at, relocated = _unwrap(tokens, index)
            if relocated and word_at == git_at:
                return None
            if word_at is not None and os.path.basename(
                    tokens[word_at]).lstrip("({") in CWD_MOVING_BUILTINS:
                return None
        if _is_assignment(token) and token.partition("=")[0] in TREE_AIMING_VARS:
            return None
        inert = _next_inert(inert, token)
        command_position = _opens_command(token, inert)
    directory = cwd
    index = git_at + 1
    while index < len(tokens):
        token = tokens[index]
        if not token.startswith("-"):
            break
        if any(token == flag or token.startswith(flag + "=")
               for flag in TREE_AIMING_FLAGS):
            return None
        if token == "-C":
            if index + 1 >= len(tokens):
                return None
            directory = os.path.join(directory, tokens[index + 1])
            index += 2
            continue
        if token in GLOBAL_FLAGS_WITH_VALUE:
            index += 2
            continue
        index += 1
    return directory


def _shares_session_tree(tokens, git_at, cwd):
    """True when the command targets the working tree the session's workers
    occupy — and when that cannot be decided, which counts as sharing."""
    target = _repo_root(_target_directory(tokens, git_at, cwd))
    if target is None:
        return True
    session = _repo_root(os.environ.get("CLAUDE_PROJECT_DIR"))
    return session is None or target == session


# ---------------------------------------------------------------------------
# Who is live
# ---------------------------------------------------------------------------

def _is_isolated(directory, key):
    """True when this agent holds its own checkout (`worktreePath` on its
    sidecar), so nothing done in THIS tree can reach it — and nothing it does
    reaches this tree either."""
    home = pending.sidecar_dir(directory, key) or directory
    meta = pending.read_sidecar(pending.sidecar_path(home, key)) or {}
    return bool(meta.get("worktreePath"))


def _live_workers(transcript_path, caller):
    """Pending delegations that SHARE this working tree.

    `caller` is the agent making the call, when the call comes from inside a
    subagent rather than the main session (a manager running `git commit` while
    its builders are live is the same hazard, and the deny text fits it). It is
    excluded twice over: an agent is never live from its own point of view, and
    an agent working in its own worktree is looking at a different tree, so
    this tree's occupants are not its problem.

    Raises rather than swallowing a ledger read failure: `main` fails open on
    it, and an unknowable settled set must not be silently rendered as "nothing
    has settled", which would deny on every agent this session ever started.
    """
    directory = pending.subagents_dir(transcript_path)
    if directory is None:
        return []
    if caller and _is_isolated(directory, caller):
        return []
    workers = []
    candidates = pending.pending_keys(directory)
    # A TaskStop'd or user-killed agent fires no SubagentStop, so the ledger
    # never settles it; the session transcript records the kill instead.
    stopped = pending.stopped_ids(transcript_path, candidates)
    for key in candidates:
        if key == caller or key in stopped:
            continue
        meta = pending.read_sidecar(pending.sidecar_path(directory, key)) or {}
        if meta.get("worktreePath"):
            # Its own checkout: this tree's state is none of its business.
            continue
        workers.append({
            "agent_id": key,
            "agent_type": meta.get("agentType") or "agent",
            "description": meta.get("description") or "no description",
        })
    return workers


def _describe(workers):
    lines = [
        "  - {0} {1} ({2})".format(w["agent_type"], w["agent_id"], w["description"])
        for w in workers[:MAX_NAMED_AGENTS]
    ]
    if len(workers) > MAX_NAMED_AGENTS:
        lines.append("  - ...and {0} more".format(len(workers) - MAX_NAMED_AGENTS))
    return "\n".join(lines)


def _deny_reason(verb, workers):
    return (
        "atelier live-worker-git-guard: `git {verb}` is blocked — this session has "
        "{count} delegation(s) still running:\n\n{who}\n\n"
        "They are working in THIS tree, not their own checkout. A commit captures "
        "their half-applied edits as finished work; a pull, checkout, switch, stash, "
        "reset or restore takes their uncommitted files off disk (or autostashes and "
        "re-applies them) while they are mid-write, and the loss looks identical to "
        "success afterwards.\n\n"
        "Wait for their completion notifications, then re-run this command. Do NOT "
        "`git stash` by hand to get around it — hand-stashing reopens the exact window "
        "this closes, and the work lands in a stash entry the agent will never look "
        "for. Restructure the operation to avoid an override first. An override is only "
        "legitimate for a git write whose target is provably outside every live worker "
        "tree; it is never for this project repository or any of its worktrees. If one "
        "is legitimate, report the exact command and cwd, and explain why that target "
        "is not shared:\n\n"
        "    {var}=1 git {verb} ...\n"
    ).format(verb=verb, count=len(workers), who=_describe(workers), var=OVERRIDE_VAR)


def _override_message(verb, workers):
    return (
        "atelier live-worker-git-guard: {var}=1 — `git {verb}` allowed with "
        "{count} live delegation(s) sharing this tree:\n{who}\n"
        "Their uncommitted work is at risk for the duration of this command."
    ).format(var=OVERRIDE_VAR, verb=verb, count=len(workers),
             who=_describe(workers))


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            sys.exit(0)
        native = codex_workers.is_codex(payload)
        if native:
            try:
                if not codex_workers.active(payload):
                    return
                payload = codex_workers.effective_payload(payload)
            except Exception as exc:
                _emit(codex_workers.deny(exc))
                return
        if payload.get("tool_name") != "Bash":
            sys.exit(0)

        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            sys.exit(0)
        command = tool_input.get("command")
        if not command or not isinstance(command, str):
            sys.exit(0)

        tokens = _tokens(command)
        verb, git_at, cmd_start = _first_mutating_verb(tokens)
        if verb is None:
            sys.exit(0)

        overridden = _override_before(tokens, cmd_start, git_at)
        if native:
            try:
                target = _repo_root(_target_directory(tokens, git_at, payload.get("cwd")))
                workers = [dict(row, description="native worker")
                           for row in codex_workers.records(payload)
                           if row["agent_id"] != payload.get("agent_id")
                           and row["status"] == "running"
                           and (target is None or _repo_root(row.get("worktree") or row["source"]) == target)]
            except Exception as exc:
                _emit(codex_workers.deny(exc))
                return
        else:
            workers = _live_workers(
                payload.get("transcript_path"), pending.agent_key(payload.get("agent_id")))
            if workers and not _shares_session_tree(tokens, git_at, payload.get("cwd")):
                workers = []
        if not workers and not overridden:
            sys.exit(0)

        if workers and overridden:
            _emit({"systemMessage": _override_message(verb, workers)})
        elif workers:
            _emit({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": _deny_reason(verb, workers),
                },
            })

        # A row per decision that reached the session, plus one for an override
        # used where nothing was going to block: an override that leaves no
        # trace is exactly the silence this stream exists to end. An empty
        # `pending` is what separates the two. Still never one row per Bash
        # call — both early exits above run first.
        agentlog.append(LOG_STREAM, {
            "session_id": payload.get("session_id"),
            "decision": "override" if overridden else "deny",
            "verb": verb,
            "pending": [w["agent_id"] for w in workers],
        }, agentlog.resolve_project(payload.get("cwd")), LOG_PATH_ENV)
        sys.exit(0)

    except SystemExit:
        raise
    except Exception:
        # Fail-open, and silently: a guard that cannot read its own records has
        # no grounds to block, and an error message on stdout would be parsed
        # as a hook decision.
        sys.exit(0)


if __name__ == "__main__":
    main()

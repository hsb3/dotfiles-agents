#!/usr/bin/env python3
"""skills-cli-guard: PreToolUse guard that denies running the third-party `skills` CLI.

Reads the command text only (shlex over logical lines, heredoc bodies skipped) and never
runs a shell. What it blocks, lets through and cannot see is in README.md.

Stdlib-only, Python 3.9 compatible. Prints one deny object on a hit, nothing otherwise, and
always exits 0.
"""

import json
import re
import shlex
import sys

OVERRIDE = "ATELIER_SKILLS_CLI_OVERRIDE=1"
RUNNERS = (("npx",), ("bunx",), ("pnpx",), ("bun", "x"), ("pnpm", "dlx"), ("yarn", "dlx"),
           ("npm", "exec"))
HELP = {"--help", "-h", "--version", "-V"}
KEYWORDS = {"!", "{", "if", "then", "else", "elif", "do", "while", "until", "time"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
OPERATORS = "();<>|&`"

REASON = (
    "skills-cli-guard: the `skills` CLI claims every skill under any .agents/ or .claude/ "
    "folder in a repo, overwrites hand-authored skills and drops a skills-lock.json, and "
    "`skills remove -g --all` deletes hand-authored skills from the user skills dir. "
    "Author, move or delete skill directories by hand instead. If this run is deliberate, "
    "prefix the command itself: `" + OVERRIDE + " npx skills ...`."
)


def runs_skills(words):
    """True when one simple command's words run the `skills` package through a runner."""
    if not words:
        return False
    words = [words[0].rsplit("/", 1)[-1]] + words[1:]
    for runner in RUNNERS:
        if tuple(words[:len(runner)]) != runner:
            continue
        rest = words[len(runner):]
        while rest and rest[0].startswith("-"):
            rest = rest[1:]
        if rest and (rest[0] == "skills" or rest[0].startswith("skills@")):
            args = rest[1:]
            return not (args and all(a in HELP for a in args))
    return False


def tokens(text):
    # ponytail: shlex drops quoting, so a quoted `;|&(` reads as an operator, a "$(...)" stays
    # one word, and a mid-word `#` starts a comment; a quote-aware lexer would fix all three.
    lex = shlex.shlex(text, posix=True, punctuation_chars=OPERATORS)
    lex.whitespace_split = True
    return list(lex)


def line_runs_skills(toks, heredocs):
    """True when a simple command among one logical line's tokens runs the CLI without the
    override. Appends (strip_tabs, delimiter) for each heredoc the line opens."""
    stack, words, override, target, ticks = [], [], False, None, False
    for tok in toks:
        if tok and all(c in OPERATORS for c in tok):
            if "<" in tok or ">" in tok:
                # ponytail: an arithmetic `<<` reads as a heredoc opener too
                target = "<<" if "<<" in tok and "<<<" not in tok else "file"
                if len(words) > 1 and words[-1].isdigit():
                    words.pop()  # the fd of `2>&1`, which shlex splits off
            for j, c in enumerate(tok):
                near = tok[max(j - 1, 0):j + 2]
                if c in "<>" or (c in "&|" and ("<" in near or ">" in near)):
                    continue
                if c == "(" or (c == "`" and not ticks):
                    stack.append((words, override))
                    words, override, target = [], False, None
                    ticks = ticks or c == "`"
                    continue
                if not override and runs_skills(words):
                    return True
                if c in ";&|":
                    words, override = [], False
                else:  # `)` or a closing backtick resumes the enclosing command
                    words, override = stack.pop() if stack else ([], False)
                    ticks = ticks and c != "`"
        elif target == "file":
            target = None
        elif target:
            if target == "<<" and tok.startswith("-"):
                tok, target = tok[1:], "<<-"
            if tok:
                heredocs.append((target == "<<-", tok))
                target = None
        elif words:
            words.append(tok)
        elif tok == OVERRIDE:
            override = True
        elif not (ASSIGNMENT.match(tok) or tok in KEYWORDS):
            words = [tok]
    return any(not o and runs_skills(w) for w, o in stack + [(words, override)])


def denied(command):
    if "skills" not in command:
        return False
    lines = command.replace("\\\n", "").split("\n")
    i = 0
    while i < len(lines):
        text, i = lines[i], i + 1
        while True:
            try:
                toks = tokens(text)
                break
            except ValueError:
                if i == len(lines):
                    return False  # an unterminated quote: the shell refuses to run it too
                text, i = text + "\n" + lines[i], i + 1
        heredocs = []
        if line_runs_skills(toks, heredocs):
            return True
        for strip_tabs, word in heredocs:
            while i < len(lines) and (lines[i].lstrip("\t") if strip_tabs else lines[i]) != word:
                i += 1
            i += 1
    return False


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or data.get("tool_name") != "Bash":
            return
        tool_input = data.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if isinstance(command, str) and denied(command):
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": REASON,
            }}))
    except Exception:  # noqa: BLE001 — a guard fails open, never with a traceback
        return


if __name__ == "__main__":
    main()

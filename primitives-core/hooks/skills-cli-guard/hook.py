#!/usr/bin/env python3
"""skills-cli-guard: PreToolUse guard that denies running the third-party `skills` CLI.

Reads the command text only (heredoc bodies dropped, then one shlex pass) and never runs a
shell. What it blocks, lets through and cannot see is in README.md.

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
VALUED = {"--prefix", "--cwd", "-C", "-w", "--workspace"}  # their next word is a value
# ponytail: matched on raw lines, so a `<<` inside quotes, a comment or `$((1<<2))` opens one too
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*((?:'[^']*'|\"[^\"]*\"|\\.|[^\s|&;()<>'\"\\])+)")

REASON = (
    "skills-cli-guard: the `skills` CLI claims every skill under any .agents/ or .claude/ "
    "folder in a repo, overwrites hand-authored skills and drops a skills-lock.json, and "
    "`skills remove -g --all` deletes hand-authored skills from the user skills dir. "
    "Author, move or delete skill directories by hand instead. If this run is deliberate, "
    "prefix the command itself: `" + OVERRIDE + " npx skills ...`."
)
# shlex grows a word by string concatenation, so its time is quadratic in one word's length
# and a timeout fails open; above this size the hook denies instead of reading.
LIMIT = 128 * 1024
TOO_BIG = (
    "skills-cli-guard: this command mentions `skills` and carries more than %dK characters of "
    "text outside heredoc bodies, too much to read inside the hook's timeout. Move the long text "
    "into a file or a heredoc body and rerun." % (LIMIT // 1024)
)


def past_flags(words, i):
    """The index of the first word from i on that is not a runner flag or its value."""
    while i < len(words) and words[i].startswith("-"):
        i += 2 if words[i] in VALUED else 1
    return i


def runs_skills(words):
    """True when one simple command's words run the `skills` package through a runner."""
    if not words:
        return False
    words = [words[0].rsplit("/", 1)[-1]] + words[1:]
    for runner in RUNNERS:
        i = 0
        for part in runner:
            i = past_flags(words, i)
            if i >= len(words) or words[i] != part:
                break
            i += 1
        else:
            i = past_flags(words, i)
            if i < len(words) and (words[i] == "skills" or words[i].startswith("skills@")):
                args = words[i + 1:]
                return not (args and all(a in HELP for a in args))
    return False


def drop_heredoc_bodies(command):
    """Logical lines with every heredoc body and terminator removed, whatever quoting the
    opener sits in: a body inside `"$(` must never reach shlex, whose quote state it shifts."""
    lines, kept, i = command.split("\n"), [], 0
    while i < len(lines):
        line, i = lines[i], i + 1
        parts = []
        # an odd run of trailing backslashes continues the line; an even run is escaped ones
        while (len(line) - len(line.rstrip("\\"))) % 2 and i < len(lines):
            parts.append(line[:-1])
            line, i = lines[i], i + 1
        line = "".join(parts) + line
        kept.append(line)
        for dash, word in HEREDOC.findall(line):
            word = re.sub(r"[\\'\"]", "", word)
            while i < len(lines) and (lines[i].lstrip("\t") if dash else lines[i]) != word:
                i += 1
            i += 1
    return "\n".join(kept)


def scan(toks):
    """True when a simple command among the tokens runs the CLI without the override."""
    stack, words, override, target, ticks = [], [], False, False, False
    for tok in toks:
        if tok and all(c in OPERATORS for c in tok):
            if "<" in tok or ">" in tok:
                target = True  # the next word is a file or a heredoc delimiter
                if len(words) > 1 and words[-1].isdigit():
                    words.pop()  # the fd of `2>&1`, which shlex splits off
            for j, c in enumerate(tok):
                near = tok[max(j - 1, 0):j + 2]
                if c in "<>" or (c in "&|" and ("<" in near or ">" in near)):
                    continue
                if c == "(" or (c == "`" and not ticks):
                    stack.append((words, override))
                    words, override, target = [], False, False
                    ticks = ticks or c == "`"
                    continue
                if not override and runs_skills(words):
                    return True
                if c in ";&|":
                    words, override = [], False
                else:  # `)` or a closing backtick resumes the enclosing command
                    words, override = stack.pop() if stack else ([], False)
                    ticks = ticks and c != "`"
                    if c == ")" and tok[j - 1:j] == "(":  # `name()`: a function body follows
                        words, override = [], False
        elif target:
            target = False
        elif words:
            words.append(tok)
        elif tok == OVERRIDE:
            override = True
        elif not (ASSIGNMENT.match(tok) or tok in KEYWORDS):
            words = [tok]
    return any(not o and runs_skills(w) for w, o in stack + [(words, override)])


def denied(command):
    """The deny reason for the command, or None when it may run."""
    if "skills" not in command:
        return None
    # A newline ends a command. The `;` after it does that for shlex, and survives a `#`
    # comment, which swallows its own newline.
    text = drop_heredoc_bodies(command)
    if "skills" not in text:  # a heredoc body is text, so a mention only there is no mention
        return None
    if len(text) > LIMIT:
        return TOO_BIG
    text = text.replace("\n", "\n;")
    # ponytail: shlex drops quoting, so a quoted `;|&(` reads as an operator, a "$(...)" stays
    # one word, and a mid-word `#` starts a comment; a quote-aware lexer would fix all three.
    lex = shlex.shlex(text, posix=True, punctuation_chars=OPERATORS)
    lex.whitespace_split = True
    try:
        return REASON if scan(lex) else None
    except ValueError:
        return None  # an unterminated quote: the shell refuses to run that text too


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or data.get("tool_name") != "Bash":
            return
        tool_input = data.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        reason = denied(command) if isinstance(command, str) else None
        if reason:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }}))
    except Exception:  # noqa: BLE001 — a guard fails open, never with a traceback
        return


if __name__ == "__main__":
    main()

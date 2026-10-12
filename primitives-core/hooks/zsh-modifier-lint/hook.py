#!/usr/bin/env python3
"""zsh-modifier-lint: PreToolUse deny on an unbraced `$NAME:<letter>` in a Bash command.

zsh reads a letter after an unbraced parameter's colon as a history modifier, so
`$T:refs/heads/x` loses `$T`'s extension and the `r`, where bash keeps the colon. The braced
`"${T}:refs/heads/x"` reads the same in both. See README.md for what passes and the ceilings.

Reads the command text only and never runs a shell. Stdlib-only, Python 3.9 compatible; any
malformed payload exits 0 with no output.
"""

import json
import re
import sys

OVERRIDE = "ATELIER_ZSH_MODIFIER_OVERRIDE"
CAP = 5

PARAM = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*|[0-9]+):")
# f, g and w prefix a modifier rather than being one; an unquoted `&` ends the word instead
MOD = re.compile(r"[fgw]*[acehlqrstuAPQ]")
MOD_QUOTED = re.compile(r"[fgw]*[acehlqrstuAPQ&]")
REST = re.compile(r"[^\s;&|<>()'\"`$\\]*")
SPECIAL = set("$?#!-*@")
# ponytail: the delimiter is one unspaced word; `<<'END OF'` or `<<E;F` is misread
DELIM = re.compile(r"[ \t]*([^\s;&|<>()]+)")
QUOTE_CHARS = re.compile(r"['\"\\]")
OVERRIDE_AT_COMMAND = re.compile(
    r"\s*(?:(?:if|then|else|elif|do|while|until|time|!|\{)\s+)*"
    r"(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*" + OVERRIDE + r"=1\s")


def _param(cmd, i, quoted, starts, hits):
    """Record a hit if the `$` at i opens one; return where scanning resumes."""
    m = PARAM.match(cmd, i)
    if not m:
        return i + 2 if cmd[i + 1:i + 2] in SPECIAL else i + 1
    mod = (MOD_QUOTED if quoted else MOD).match(cmd, m.end())
    if not mod:
        return m.end()
    end = REST.match(cmd, mod.end()).end()
    braced = "${%s}%s" % (m.group(1), cmd[m.end() - 1:end])
    hits.append((cmd[i:end], braced if quoted else '"%s"' % braced, starts))
    return end


def _skip_ansi_c(cmd, j):
    while j < len(cmd):
        if cmd[j] == "\\":
            j += 2
        elif cmd[j] == "'":
            return j + 1
        else:
            j += 1
    return len(cmd)


def _bodies(cmd, pos, pending, hits):
    """Consume the pending heredoc bodies starting at pos; return the index after them."""
    for delim, strip, expands, starts in pending:
        while pos < len(cmd):
            end = cmd.find("\n", pos)
            end = len(cmd) if end < 0 else end
            line, start, pos = cmd[pos:end], pos, end + 1
            if (line.lstrip("\t") if strip else line) == delim:
                break
            j = start
            while expands and j < end:
                if cmd[j] == "\\":
                    j += 2
                elif cmd[j] == "$":
                    j = _param(cmd, j, True, starts, hits)
                else:
                    j += 1
    del pending[:]
    return pos


def scan(cmd):
    """(offending text, braced rewrite) for each modifier zsh would apply, minus overrides."""
    hits, pending = [], []
    stack = [["top", 0, 0]]  # [kind, command start, paren depth]; "dq" has no command start
    i, n = 0, len(cmd)
    while i < n:
        kind, c = stack[-1][0], cmd[i]
        starts = [f[1] for f in stack if f[1] is not None]
        if c == "\\":
            i += 2
        elif c == "$":
            if kind != "dq" and cmd.startswith("$'", i):
                i = _skip_ansi_c(cmd, i + 2)
            elif cmd.startswith("$(", i):
                stack.append(["sub", i + 2, 1])
                i += 2
            else:
                i = _param(cmd, i, kind == "dq", starts, hits)
        elif c == "`":
            if kind == "bt":
                stack.pop()
            else:
                stack.append(["bt", i + 1, 0])
            i += 1
        elif kind == "dq":
            if c == '"':
                stack.pop()
            i += 1
        elif c == "'":
            end = cmd.find("'", i + 1)
            i = n if end < 0 else end + 1
        elif c == '"':
            stack.append(["dq", None, 0])
            i += 1
        elif c == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|("):
            end = cmd.find("\n", i)
            i = n if end < 0 else end
        elif cmd.startswith("<<<", i):
            i += 3
        elif cmd.startswith("<<", i):
            j = i + 2 + cmd.startswith("-", i + 2)
            m = DELIM.match(cmd, j)
            if m:
                word = m.group(1)
                pending.append((QUOTE_CHARS.sub("", word), j > i + 2,
                                not QUOTE_CHARS.search(word), starts))
            i = m.end() if m else j
        elif kind == "sub" and c == ")" and stack[-1][2] == 1:
            stack.pop()
            i += 1
        else:
            # ponytail: parens are counted, so a `case` pattern's `)` closes `$(` early
            if kind == "sub" and c in "()":
                stack[-1][2] += 1 if c == "(" else -1
            if c in ";&|(\n":
                stack[-1][1] = i + 1
            if c == "\n" and pending:
                i = _bodies(cmd, i + 1, pending, hits)
                stack[-1][1] = i
            else:
                i += 1
    return [(text, rewrite) for text, rewrite, starts in hits
            if not any(OVERRIDE_AT_COMMAND.match(cmd, s) for s in starts)]


def deny(hits):
    listed = "; ".join("`{0}` -> `{1}`".format(t, r) for t, r in hits[:CAP])
    if len(hits) > CAP:
        listed += " (and {0} more)".format(len(hits) - CAP)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "zsh-modifier-lint: {0}. Commands run under zsh, which reads a letter after "
                "an unbraced `$NAME:` as a history modifier (`:r` drops an extension, `:h` "
                "keeps the directory) and swallows the colon and letter, where bash keeps "
                "them as text. Brace the name and keep the rest. If the modifier is "
                "intended, rerun as `{1}=1 <command>`."
            ).format(listed, OVERRIDE),
        }
    }


def main():
    try:
        data = json.load(sys.stdin)
        if data.get("tool_name") != "Bash":
            return
        command = data["tool_input"]["command"]
        hits = scan(command) if isinstance(command, str) else []
    except Exception:
        return
    if hits:
        print(json.dumps(deny(hits)))


if __name__ == "__main__":
    main()

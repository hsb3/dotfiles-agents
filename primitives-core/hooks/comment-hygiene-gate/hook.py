#!/usr/bin/env python3
"""
comment-hygiene-gate — PreToolUse hook.

Fires only on a Bash command that is about to LAND work (`git commit`,
`gh pr create`), scans the ADDED comment lines of the SOURCE files in that
change for history markers (issue and board refs, dates, CI run ids,
attributions), and names what it found. Silent on every other Bash command,
and on prose files, where history is supposed to live (see PROSE_SUFFIXES).

History and commentary belong on the related task, not in the code. Prose
alone does not make the cleanup happen; a check at the moment work lands does.

Purely observational: it never blocks, never edits, and fails open on every
error path — no git, no repo, no diff, weird encoding all exit silently.

Doc sources verified against:
  https://code.claude.com/docs/en/hooks
  https://code.claude.com/docs/en/hooks-guide

Contract (PreToolUse):
  - stdin JSON fields consumed: cwd, tool_name, tool_input.command.
  - stdout JSON (exit 0), only when markers are found:
      {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                              "additionalContext": "..."},
       "systemMessage": "..."}
    Never emits permissionDecision, so it cannot deny.
  - exit 0 always.

Fires unconditionally, like the other observational hooks (context-watermark,
delegation-watermark). Only the enforcing hooks read `.claude/atelier.local.md`.

This file must have ZERO third-party dependencies (Python 3 stdlib only) and
must stay compatible with Python 3.9.
"""

import json
import os
import re
import subprocess
import sys

GIT_TIMEOUT = int(os.environ.get("COMMENT_HYGIENE_GIT_TIMEOUT", "10") or 10)
MAX_DIFF_BYTES = 4 * 1024 * 1024
MAX_FILES_LISTED = 6
MAX_EXAMPLES = 3
MAX_EXAMPLE_CHARS = 120

LANDING = (
    re.compile(r"\bgit\b(?:\s+-\S+|\s+--\S+)*\s+commit\b"),
    re.compile(r"\bgh\b\s+pr\s+create\b"),
)

# What opens a comment depends on the language: `#` starts one in Python and
# names a colour in CSS. A single universal table is what makes `color: #141413`
# read as an issue reference, so the openers are keyed by extension.
_HASH = ("#",)
_C = ("//", "/*")
_BLOCK = ("/*",)
_MARKUP = ("<!--",)
_DASH = ("--",)
_SEMI = (";",)

OPENERS = {
    "py": _HASH, "pyi": _HASH, "sh": _HASH, "bash": _HASH, "zsh": _HASH,
    "rb": _HASH, "pl": _HASH, "r": _HASH, "yaml": _HASH, "yml": _HASH,
    "toml": _HASH, "tf": _HASH, "ini": _HASH, "cfg": _HASH, "conf": _HASH,
    "gitignore": _HASH, "dockerfile": _HASH, "makefile": _HASH, "mk": _HASH,
    "c": _C, "h": _C, "cc": _C, "cpp": _C, "hpp": _C, "cs": _C, "go": _C,
    "rs": _C, "java": _C, "kt": _C, "swift": _C, "scala": _C, "php": _C,
    "js": _C, "cjs": _C, "mjs": _C, "jsx": _C, "ts": _C, "tsx": _C,
    "scss": _C, "less": _C, "css": _BLOCK,
    "html": _MARKUP, "htm": _MARKUP, "xml": _MARKUP, "svg": _MARKUP,
    "vue": _MARKUP, "svelte": _MARKUP,
    "sql": _DASH, "lua": _DASH, "hs": _DASH, "elm": _DASH,
    "el": _SEMI, "lisp": _SEMI, "clj": _SEMI, "scm": _SEMI,
}
# An unknown extension gets the two commonest families rather than nothing:
# missing a comment costs less than inventing one, but silence costs coverage.
DEFAULT_OPENERS = _HASH + _C
QUOTES = "\"'`"

# `UTF-8`, `SHA-256` and friends are not board refs.
KEY_PREFIX_SKIP = {
    "UTF", "SHA", "RFC", "ISO", "AES", "CVE", "TLS", "SSL", "HTTP", "HTTPS",
    "IPV", "PEP", "RGB", "UTC", "MD", "GPT", "API", "URL", "ID",
    "LICENSE", "LICENCE", "GPL", "LGPL", "BSD", "ES", "HTML", "CSS",
}

BOARD_KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,9})-([0-9]{1,6})\b")

# Prose files have no comments — a markdown `#` is a heading, and an issue number
# mid-sentence is a sentence. Scanning them inverts the rule this hook enforces,
# because a tracker card or a handoff is where the history is SUPPOSED to live.
PROSE_SUFFIXES = (".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc", ".org")
# The same, for the prose files that carry no extension at all.
PROSE_NAMES = {
    "license", "licence", "notice", "copying", "authors", "contributors",
    "changelog", "readme",
}

MARKERS = (
    # Same shape the identity gate uses: 1-5 digits with a hex-char lookahead, so a
    # six-hex-digit colour is not read as an issue number.
    (re.compile(r"(?<![\w&])#[0-9]{1,5}(?![0-9A-Fa-f])"), "issue reference"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "date"),
    (re.compile(r"\b(?:CI\s+)?run\s+(?:id\s+)?\d{6,}\b", re.I), "CI run id"),
    (
        re.compile(
            r"\b(?:owner|maintainer|reviewer|client)'?s?\s+"
            r"(?:directive|ruling|report|request|call|feedback|decision)\b",
            re.I,
        ),
        "attribution",
    ),
    (re.compile(r"\bper\s+(?:the\s+)?(?:owner|review|discussion|standup|call)\b", re.I), "attribution"),
    (re.compile(r"\bas\s+(?:discussed|agreed|requested)\b", re.I), "attribution"),
    (re.compile(r"\b(?:this|it|we)\s+used\s+to\b", re.I), "superseded history"),
    (re.compile(r"\b(?:the\s+)?(?:first|original|previous|earlier)\s+version\s+of\b", re.I), "superseded history"),
)


def _git(cwd, *args):
    """Run git; return stdout, or None on any failure."""
    try:
        p = subprocess.run(
            ("git",) + args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=GIT_TIMEOUT,
        )
    except Exception:
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", errors="replace")


def _merge_base_diff(cwd):
    """Branch diff against the merge-base with the default branch."""
    head = _git(cwd, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    candidates = []
    if head:
        candidates.append(head.strip())  # already a full refname; shortening it re-introduces the shadow
    # `refs/tags/<name>` and `refs/heads/<name>` resolve BEFORE `refs/remotes/<name>`, so a
    # local ref named `origin/main` would otherwise become the base and diff the wrong range.
    candidates += ["refs/remotes/origin/main", "refs/remotes/origin/master"]
    # Last resort for a clone with no remote: these two are genuine LOCAL branches.
    candidates += ["refs/heads/main", "refs/heads/master"]
    for base in candidates:
        if not base:
            continue
        out = _git(cwd, "diff", "--unified=0", "--no-color", base + "...HEAD")
        if out:
            return out
    return None


def _openers_for(path):
    name = path.rsplit("/", 1)[-1].lower()
    return OPENERS.get(name.rsplit(".", 1)[-1] if "." in name else name, DEFAULT_OPENERS)


def _is_prose(path):
    name = path.rsplit("/", 1)[-1].lower()
    return name.endswith(PROSE_SUFFIXES) or name.split(".")[0] in PROSE_NAMES


def _comment_text(added_line, openers):
    """The comment portion of an added diff line, or None.

    Walks the line left to right tracking quote state, so a marker inside a
    string literal stays code: `print("see #NNN")` is not history. Only single
    lines are ever available here (a diff hunk is fragments, not a parseable
    file), so this is a lexer for one line, not a parser.

    ponytail: single-line scope — a comment character inside a MULTI-line
    string (a generator's file template) still reads as a comment, because the
    opening quote is on a line this never sees. Measured at 1 occurrence in 156
    Python files. Reaching it needs whole-file parsing per language; do that
    only if templates ever become a real share of the noise.
    """
    body = added_line[1:]
    stripped = body.lstrip()
    if stripped[:3] in ('"""', "'''"):  # a docstring's opening line
        return stripped[3:].strip() or None

    i, n, quote = 0, len(body), ""
    while i < n:
        ch = body[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in QUOTES:
            quote = ch
            i += 1
            continue
        for op in openers:
            if body.startswith(op, i):
                # `--` opens a comment only with a space after it; otherwise it
                # is `i--` or a CSS custom property.
                if op == "--" and body[i + 2:i + 3] != " ":
                    continue
                if op == "//" and body[i - 1:i] == ":":  # a URL scheme
                    continue
                return body[i + len(op):].strip() or None
        i += 1
    return None


def _board_ref(text):
    for prefix, _num in BOARD_KEY.findall(text):
        if prefix not in KEY_PREFIX_SKIP:
            return True
    return False


def _scan(diff):
    """Return {file: [(kind, text), ...]} for added comment lines carrying history."""
    findings = {}
    current = None
    skip = False
    openers = DEFAULT_OPENERS
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            # git appends a tab to the header when the path contains spaces.
            current = line[6:].split("\t")[0]
            skip = _is_prose(current)
            openers = _openers_for(current)
            continue
        if skip:
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        text = _comment_text(line, openers)
        if not text:
            continue
        kinds = [why for rx, why in MARKERS if rx.search(text)]
        if _board_ref(text):
            kinds.append("board reference")
        if kinds:
            findings.setdefault(current or "(unknown file)", []).append(
                (sorted(set(kinds))[0], text[:MAX_EXAMPLE_CHARS])
            )
    return findings


def _format(findings):
    total = sum(len(v) for v in findings.values())
    files = sorted(findings)
    shown = files[:MAX_FILES_LISTED]
    file_list = "\n".join(f"  - {f} ({len(findings[f])})" for f in shown)
    if len(files) > len(shown):
        file_list += f"\n  - ...and {len(files) - len(shown)} more file(s)"

    examples = []
    for f in files:
        for kind, text in findings[f]:
            examples.append(f"  {kind}: {text}")
            if len(examples) >= MAX_EXAMPLES:
                break
        if len(examples) >= MAX_EXAMPLES:
            break

    return (
        f"[atelier] comment-hygiene: {total} added comment line(s) in this change carry "
        "history rather than a reason the code needs.\n\n"
        f"{file_list}\n\n" + "\n".join(examples) + "\n\n"
        "History and commentary belong on the related task, not in the code. Before this "
        "lands: append the reasoning to its tracker item (board task, issue, or the repo's "
        "decisions log), then rewrite each comment as a present-tense fact about the system "
        "— or delete it. A comment survives only if a competent reader would break something "
        "without it. The comment-hygiene skill has the keep test and the cut list.\n\n"
        "Advisory only; nothing is blocked."
    )


def main():
    try:
        payload = json.loads(sys.stdin.read())
        if payload.get("tool_name") != "Bash":
            sys.exit(0)
        command = (payload.get("tool_input") or {}).get("command") or ""
        if not isinstance(command, str):
            sys.exit(0)

        is_pr = bool(LANDING[1].search(command))
        if not is_pr and not LANDING[0].search(command):
            sys.exit(0)

        cwd = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
        if not cwd or not os.path.isdir(cwd):
            sys.exit(0)

        diff = _merge_base_diff(cwd) if is_pr else _git(cwd, "diff", "--cached", "--unified=0", "--no-color")
        if not diff or len(diff) > MAX_DIFF_BYTES:
            sys.exit(0)

        findings = _scan(diff)
        if not findings:
            sys.exit(0)

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": _format(findings),
            },
            "systemMessage": (
                f"atelier: {sum(len(v) for v in findings.values())} added comment line(s) "
                "carry history (refs, dates, attributions) — run the comment-hygiene pass."
            ),
        }))
        sys.stdout.flush()
    except BrokenPipeError:
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
        except Exception:
            pass
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()

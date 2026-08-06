#!/usr/bin/env python3
"""Identity-neutrality lint — D6 machine-floor check 1 (entry-gate spec, decision 0013 item 9).

No name / org / repo / issue is hardcoded in any SHIPPED artifact; personalization reaches a
skill only through data surfaces (the roster's `requires:`, a repo's own config), never baked
into a primitive body. This is the vendored, in-repo successor to the archived workbench
`scripts/promote_check.py` H2/H5 checks — no cross-repo import at runtime.

Scope = the shipped primitive bodies under `primitives-core/{skills,agents,hooks}/`, plus the
symlink-assembly tree `plugins/` (ADR 0017): bundle READMEs are regular files there, and each
standalone wrapper's README travels with its skill (`primitives-core/skills/<id>/README.md`,
symlinked to the plugin root) — all of it ships to a user the same as a skill body and is in
scope for the same reason. Within `plugins/`, `.claude-plugin/` metadata is skipped (the
marketplace/plugin `owner`/`author` metadata is the *sanctioned* data surface for authorship —
that is where identity is allowed to live), and symlinks are skipped (their targets are
already scanned at source). Repo-internal docs that never leave
the source tree (root README, CONTRIBUTING, ADRs) do not ship to a user and are not
scanned here.

Folded in from the D1-dropped `validate` lane (per the desk's R5 ruling), so that intent is
not lost:
  - frontmatter shape — every SKILL.md carries `name` + `description`; agent .md carries
    `name` + `description`.
  - description hygiene — no XML/angle-bracket tag in a SKILL.md `description` (Claude Cowork
    refuses to load such a skill).
  - secret hygiene — no literal credential (token/key) baked into a body.
  - portability — machine-tied content is banned outright (absolute /Users paths, personal
    home-folder locations, personal vault name, non-portable install flags); a machine-local
    tool reference is legal only when the roster entry declares it in `requires:`.

Stdlib-only, deterministic. Exit 0 = clean; exit 1 = violations (prints every one).
Usage: python3 scripts/check_identity.py   (run from the repo root)
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from check_roster import _list, parse_roster  # noqa: E402

SCAN_ROOTS = (
    os.path.join(REPO, "primitives-core", "skills"),
    os.path.join(REPO, "primitives-core", "agents"),
    os.path.join(REPO, "primitives-core", "hooks"),
    os.path.join(REPO, "plugins"),
)
TEXT_EXT = (".md", ".json", ".sh", ".py", ".js", ".ts", ".yaml", ".yml", ".toml", ".txt")

# ── Identity tokens: name / org / client / repo / issue hardcoded in a shipped body. ──
# Lookbehind/ahead exclude a leading/trailing word-char OR hyphen so a personal name embedded
# in a skill id (e.g. a hypothetical `foo-henry`) is not matched — a skill-id reference is a
# structural dependency, not baked-in personalization, and renaming one is out of scope here.
IDENTITY = [
    (re.compile(r"(?<![\w-])[Hh]enry(?![\w-])"), "personal name 'Henry'"),
    (re.compile(r"(?<![\w-])[Bb]urden(?![\w-])"), "personal name 'Burden'"),
    (re.compile(r"(?<![\w-])hsb3(?![\w-])"), "GitHub owner handle 'hsb3'"),
    (re.compile(r"(?<![\w-])mhi-raptorxai(?![\w-])"), "GitHub org 'mhi-raptorxai'"),
    (re.compile(r"(?<![\w-])raptorxai(?![\w-])"), "client token 'raptorxai'"),
    (re.compile(r"(?<![\w-])ra-platform(?![\w-])"), "client repo 'ra-platform'"),
    (re.compile(r"(?<![\w-])ra-labs(?![\w-])"), "client repo 'ra-labs'"),
    (re.compile(r"(?<![\w-])functionform(?![\w-])"), "client token 'functionform'"),
    (re.compile(r"(?<![\w-])raptorgpt(?![\w-])"), "client token 'raptorgpt'"),
    (re.compile(r"(?<![\w-])headcase(?![\w-])"), "client token 'headcase'"),
    (re.compile(r"(?<![\w-])dotfiles-agents-workbench(?![\w-])"), "internal repo slug 'dotfiles-agents-workbench'"),
    (re.compile(r"(?<![\w-])fable-optimization(?![\w-])"), "internal repo slug 'fable-optimization'"),
    # Issue refs. Capped at 5 digits + a hex-char lookahead so a 6-hex-digit colour (#003366)
    # is not read as an issue number; `&#123;` HTML entities excluded via the `&` lookbehind.
    # (Issue numbers realistically run 1-5 digits; a 6-digit ref is far more likely a colour.)
    (re.compile(r"(?<![\w&])#[0-9]{1,5}(?![0-9A-Fa-f])"), "hardcoded issue reference (#NNN)"),
    # Multica issue keys only — `GH-NN` is deliberately NOT here: the repo-meta-structure
    # checklist uses GH-01..GH-09 as check IDs (like MEM-xx / HOOK-01), not issue refs.
    (re.compile(r"(?<![\w-])(?:MUL|DEV)-[0-9]+(?![\w-])"), "hardcoded issue reference"),
    (re.compile(r"(?<![\w-])(?:da|wb)#[0-9]+"), "hardcoded issue reference"),
]

# ── Machine-tied content: always a defect, no `requires:` declaration excuses it. ──
# Precise continuations (a real path char after the prefix) so instructional mentions like
# "avoid /Users/... paths" or "~/Documents|Desktop" do not false-positive.
HARD_MACHINE = [
    (re.compile(r"/Users/[A-Za-z]"), "machine-absolute path (/Users/...)"),
    (re.compile(r"hsb-2026"), "personal vault name 'hsb-2026'"),
    (re.compile(r"--break-system-packages"), "non-portable pip flag --break-system-packages"),
    (re.compile(r"(?:~|\$HOME)/(?:Documents|Desktop)/"), "personal home-folder path (~/Documents, ~/Desktop)"),
]

# ── Machine-local tools: legal ONLY with a covering roster `requires:` (cli:<tool>). ──
DOTFILES_PATH = re.compile(r"(?:~|\$HOME)/(?:dotfiles|Developer)\b")
LOCAL_TOOLS = (
    "agy", "capture-console-errors", "cc-hooks", "cc-project-memory",
    "check-tool-updates", "da-prune-sessions", "dcode", "fetch-docs",
    "mcp-secrets-sync", "migrate-claude-memory", "models-dev", "project-activity",
    "speak_gemini", "speak_kokoro",
)
LOCAL_TOOL_RX = {t: re.compile(rf"(?<![\w./-]){re.escape(t)}(?![\w-])") for t in LOCAL_TOOLS}

# ── Secret literals — precision over recall (obvious credential shapes only). ──
SECRET_LITERAL = [
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}"), "GitHub PAT literal"),
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained PAT literal"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "API secret-key literal (sk-...)"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access-key id literal"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "embedded private key"),
]

XML_TAG = re.compile(r"</?[A-Za-z][^>\n]*>")


def _requires_by_source():
    """Map each roster source path -> the set of its `requires:` words."""
    out = {}
    for e in parse_roster(os.path.join(REPO, "primitives-core.yaml")):
        out[e.get("source", "")] = set(_list(e.get("requires", "")))
    return out


def _owning_source(rel):
    """The roster source path that owns a repo-relative file (its skill/agent/hook dir)."""
    parts = rel.split(os.sep)
    if len(parts) >= 3 and parts[0] == "primitives-core" and parts[1] in ("skills", "hooks"):
        return os.path.join(parts[0], parts[1], parts[2])
    if len(parts) >= 3 and parts[1] == "agents":
        return os.path.join(parts[0], parts[1], parts[2])  # agents/<name>.md
    return None


def _frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    return m.group(1) if m else None


def _fm_has(fm, key):
    return fm is not None and re.search(rf"^{re.escape(key)}:\s*\S", fm, re.M) is not None


def _fm_value(fm, key):
    if fm is None:
        return ""
    m = re.search(rf"^{re.escape(key)}:(.*?)(?=^\S|\Z)", fm, re.S | re.M)
    return m.group(1) if m else ""


def scan_file(fp, rel, requires, problems):
    try:
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            body = fh.read()
    except OSError as e:
        problems.append(f"{rel}: unreadable ({e})")
        return
    for rx, why in IDENTITY:
        if rx.search(body):
            problems.append(f"{rel}: {why}")
    for rx, why in HARD_MACHINE:
        if rx.search(body):
            problems.append(f"{rel}: {why}")
    for rx, why in SECRET_LITERAL:
        if rx.search(body):
            problems.append(f"{rel}: {why}")
    if DOTFILES_PATH.search(body) and "env:dotfiles" not in requires:
        problems.append(f"{rel}: ~/dotfiles or ~/Developer path without `requires: [env:dotfiles]`")
    for tool, rx in LOCAL_TOOL_RX.items():
        if rx.search(body) and f"cli:{tool}" not in requires and "env:dotfiles" not in requires:
            problems.append(f"{rel}: machine-local tool '{tool}' without `requires: [cli:{tool}]`")


def check_frontmatter(fp, rel, is_skill, problems):
    with open(fp, encoding="utf-8", errors="ignore") as fh:
        text = fh.read()
    fm = _frontmatter(text)
    for need in ("name", "description"):
        if not _fm_has(fm, need):
            problems.append(f"{rel}: frontmatter missing `{need}`")
    if is_skill:
        tags = XML_TAG.findall(_fm_value(fm, "description"))
        if tags:
            found = ", ".join(sorted(set(tags)))
            problems.append(
                f"{rel}: description contains XML tag(s) {found} — Claude Cowork refuses to "
                f"load such a skill (use a bracket-free placeholder)"
            )


def main():
    problems = []
    req_by_src = _requires_by_source()
    for root in SCAN_ROOTS:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            # plugin metadata (.claude-plugin/plugin.json) is the sanctioned identity
            # surface; symlinked bodies are scanned once, at their source
            _dirs[:] = [d for d in _dirs if d != ".claude-plugin"]
            for f in sorted(files):
                fp = os.path.join(dirpath, f)
                if os.path.islink(fp):
                    continue
                rel = os.path.relpath(fp, REPO)
                src = _owning_source(rel)
                requires = req_by_src.get(src, set()) if src else set()
                if f.endswith(TEXT_EXT):
                    scan_file(fp, rel, requires, problems)
                if f == "SKILL.md":
                    check_frontmatter(fp, rel, True, problems)
                elif root.endswith("agents") and f.endswith(".md") and f.lower() != "readme.md":
                    check_frontmatter(fp, rel, False, problems)

    problems = sorted(set(problems))
    if problems:
        print(f"✗ identity-neutrality: {len(problems)} violation(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("✓ identity-neutral — no name/org/repo/issue hardcoded in any shipped body")
    return 0


if __name__ == "__main__":
    sys.exit(main())

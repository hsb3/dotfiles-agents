#!/usr/bin/env python3
"""Identity-neutrality lint — D6 machine-floor check 1 (entry-gate spec, decision 0013 item 9).

No name / org / repo / issue is hardcoded in any SHIPPED artifact; personalization reaches a
skill only through data surfaces (the roster's `requires:`, a repo's own config), never baked
into a primitive body. This is the vendored, in-repo successor to the archived workbench
`scripts/promote_check.py` H2/H5 checks — no cross-repo import at runtime.

Scope = the shipped primitive bodies under `primitives-core/{skills,agents,commands,hooks}/`,
plus the symlink-assembly tree `plugins/` (decision-030): bundle READMEs are regular files there,
and each standalone wrapper's README travels with its skill
(`primitives-core/skills/<id>/README.md`,
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
    `name` + `description`. Presence is not enough: a plain scalar YAML cannot parse takes
    the whole block down silently, so unquoted values are checked for parseability too.
  - description hygiene — no XML/angle-bracket tag in a SKILL.md `description` (Claude Cowork
    refuses to load such a skill), and no `description` over MAX_DESCRIPTION chars once folded
    (opencode's hard limit, applied here to EVERY skill — `gen_opencode.py` enforces the same
    number but only sees skills rostered `targets: [.., opencode]`). The length cap is a
    deliberate forward-guard with ZERO real subjects: every shipped description is comfortably
    under it today, so it can only fail on a future one. Its red-ability lives in the fixture
    tests, not in the tree.
  - secret hygiene — no literal credential (token/key) baked into a body.
  - portability — machine-tied content is banned outright (absolute /Users paths, personal
    home-folder locations, personal vault name, non-portable install flags); a machine-local
    tool name is a defect wherever it appears — in a shipped body OR as a roster
    `requires: cli:<tool>` entry. A `requires:` declaration never excuses the mention.
  - issue reference — no bare `#NNN` (or MUL-/DEV-/da#/wb#) issue key baked into a shipped
    body: an issue number is repo-specific personalization, and a shipped primitive must stay
    portable across repos (entered a3d1014, 2026-07-17, entry-gate D6, decision 0013 item 9).
    Carve-out: a file under an `examples/` directory is exempt from THIS rule only — sample
    content demonstrating ref-linkify has to contain a ref, and a ref inside `examples/` is
    self-evidently demo data, not real personalization. Every other identity rule (name, org,
    repo slug, secrets, absolute paths, machine-tied content, frontmatter) still applies inside
    `examples/` unchanged.

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
    os.path.join(REPO, "primitives-core", "commands"),
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
]

# ── Issue refs: repo-specific personalization, kept separate from IDENTITY above so the
# `examples/` carve-out can exempt this rule ONLY, never the name/org/repo tokens above it. ──
ISSUE_REF = [
    # Capped at 5 digits + a hex-char lookahead so a 6-hex-digit colour (#003366) is not read
    # as an issue number; `&#123;` HTML entities excluded via the `&` lookbehind.
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

# ── Machine-local tools: a finding wherever they appear. ──
# These exist only on the owner's machines (hsb3/dev-journey `packages/`; keep the list
# current with that directory). A body mention is a defect regardless of `requires:`, and a
# roster `requires: cli:<tool>` naming one is itself a defect: `cli:` must name a tool with a
# public install path (brew, uv, bun, GitHub release). A stdlib-only script a skill needs
# ships as an asset under its `scripts/`, invoked by <plugin-root> path.
DOTFILES_PATH = re.compile(r"(?:~|\$HOME)/(?:dotfiles|Developer)\b")
LOCAL_TOOLS = (
    "agy", "brewup", "camera-log", "capture-console-errors", "cc-hooks",
    "cc-migrate-memory", "cc-project-memory", "check-config-drift", "check-reminders",
    "check-tool-updates", "check-tools", "da-prune-sessions", "dcode",
    "dev-cleanup-report", "disk-cleanup", "fetch-docs", "find-mcp-servers",
    "gh-runner-fallback", "json-to-csv", "mcp-secrets-sync", "models-dev",
    "project-activity", "speak_gemini", "speak_kokoro", "upgrade-globals",
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

# Same number as scripts/gen_opencode.py's MAX_DESCRIPTION (opencode's own hard limit), which
# only sees skills rostered `targets: [.., opencode]` — so the cap is repeated here to cover
# every skill, and a test asserts the two constants stay equal.
MAX_DESCRIPTION = 1024


def _requires_by_source():
    """Map each roster source path -> the set of its `requires:` words."""
    out = {}
    for e in parse_roster(os.path.join(REPO, "primitives-core.yaml")):
        out[e.get("source", "")] = set(_list(e.get("requires", "")))
    return out


def _vendored_bases():
    """Repo-relative `<source>/base` prefix for every `origin: vendored` roster entry.

    A vendored body is third-party bytes held verbatim under `base/` (docs/vendoring-rule.md):
    it carries none of OUR personalization, and it cannot be corrected here — a hand-edit
    registers as `diverged` against the pinned ref and fails the vendored-drift gate. So the
    IDENTITY token scan, whose whole subject is our own name/org/repo/issue leaking into a
    shipped body, is both inapplicable and unfixable there. Derived from the roster rather
    than hardcoded, so a new vendored entry is covered the day it lands.

    Machine-tied paths and secret literals are still scanned: those would be real defects in
    any bytes we ship, whoever wrote them.
    """
    bases = []
    for e in parse_roster(os.path.join(REPO, "primitives-core.yaml")):
        if (e.get("origin") or "").strip() == "vendored":
            bases.append(os.path.join(e.get("source", ""), "base") + os.sep)
    return tuple(b for b in bases if b.strip(os.sep))


def _owning_source(rel):
    """The roster source path that owns a repo-relative file (its skill/agent/command/hook)."""
    parts = rel.split(os.sep)
    if len(parts) >= 3 and parts[0] == "primitives-core" and parts[1] in ("skills", "hooks"):
        return os.path.join(parts[0], parts[1], parts[2])
    if len(parts) >= 3 and parts[1] in ("agents", "commands"):
        # flat-file primitives: agents/<name>.md, commands/<name>.md
        return os.path.join(parts[0], parts[1], parts[2])
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


# Faults a plain (unquoted, non-block) YAML scalar cannot survive. Claude Code drops
# EVERY frontmatter field silently when the block fails to parse — no error, no partial
# load — so an agent with a colon in its description ships with no model, no tools, and
# no colour while `make ci` stays green. Quoting the value is the fix in every case.
#
# Deliberately three rules, not a YAML validator: stdlib has no YAML parser (zero-install
# is an invariant), and these are the faults that actually reach the shipped tree. Block
# scalars (`|`, `>`, `>-`) are valid and common here, so a value that opens one is exempt
# — its content lives on the indented lines this scan already skips.
PLAIN_SCALAR_FAULTS = (
    (lambda v: ": " in v, "contains ': ' — YAML reads it as a nested mapping and the "
                          "whole block fails to parse"),
    (lambda v: v.endswith(":"), "ends with ':' — YAML reads it as a nested mapping key"),
    (lambda v: " #" in v, "contains ' #' — YAML truncates the value at the comment"),
)


def _plain_scalar_faults(fm):
    """(key, why) for every top-level frontmatter key whose unquoted scalar value YAML
    would reject or silently truncate. Quoted values and block scalars are exempt."""
    if fm is None:
        return
    for line in fm.splitlines():
        # indented -> a block scalar's content or a mapping child, not a top-level key
        if not line.strip() or line[:1].isspace() or line.lstrip().startswith("#"):
            continue
        colon = line.find(":")
        if colon == -1:
            continue
        key, value = line[:colon].strip(), line[colon + 1:].strip()
        if not value or value[:1] in ("'", '"', "|", ">"):
            continue
        for predicate, why in PLAIN_SCALAR_FAULTS:
            if predicate(value):
                yield key, why


def _in_examples_dir(rel):
    """True if the repo-relative path has a path segment exactly `examples` — the
    ref-linkify carve-out (issue refs only; every other rule still applies there)."""
    return "examples" in rel.split(os.sep)


def scan_file(fp, rel, requires, problems, skip_identity=False, skip_issue_ref=False):
    try:
        with open(fp, encoding="utf-8", errors="ignore") as fh:
            body = fh.read()
    except OSError as e:
        problems.append(f"{rel}: unreadable ({e})")
        return
    if not skip_identity:
        for rx, why in IDENTITY:
            if rx.search(body):
                problems.append(f"{rel}: {why}")
        if not skip_issue_ref:
            for rx, why in ISSUE_REF:
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
        if rx.search(body):
            problems.append(f"{rel}: machine-local tool '{tool}' (ship the script as a skill asset)")


def check_roster_requires(entries, problems):
    """A roster `requires: cli:<tool>` naming a machine-local tool is a finding."""
    for e in entries:
        for word in _list(e.get("requires", "")):
            if word.startswith("cli:") and word[4:] in LOCAL_TOOLS:
                problems.append(
                    f"primitives-core.yaml: {e.get('id', '?')} requires `{word}`, a machine-local "
                    f"tool (cli: must name a publicly installable tool)")


def check_frontmatter(fp, rel, is_skill, problems):
    with open(fp, encoding="utf-8", errors="ignore") as fh:
        text = fh.read()
    fm = _frontmatter(text)
    for need in ("name", "description"):
        if not _fm_has(fm, need):
            problems.append(f"{rel}: frontmatter missing `{need}`")
    for key, why in _plain_scalar_faults(fm):
        problems.append(f"{rel}: frontmatter `{key}` {why} — quote the value")
    if is_skill:
        # Byte-for-byte the normalization gen_opencode.skill_problems applies, so both gates
        # measure any one skill identically. It is NOT the YAML value's true length: a block
        # marker's chomp char, quote chars and a stripped `#` comment all survive (erring
        # high, so nothing over-long slips through), and internal whitespace runs collapse.
        desc = " ".join(_fm_value(fm, "description").split()).lstrip(">").strip()
        if len(desc) > MAX_DESCRIPTION:
            problems.append(
                f"{rel}: description is {len(desc)} chars, over the {MAX_DESCRIPTION} cap "
                f"— trim it to what the skill does plus when it triggers"
            )
        tags = XML_TAG.findall(_fm_value(fm, "description"))
        if tags:
            found = ", ".join(sorted(set(tags)))
            problems.append(
                f"{rel}: description contains XML tag(s) {found} — Claude Cowork refuses to "
                f"load such a skill (use a bracket-free placeholder)"
            )


def main():
    problems = []
    check_roster_requires(parse_roster(os.path.join(REPO, "primitives-core.yaml")), problems)
    req_by_src = _requires_by_source()
    vendored = _vendored_bases()
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
                    scan_file(fp, rel, requires, problems,
                              skip_identity=rel.startswith(vendored),
                              skip_issue_ref=_in_examples_dir(rel))
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

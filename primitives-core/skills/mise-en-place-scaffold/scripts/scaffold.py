#!/usr/bin/env python3
"""Mise-en-place scaffold — fill-only repo setup against the packaged standards.

The pair to the read-only repo-compliance-audit: the audit measures, this fills the gaps.
One code path serves brownfield compliance and new-repo setup: run against any git repo
(including a fresh `git init`), it plans and creates exactly the structure the standards'
checklists require, sourcing content from the repo-meta-structure standard's assets. It
carries no templates of its own.

Modes:
  --plan (default)  print what would be created, per checklist ID, plus conflicts and
                    non-mechanical items — writes NOTHING.
  --apply           create only the planned items. Additive-only; there is no overwrite
                    mode at all.
  --init-manifest   write the commented `_meta/mise-en-place.yml` template when none
                    exists (never overwrites an existing manifest).

Properties (by construction):
  - NEVER overwrites, merges, edits, deletes, or moves an existing file. A file that
    differs from a standard template is reported as a CONFLICT with a diff and left
    byte-identical; files whose checklist pass condition is existence-only are simply OK.
  - Idempotent: a second run plans zero creations; a conformant repo is a no-op.
  - Reports non-mechanical items (AVOID files, inline hooks, authored docs) with
    guidance — it never acts on them. README.md / CLAUDE.md / AGENTS.md are authored
    content (agent-dot-md-authoring, readme-value-and-proof); inline-hook migration is
    deferred to the hook-composition standard.
  - No GitHub-side provisioning: `gh_*` / `board_title` manifest fields are declared for
    the github-project-board skill; this script touches only in-repo files.
  - No `git add` / `git commit`: staging the scaffolded files is the owner's call.

Checklist + manifest contract: rows come from the standards' checklist files (same
contract as audit.py); per-repo variance comes from `_meta/mise-en-place.yml`. The
manifest field set is documented in ../references/manifest.md (format owned here).

SYNC NOTE — duplicated reader functions: each skill bundle is copied independently at
build time, so a shared module cannot be imported across skill bundles. The pure
functions parse_checklist / load_manifest / variance_rows / plans_scope /
frontmatter_keys / hook_commands / is_script_invocation (and their regexes) are
duplicated from repo-compliance-audit/scripts/audit.py — that file is the source to keep
in sync. load_manifest here additionally warns on unknown top-level keys (the audit
skips them silently); acceptance semantics for audit-known fields are identical.

Usage (from the scaffolded repo root):
  python3 scaffold.py [--plan | --apply | --init-manifest] [--plugin-root PATH]

Plugin root resolution: $CLAUDE_PLUGIN_ROOT (set by the harness) or --plugin-root. The
root must contain skills/repo-meta-structure/{references/checklist.md,assets/} and
skills/project-memory/references/checklist.md.

Stdlib-only (no pyyaml): tailored manifest reader, same stance as scripts/translate.py
in dotfiles-agents.
"""

import argparse
import difflib
import json
import os
import re
import shlex
import subprocess
import sys

EXIT_OK = 0  # plan/apply printed — conflicts do NOT change the exit code (report, don't police)
EXIT_ERROR = 2  # hard error: nothing planned, nothing written

CHECKLIST_RELPATHS = (
    os.path.join("skills", "repo-meta-structure", "references", "checklist.md"),
    os.path.join("skills", "project-memory", "references", "checklist.md"),
)

ASSETS_RELPATH = os.path.join("skills", "repo-meta-structure", "assets")

MANIFEST_RELPATH = os.path.join("_meta", "mise-en-place.yml")

# The one script-sourced row (same sanctioned exception as audit.py: sourced from the
# hooks-as-script-plus-config decision until the hook-composition standard lands).
HOOK_ROW = {
    "id": "HOOK-01",
    "area": "hooks",
    "type": "no-inline-hooks",
    "arg": os.path.join(".claude", "settings.json"),
    "debt": False,
    "source": "hooks-as-script-plus-config decision",
}

# Row actions
CREATE, OK, CONFLICT, MANUAL = "CREATE", "OK", "CONFLICT", "MANUAL"

CHECK_ROW_RE = re.compile(
    r"^\|\s*(?P<id>[A-Z]+-\d+)\s*\|\s*(?P<area>[^|]+?)\s*\|\s*"
    r"`(?P<type>[a-z-]+):\s*(?P<arg>[^`]+?)`\s*\|\s*(?P<cond>[^|]*?)\s*\|\s*$"
)

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")

FRONTMATTER_KEY_RE = re.compile(r"^([\w-]+):", re.M)

SHELL_META_RE = re.compile(r"[;|&<>`\n]|\$\(")
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
INTERPRETERS = {
    "bash",
    "sh",
    "zsh",
    "dash",
    "python",
    "python3",
    "node",
    "bun",
    "deno",
    "uv",
    "npx",
}


class ScaffoldError(Exception):
    """Hard failure — abort with a single clear error; nothing written."""


# ── stub content (existence-only rows the standard requires but ships no asset for) ────
# These rows' pass condition is "file exists"; content is repo-specific, so an existing
# file is always OK (never a conflict) and the scaffold writes a minimal functional stub
# only when the file is missing.

META_README_STUB = """# `_meta/` — the local working desk

Tracked by default (ADR-0006); the only ignored path is `operations/` content (its
secrets/live-ops material), plus tool caches and OS litter. Desk content is
clone-survivable by default; deliberately-local scratch belongs in `operations/` or
outside the repo.

| Entry | Purpose |
|---|---|
| `_archive/` | Superseded working material — moved, never deleted |
| `briefings/` | Dated readouts (`yyyy-mm-dd-subject/`) |
| `plans/` | The code planning desk — issue bodies and build plans, tracked; `plans/inbox/` receives communication-package intake |
| `operations/` | Live URLs, credentials, runbooks with secrets — never tracked, never in `docs/` |
| `research/` | Live investigations; findings graduate to `docs/` or issues |
| `HANDOFF.md` | Cold-start bridge — tracked, secret-free |
| `README.md` | This file — states the taxonomy |
| `mise-en-place.yml` | Per-repo variance manifest — tracked |
"""

HANDOFF_STUB = """# HANDOFF

_Cold-start bridge: what a brand-new session must know before working here. Tracked by
default (ADR-0006); keep it secret-free (secrets live in `_meta/operations/`). This is a
scaffolded skeleton — fill it via the handoff skill at the first session boundary._

## 0. Orientation

## 1. Current standing & top priority

## 2. What the last substantial session delivered

## 3. Where to start building

## 4. Conventions & gotchas

## 5. Incident log
"""

MAKEFILE_STUB = """# Makefile — the canonical task interface (`make help` lists targets).
# Scaffolded stub: add this repo's real targets; CI and docs should reference
# make targets, not raw commands.
.DEFAULT_GOAL := help
.PHONY: help

help: ## List targets
\t@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\\n", $$1, $$2}'
"""

MCP_JSON_STUB = '{\n  "mcpServers": {}\n}\n'

SETTINGS_JSON_STUB = "{}\n"

# Shape mirrors the MEMORY_STUB in ~/.local/bin/cc-project-memory (`init` creates the
# index only when absent, so any scaffolded index makes a later `init` a no-op for the
# files it owns). One deliberate rewording: cc-project-memory's literal example line
# `- [Title](file.md) — short hook` parses as a dangling relative link under the
# audit's MEM-04 index-links-resolve check, so the format hint here avoids markdown
# link syntax.
MEMORY_INDEX_STUB = """<!-- Project auto-memory index for {repo}. Tracked in this repo so learnings travel
across machines and can be mined for global patterns. Claude writes here automatically;
edit or prune freely. Global/user memory lives separately in ~/.claude/memory/ (curated).
Keep this file an index: one line per memory file. First 200 lines load every session. -->

# Project memory — {repo}

_Index format: one line per memory file — a markdown link to the topic file, then a short hook._
"""

STUB_FILES = {
    "_meta/README.md": lambda repo: META_README_STUB,
    "_meta/HANDOFF.md": lambda repo: HANDOFF_STUB,
    ".claude/settings.json": lambda repo: SETTINGS_JSON_STUB,
    ".claude/memory/MEMORY.md": lambda repo: MEMORY_INDEX_STUB.format(
        repo=os.path.basename(repo)
    ),
    "Makefile": lambda repo: MAKEFILE_STUB,
    ".mcp.json": lambda repo: MCP_JSON_STUB,
}

# Authored content the scaffold NEVER writes — those rows stay flagged for the
# authoring skills.
AUTHORED_FILES = {
    "README.md": "authored content — owner: the readme-value-and-proof skill",
    "CLAUDE.md": "authored content — owner: the agent-dot-md-authoring skill",
    "AGENTS.md": "authored content — owner: the agent-dot-md-authoring skill",
    "docs/CHARTER.md": "authored content — the repo's canonical precedence page; never scaffolded",
}

MANIFEST_TEMPLATE = """\
# _meta/mise-en-place.yml — per-repo variance manifest (tracked by default; ADR-0006).
# The standards define the invariants; this file is the ONLY home for per-repo variance.
# Field reference: the mise-en-place-scaffold skill's references/manifest.md.
# Readers: repo-compliance-audit + mise-en-place-scaffold consume default_branch,
# required_folders, required_files; the gh_* / board_title fields are declared here for
# the github-project-board skill. Unknown fields are tolerated by both readers.
owner: ""            # e.g. your GitHub owner
repo: ""
default_branch: main # e.g. dev in some orgs
gh_issue_labels: []  # [{name, color, description}] — consumed by github-project-board
gh_milestones: []    # [{title, description}] — consumed by github-project-board
board_title: ""
required_folders: [] # repo-specific additions beyond the standard
required_files: []
"""


# ── checklist loading (duplicated from audit.py — see SYNC NOTE) ────────────────────────


def load_checklists(plugin_root):
    """Parse the standards' checklist tables into ordered row dicts."""
    rows = []
    for rel in CHECKLIST_RELPATHS:
        path = os.path.join(plugin_root, rel)
        if not os.path.isfile(path):
            raise ScaffoldError(
                f"checklist file missing: {path} — broken plugin install; "
                f"refusing to scaffold against a partial checklist"
            )
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        file_rows = parse_checklist(text)
        if not file_rows:
            raise ScaffoldError(f"checklist file has no parseable rows: {path}")
        rows.extend(file_rows)
    return rows


def parse_checklist(text):
    """Extract `ID | Area | Check | Pass condition` rows from a checklist markdown file."""
    rows = []
    for line in text.splitlines():
        m = CHECK_ROW_RE.match(line.strip())
        if not m:
            continue
        rows.append(
            {
                "id": m.group("id"),
                "area": m.group("area"),
                "type": m.group("type"),
                "arg": m.group("arg").strip(),
                "debt": "(migration debt)" in m.group("cond"),
                "source": "standard",
            }
        )
    return rows


# ── manifest reader (duplicated from audit.py — see SYNC NOTE) ──────────────────────────
# Scaffold-side field set. The audit consumes only AUDIT_KNOWN fields; everything the
# audit does not know it tolerates silently. This reader knows the full manifest schema
# (owned here), parses the same audit-side fields with identical semantics, tolerates
# the github-project-board fields without deep-parsing them, and WARNS on truly unknown
# top-level keys instead of skipping silently.

KNOWN_SCALAR_KEYS = {"default_branch", "owner", "repo", "board_title"}
KNOWN_LIST_KEYS = {"required_folders", "required_files"}
KNOWN_BLOCK_KEYS = {"gh_issue_labels", "gh_milestones"}  # github-project-board's fields
AUDIT_STRICT_KEYS = {
    "default_branch"
} | KNOWN_LIST_KEYS  # keys audit.py parses strictly


def load_manifest(repo):
    """Tailored stdlib reader for `_meta/mise-en-place.yml`.

    Returns (manifest, warnings). {} when absent — a missing manifest is not a gap;
    defaults apply. Malformed KNOWN fields or unparseable top-level syntax abort;
    unknown top-level keys produce a warning and are ignored (forward compatibility).
    Acceptance semantics for audit-known fields match audit.py's load_manifest exactly:
    a manifest accepted by one reader is accepted by the other.
    """
    path = os.path.join(repo, MANIFEST_RELPATH)
    warnings = []
    if not os.path.isfile(path):
        return {}, warnings
    manifest = {}
    current_key = None  # known list key currently collecting items
    in_tolerated_block = False
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line[0].isspace():  # top-level line
                current_key, in_tolerated_block = None, False
                m = re.match(r"^([\w-]+):\s*(.*?)\s*(?:#.*)?$", line)
                if not m:
                    raise ScaffoldError(
                        f"malformed manifest {MANIFEST_RELPATH} line {lineno}: {stripped!r} "
                        f"(expected `key: value` or `key:` + list items)"
                    )
                key, value = m.group(1), m.group(2)
                if key in KNOWN_SCALAR_KEYS:
                    if not value and key in AUDIT_STRICT_KEYS:
                        raise ScaffoldError(
                            f"malformed manifest {MANIFEST_RELPATH} line {lineno}: "
                            f"`{key}` needs a scalar value"
                        )
                    manifest[key] = value.strip("\"'")
                    # audit.py treats non-audit scalars as unknown blocks; mirror that
                    # tolerance so both readers accept the same manifests
                    in_tolerated_block = key not in AUDIT_STRICT_KEYS
                elif key in KNOWN_LIST_KEYS:
                    if value and value != "[]":
                        m_inline = re.match(r"^\[(.*)\]$", value)
                        if not m_inline:
                            raise ScaffoldError(
                                f"malformed manifest {MANIFEST_RELPATH} line {lineno}: "
                                f"`{key}` must be a list"
                            )
                        manifest[key] = [
                            v.strip().strip("\"'")
                            for v in m_inline.group(1).split(",")
                            if v.strip()
                        ]
                    else:
                        manifest[key] = manifest.get(key, [])
                        current_key = key
                elif key in KNOWN_BLOCK_KEYS:
                    # declared for github-project-board; not consumed here, block tolerated
                    in_tolerated_block = True
                else:
                    warnings.append(
                        f"unknown manifest field `{key}` "
                        f"({MANIFEST_RELPATH} line {lineno}) — ignored"
                    )
                    in_tolerated_block = True
            else:  # indented line
                m_item = re.match(r"^\s+-\s+(.*?)\s*(?:#.*)?$", line)
                if current_key is not None:
                    if not m_item:
                        raise ScaffoldError(
                            f"malformed manifest {MANIFEST_RELPATH} line {lineno}: "
                            f"expected `- item` under `{current_key}`, got {stripped!r}"
                        )
                    manifest[current_key].append(m_item.group(1).strip("\"'"))
                elif in_tolerated_block:
                    continue  # nested content of a field this script does not consume
                else:
                    raise ScaffoldError(
                        f"malformed manifest {MANIFEST_RELPATH} line {lineno}: "
                        f"unexpected indented line {stripped!r}"
                    )
    return manifest, warnings


def variance_rows(manifest):
    """Extra rows declared by the repo's manifest (created if missing, not just noted)."""
    rows = []
    n = 0
    for key, kind in (("required_folders", "folder"), ("required_files", "file")):
        for item in manifest.get(key, []):
            n += 1
            arg = item if kind == "file" else item.rstrip("/") + "/"
            rows.append(
                {
                    "id": f"VAR-{n:02d}",
                    "area": "manifest",
                    "type": "path-exists",
                    "arg": arg,
                    "debt": False,
                    "source": MANIFEST_RELPATH,
                }
            )
    return rows


# ── read-only probes (duplicated from audit.py — see SYNC NOTE) ─────────────────────────


def git_toplevel(cwd):
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:  # pragma: no cover — git always present in CI
        raise ScaffoldError(f"git not available: {e}") from e
    if r.returncode != 0:
        raise ScaffoldError(
            f"not a git repository: {cwd} (scaffold runs from a repo root)"
        )
    return r.stdout.strip()


def check_ignore(repo, probe):
    """git check-ignore exit code for a probe path: 0 = ignored, 1 = not ignored."""
    r = subprocess.run(
        ["git", "check-ignore", "-q", "--", probe],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if r.returncode not in (0, 1):
        raise ScaffoldError(
            f"git check-ignore failed for {probe!r}: {r.stderr.strip()}"
        )
    return r.returncode


def working_tree_dirty(repo):
    """True when `git status --porcelain` reports anything. --no-optional-locks keeps
    the probe from refreshing the index, preserving the read-only property of --plan
    and the byte-stability of a repeated --apply."""
    r = subprocess.run(
        ["git", "--no-optional-locks", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return bool(r.stdout.strip())


def plans_scope(repo):
    """Every *.md under _meta/plans/ (recursive), excluding README.md, any path
    component starting with `_` (desk config such as `_config.md`, `_utils/`), and
    `issue-body.md` (a staged body is the raw publishable GitHub issue body, kept
    byte-identical to the live issue — exempt from the frontmatter schema per the
    owner ruling 2026-07-02)."""
    root = os.path.join(repo, "_meta", "plans")
    docs = []
    if not os.path.isdir(root):
        return docs
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(("_", ".")))
        for fn in sorted(filenames):
            if (
                not fn.endswith(".md")
                or fn in ("README.md", "issue-body.md")
                or fn.startswith("_")
            ):
                continue
            docs.append(os.path.join(dirpath, fn))
    return docs


def frontmatter_keys(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return set()
    return set(FRONTMATTER_KEY_RE.findall(m.group(1)))


def dangling_index_links(repo, arg):
    """Dangling relative links in an index file (MEM-04 semantics), or [] if none."""
    index = os.path.join(repo, arg)
    base = os.path.dirname(index)
    dangling = []
    with open(index, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            for target in MD_LINK_RE.findall(line):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target):  # absolute URL scheme
                    continue
                if target.startswith("#") or target.startswith("/"):
                    continue
                rel = target.split("#", 1)[0]
                if not rel:
                    continue
                if not os.path.exists(os.path.join(base, rel)):
                    dangling.append(f"line {lineno}: ({target}) does not resolve")
    return dangling


def hook_commands(settings):
    """Every `type: command` command string anywhere under the settings' `hooks` key."""
    cmds = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "command" and isinstance(node.get("command"), str):
                cmds.append(node["command"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(settings.get("hooks", {}))
    return cmds


def is_script_invocation(cmd):
    """True when the command is a plain invocation of a script by path."""
    if SHELL_META_RE.search(cmd):
        return False
    try:
        toks = shlex.split(cmd)
    except ValueError:
        return False
    while toks and ENV_ASSIGN_RE.match(toks[0]):
        toks = toks[1:]
    if not toks:
        return False
    if os.path.basename(toks[0]) in INTERPRETERS:
        rest = [t for t in toks[1:] if not t.startswith("-")]
        if rest and rest[0] == "run":  # `uv run script.py`
            rest = rest[1:]
        candidate = rest[0] if rest else ""
    else:
        candidate = toks[0]
    return "/" in candidate


# ── planning ────────────────────────────────────────────────────────────────────────────

CLAUDE_REVIEW_ARG = ".github/workflows/claude-review.yml"
# `pull_request:` / `pull_request_target:` only — must NOT match the tag workflow's
# `pull_request_review:` / `pull_request_review_comment:` triggers (claude.yml is a
# claude-code-action workflow too, but not a review-on-push).
PR_TRIGGER_RE = re.compile(r"^\s*pull_request(_target)?\s*:", re.M)

CI_WORKFLOW_ARG = ".github/workflows/ci.yml"
# Workflows that cannot run until the repo carries an Anthropic credential secret.
SECRET_WORKFLOW_ARGS = (CLAUDE_REVIEW_ARG, ".github/workflows/claude.yml")
# A `ci:` rule at column 0 — the aggregate gate the standard ci.yml template invokes.
CI_TARGET_RE = re.compile(r"^ci\s*:", re.M)


def makefile_has_ci_target(repo):
    """True when the target repo's Makefile defines a `ci:` target. The standard
    ci.yml template runs `make ci`; a repo without the target gets a red check on its
    first push (fleet-dashboard test-bed finding). The Makefile stub deliberately
    ships without a no-op `ci:` — a green gate that runs nothing would be worse."""
    path = os.path.join(repo, "Makefile")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            return bool(CI_TARGET_RE.search(fh.read()))
    except (OSError, UnicodeDecodeError):
        return False


def existing_review_workflows(repo):
    """Workflow files that already run claude-code-action on pull_request — a
    claude-review.yml equivalent under another name. Creating the standard file
    alongside one doubles the AI reviews and token spend per push (Gate-2 pilot
    finding), so GH-08 reports MANUAL instead of planning a duplicate."""
    wf_dir = os.path.join(repo, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        return []
    hits = []
    for fn in sorted(os.listdir(wf_dir)):
        if not fn.endswith((".yml", ".yaml")):
            continue
        path = os.path.join(wf_dir, fn)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue
        if "claude-code-action" in text and PR_TRIGGER_RE.search(text):
            hits.append(".github/workflows/" + fn)
    return hits


def template_source(plugin_root, arg):
    """Asset path for a template-backed file row, or None. The scaffold carries no
    templates of its own: content comes from the repo-meta-structure standard's assets
    (structure-preserving copy)."""
    if arg == ".gitignore":
        return os.path.join(plugin_root, ASSETS_RELPATH, "gitignore.template")
    if arg == "lefthook.yml":
        return os.path.join(plugin_root, ASSETS_RELPATH, "lefthook.template.yml")
    if arg.startswith(".github/"):
        return os.path.join(
            plugin_root, ASSETS_RELPATH, "github", arg[len(".github/") :]
        )
    if arg in AUTHORED_FILES:
        return None  # authored content never has a template (planner intercepts too)
    if arg.startswith("docs/") and not arg.endswith("/"):
        # structure-preserving, mirroring the .github/ branch (file rows only — the
        # ROOT-08 `docs/` directory row is mkdir'd, not templated); docs/CHARTER.md
        # never reaches here (AUTHORED_FILES intercepts it first)
        return os.path.join(plugin_root, ASSETS_RELPATH, "docs", arg[len("docs/") :])
    return None


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def make_diff(rel, current, template):
    cur = current.decode("utf-8", "replace").splitlines(keepends=True)
    tpl = template.decode("utf-8", "replace").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            cur,
            tpl,
            fromfile=f"{rel} (existing — untouched)",
            tofile=f"{rel} (standard template)",
        )
    )


class PlanContext:
    """Accumulates the concrete filesystem plan while rows are classified."""

    def __init__(self):
        self.dirs = []  # relpaths ending in "/", ordered, deduped
        self.files = []  # (relpath, payload bytes), ordered, deduped
        self.conflicts = {}  # relpath -> unified diff text
        self.swallowed = []  # planned files the target repo's gitignore ignores
        self.notes = []  # follow-ups the scaffold cannot do (secrets, missing targets)

    def add_dir(self, rel):
        if rel not in self.dirs:
            self.dirs.append(rel)

    def add_file(self, rel, payload):
        if rel not in {r for r, _ in self.files}:
            self.files.append((rel, payload))

    def finalize_gitkeeps(self):
        """A planned empty directory gets a .gitkeep so it survives clone; a directory
        that receives a planned file needs none."""
        file_rels = [r for r, _ in self.files]
        for d in self.dirs:
            if not any(f.startswith(d) for f in file_rels):
                self.files.append((d + ".gitkeep", b""))

    def planned_paths(self):
        return list(self.dirs) + [r for r, _ in self.files]


def classify_path_exists(repo, plugin_root, arg, ctx):
    full = os.path.join(repo, arg)
    if arg in AUTHORED_FILES:
        if os.path.isfile(full):
            return OK, f"present: {arg} (content is authored — never scaffolded)"
        return (
            MANUAL,
            f"missing file: {arg} — {AUTHORED_FILES[arg]}; the scaffold never authors it",
        )
    if arg.endswith("/"):
        if os.path.isdir(full):
            return OK, f"present: {arg}"
        ctx.add_dir(arg)
        return CREATE, f"mkdir {arg}"
    tpl_src = template_source(plugin_root, arg)
    if tpl_src is not None:
        if not os.path.isfile(tpl_src):
            raise ScaffoldError(
                f"standard template asset missing: {tpl_src} — broken plugin install"
            )
        tpl = read_bytes(tpl_src)
        if not os.path.isfile(full):
            if arg == CLAUDE_REVIEW_ARG:
                equivalents = existing_review_workflows(repo)
                if equivalents:
                    return (
                        MANUAL,
                        f"missing file: {arg} — but an equivalent claude-code-action "
                        f"PR-review workflow already exists "
                        f"({', '.join(equivalents)}); creating the standard file "
                        f"would double the reviews per push. Rename or align it by "
                        f"hand; not scaffolded",
                    )
            ctx.add_file(arg, tpl)
            detail = f"copy standard template → {arg}"
            if arg == CI_WORKFLOW_ARG and not makefile_has_ci_target(repo):
                ctx.notes.append(
                    f"{arg}: the template runs `make ci`, but the repo's Makefile "
                    f"has no `ci` target — the workflow fails on its first run. Add "
                    f"the aggregate target and adapt the setup steps to the repo's "
                    f"toolchain (the template assumes Python)"
                )
                detail += " — no `ci` Makefile target (see note below)"
            elif arg in SECRET_WORKFLOW_ARGS:
                ctx.notes.append(
                    f"{arg}: needs the ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN "
                    f"repo secret before it can run"
                )
            return CREATE, detail
        if read_bytes(full) == tpl:
            return OK, f"matches standard template: {arg}"
        if arg not in ctx.conflicts:
            ctx.conflicts[arg] = make_diff(arg, read_bytes(full), tpl)
        return (
            CONFLICT,
            f"{arg} differs from the standard template — diff below; file untouched "
            f"(resolve by hand; the scaffold never overwrites)",
        )
    gen = STUB_FILES.get(arg)
    if gen is not None:
        if os.path.isfile(full):
            return OK, f"present: {arg} (existence is the pass condition)"
        ctx.add_file(arg, gen(repo).encode("utf-8"))
        return CREATE, f"write stub: {arg}"
    # manifest-declared file extras, or a future checklist row without a source
    if os.path.exists(full):
        return OK, f"present: {arg}"
    ctx.add_file(arg, b"")
    return CREATE, f"create empty file: {arg}"


def classify_gitignore_probe(repo, arg, want_ignored, gitignore_planned):
    if gitignore_planned:
        return OK, f"probe {arg} — will be governed by the created .gitignore (ROOT-06)"
    code = check_ignore(repo, arg)
    ignored = code == 0
    if ignored == want_ignored:
        state = "ignored" if ignored else "tracked (not ignored)"
        return OK, f"probe {arg} — {state}"
    return (
        CONFLICT,
        f"probe {arg} — gitignore semantics wrong (see ROOT-06); "
        f"the audit keeps flagging this row until the .gitignore is fixed by hand",
    )


def classify_flag_if_present(repo, arg, debt):
    if not os.path.exists(os.path.join(repo, arg)):
        return OK, f"absent: {arg}"
    if debt:
        return (
            MANUAL,
            f"migration debt: {arg} present — fold into the standard replacement "
            f"(not scaffolded; judgment call)",
        )
    return (
        MANUAL,
        f"present at root: {arg} — content belongs in _meta/; moving content is a "
        f"judgment call the scaffold never makes",
    )


def classify_frontmatter_has(repo, field):
    docs = plans_scope(repo)
    if not docs:
        return OK, "no in-scope planning docs"
    missing = [
        os.path.relpath(doc, repo) for doc in docs if field not in frontmatter_keys(doc)
    ]
    if not missing:
        return OK, f"`{field}` present in all {len(docs)} in-scope docs"
    return (
        MANUAL,
        f"authored planning docs missing `{field}`: {', '.join(missing)} — "
        f"fill by hand or via the planning-desk skill",
    )


def classify_no_inline_hooks(repo, arg, ctx):
    path = os.path.join(repo, arg)
    if not os.path.isfile(path):
        planned = arg in {r for r, _ in ctx.files}
        note = " (created empty by CLAUDE-06)" if planned else ""
        return OK, f"no {arg}{note} — no hooks defined inline"
    try:
        with open(path, encoding="utf-8") as fh:
            settings = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        return MANUAL, f"cannot parse {arg}: {e} — fix by hand; not scaffolded"
    cmds = hook_commands(settings)
    inline = [c for c in cmds if not is_script_invocation(c)]
    if not inline:
        if not cmds:
            return OK, f"no hooks defined in {arg}"
        return OK, f"{len(cmds)} hook command(s), all plain script invocations"
    return (
        MANUAL,
        f"{len(inline)} inline hook command(s) in {arg} — migration is out of scope "
        f"for the scaffold (deferred to the hook-composition standard); left in place",
    )


def classify_index_links(repo, arg, ctx):
    if not os.path.isfile(os.path.join(repo, arg)):
        if arg in {r for r, _ in ctx.files}:
            return OK, "index will be created (MEM-02) — stub has no dangling links"
        return OK, f"index absent ({arg}) — the gap is the index-presence row's"
    dangling = dangling_index_links(repo, arg)
    if not dangling:
        return OK, f"all relative links in {arg} resolve"
    return (
        MANUAL,
        f"dangling index line(s) in {arg}: {'; '.join(dangling)} — "
        f"curation judgment, not scaffolded",
    )


def compute_plan(repo, plugin_root, manifest):
    """Classify every checklist + manifest row into an action; return (actions, ctx)."""
    rows = load_checklists(plugin_root)
    rows.append(dict(HOOK_ROW))
    rows.extend(variance_rows(manifest))

    ctx = PlanContext()
    gitignore_planned = not os.path.isfile(os.path.join(repo, ".gitignore"))

    actions = []
    deferred = []  # rows classified after file plan is known (HOOK-01, MEM-04)
    for row in rows:
        t = row["type"]
        if t == "path-exists":
            action, detail = classify_path_exists(repo, plugin_root, row["arg"], ctx)
        elif t in ("gitignore-tracks", "gitignore-ignores"):
            action, detail = classify_gitignore_probe(
                repo, row["arg"], t == "gitignore-ignores", gitignore_planned
            )
        elif t == "flag-if-present":
            action, detail = classify_flag_if_present(repo, row["arg"], row["debt"])
        elif t == "frontmatter-has":
            action, detail = classify_frontmatter_has(repo, row["arg"])
        elif t == "no-inline-hooks":
            deferred.append((len(actions), row, classify_no_inline_hooks))
            actions.append({**row, "action": None, "detail": None})
            continue
        elif t == "index-links-resolve":
            deferred.append((len(actions), row, classify_index_links))
            actions.append({**row, "action": None, "detail": None})
            continue
        else:
            action, detail = (
                MANUAL,
                f"unknown check type `{t}` — not scaffoldable by this script version",
            )
        actions.append({**row, "action": action, "detail": detail})

    for idx, row, fn in deferred:  # these read ctx.files, complete after the pass
        action, detail = fn(repo, row["arg"], ctx)
        actions[idx].update(action=action, detail=detail)

    ctx.finalize_gitkeeps()
    # Gitignore-swallow probe: a planned creation the TARGET repo's own ignore rules
    # swallow is still created (additive-only, and presence-on-disk is the audit's
    # pass condition) but is invisible to `git status` and lost on a fresh clone —
    # warn per path so the owner tracks `_meta/` by default or fixes the rule. Probed against
    # the current rules: a .gitignore planned by this same run is not on disk yet.
    ctx.swallowed = [rel for rel, _ in ctx.files if check_ignore(repo, rel) == 0]
    return actions, ctx


# ── apply ───────────────────────────────────────────────────────────────────────────────


def execute_plan(repo, ctx):
    """Create planned items only. NEVER overwrites: a path that exists at write time is
    skipped and reported, whatever the reason."""
    created, skipped = [], []
    for rel in ctx.dirs:
        full = os.path.join(repo, rel)
        if os.path.isdir(full):
            skipped.append(rel)
            continue
        os.makedirs(full)
        created.append(rel)
    for rel, payload in ctx.files:
        full = os.path.join(repo, rel)
        if os.path.exists(full):
            skipped.append(rel)
            continue
        parent = os.path.dirname(full)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(payload)
        created.append(rel)
    return created, skipped


# ── manifest init ───────────────────────────────────────────────────────────────────────


def init_manifest(repo):
    path = os.path.join(repo, MANIFEST_RELPATH)
    if os.path.exists(path):
        print(
            f"{MANIFEST_RELPATH} already exists — not overwritten "
            f"(there is no overwrite mode; edit it in place)"
        )
        return EXIT_OK
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(MANIFEST_TEMPLATE)
    print(f"wrote {MANIFEST_RELPATH} — fill the fields, then commit it")
    print("(tracked by default under the standard .gitignore — `_meta/` is tracked; ADR-0006)")
    return EXIT_OK


# ── output ──────────────────────────────────────────────────────────────────────────────


def render(repo, mode, actions, ctx, manifest, created=None, skipped=None):
    lines = [f"Mise-en-place scaffold — {repo} ({mode})"]
    if manifest:
        knobs = []
        if manifest.get("default_branch"):
            knobs.append(f"default_branch={manifest['default_branch']}")
        for k in ("required_folders", "required_files"):
            if manifest.get(k):
                knobs.append(f"{k}={len(manifest[k])}")
        lines.append(
            "Manifest variance applied (_meta/mise-en-place.yml): "
            + (", ".join(knobs) if knobs else "no scaffold-side knobs")
        )
    lines.append("")

    headers = ("ID", "Area", "Action", "Detail")
    table = [headers] + [
        (a["id"], a["area"], a["action"], a["detail"]) for a in actions
    ]
    widths = [max(len(row[i]) for row in table) for i in range(3)]  # Detail unpadded
    for i, row in enumerate(table):
        lines.append(
            " | ".join([row[j].ljust(widths[j]) for j in range(3)] + [row[3]]).rstrip()
        )
        if i == 0:
            lines.append(
                "-+-".join("-" * w for w in widths) + "-+-" + "-" * len("Detail")
            )

    planned = ctx.planned_paths()
    lines.append("")
    if mode == "plan":
        lines.append("Planned creations:")
        for p in planned:
            lines.append(f"  + {p}")
        if not planned:
            lines.append("  (none)")
    else:
        lines.append("Created:")
        for p in created:
            lines.append(f"  + {p}")
        if not created:
            lines.append("  (none)")
        for p in skipped:
            lines.append(f"  skipped (already exists — untouched): {p}")

    if ctx.swallowed:
        verb = "will be created" if mode == "plan" else "created"
        lines += [
            "",
            f"warning: {len(ctx.swallowed)} planned path(s) are ignored by the "
            f"target repo's .gitignore — {verb} on disk, but invisible to "
            f"`git status` and lost on a fresh clone:",
        ]
        for p in ctx.swallowed:
            lines.append(f"  ! {p} — track `_meta/` by default (ADR-0006) or fix the ignore rule")

    if ctx.notes:
        lines += [
            "",
            f"note: {len(ctx.notes)} follow-up(s) the scaffold cannot do for you:",
        ]
        for p in ctx.notes:
            lines.append(f"  ! {p}")

    if ctx.conflicts:
        lines += ["", f"Conflict diffs ({len(ctx.conflicts)} file(s)):"]
        for rel in ctx.conflicts:
            lines += ["", ctx.conflicts[rel].rstrip("\n")]

    n = {
        k: sum(1 for a in actions if a["action"] == k)
        for k in (CREATE, CONFLICT, MANUAL, OK)
    }
    lines += [
        "",
        f"{n[CREATE]} create / {n[CONFLICT]} conflict / {n[MANUAL]} manual / {n[OK]} ok",
    ]
    if mode == "plan":
        lines.append("plan only — nothing written")
    else:
        lines.append(
            f"applied — {len(created)} path(s) created; conflicts and manual items "
            f"left untouched"
        )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fill-only mise-en-place scaffold (plans by default; never overwrites)."
    )
    ap.add_argument(
        "--plan", action="store_true", help="print the plan, write nothing (default)"
    )
    ap.add_argument(
        "--apply",
        dest="apply_mode",
        action="store_true",
        help="create the planned items (additive-only; no overwrite mode exists)",
    )
    ap.add_argument(
        "--init-manifest",
        action="store_true",
        help="write the commented _meta/mise-en-place.yml template when none exists",
    )
    ap.add_argument(
        "--plugin-root",
        default=os.environ.get("CLAUDE_PLUGIN_ROOT", ""),
        help="Plugin root containing the standards' skills/*/references and assets "
        "(default: $CLAUDE_PLUGIN_ROOT)",
    )
    args = ap.parse_args(argv)

    modes = [args.plan, args.apply_mode, args.init_manifest]
    if sum(modes) > 1:
        print(
            "scaffold error: --plan, --apply, and --init-manifest are mutually exclusive",
            file=sys.stderr,
        )
        return EXIT_ERROR

    try:
        repo = git_toplevel(os.getcwd())
        if args.init_manifest:
            return init_manifest(repo)
        if not args.plugin_root:
            raise ScaffoldError(
                "no plugin root: set $CLAUDE_PLUGIN_ROOT or pass --plugin-root "
                "(must contain the standards' skills/repo-meta-structure/ content)"
            )
        # malformed manifest aborts BEFORE any planning; nothing written
        manifest, warnings = load_manifest(repo)
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        actions, ctx = compute_plan(repo, args.plugin_root, manifest)
    except ScaffoldError as e:
        print(f"scaffold error: {e}", file=sys.stderr)
        return EXIT_ERROR

    if not args.apply_mode:  # plan is the default mode
        print(render(repo, "plan", actions, ctx, manifest))
        return EXIT_OK

    if working_tree_dirty(repo):
        print(
            "warning: working tree is dirty — the scaffold is additive-only and will "
            "proceed; review `git status` before committing"
        )
    created, skipped = execute_plan(repo, ctx)
    print(render(repo, "apply", actions, ctx, manifest, created, skipped))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

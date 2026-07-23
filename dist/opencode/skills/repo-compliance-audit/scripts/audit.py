#!/usr/bin/env python3
"""Repo compliance audit — read-only pass/gap table against the packaged standards.

The rollout's measuring instrument. Reads the stable-ID checklist rows from the sibling
standards' reference content (repo-meta-structure + project-memory checklists), executes
each row against the working tree of the invocation root's git toplevel, and prints a
`ID | Area | Verdict | Detail` table plus a `N pass / M gap` summary.

Properties (by construction):
  - READ-ONLY: opens files for reading only; the only subprocesses are read-only git
    queries (`rev-parse`, `check-ignore`). It never writes to the audited repo.
  - Reports, never polices: exit 0 whether or not gaps exist. Non-zero exit (2) is
    reserved for hard errors (not a git repo, broken plugin install, malformed manifest).
  - Defines (almost) zero checklist content: every row is read from a standard's
    checklist file. The single sanctioned exception is HOOK-01 (`no-inline-hooks`),
    sourced directly from the accepted hooks-as-script-plus-config decision until the
    hook-composition standard lands with its own checklist.
  - Manifest awareness: if `_meta/mise-en-place.yml` exists, declared variance is applied
    (`default_branch` recorded; `required_folders` / `required_files` audited as extra
    rows). A missing manifest is not a gap in v1. Unknown manifest keys are ignored —
    the manifest schema is owned by the mise-en-place scaffold skill and carries fields
    (GitHub-side knobs) this audit does not consume.

Checklist row contract (owned by the standards): markdown tables with columns
`ID | Area | Check | Pass condition`; the Check cell is a backtick-wrapped
`<check-type>: <argument>` drawn from a closed vocabulary:
  path-exists · gitignore-tracks · gitignore-ignores · frontmatter-has ·
  flag-if-present · index-links-resolve  (+ no-inline-hooks, script-side, HOOK-01 only)
New check *types* are a change to this script; new check *rows* belong in a standard.

Usage (from the audited repo root):
  python3 audit.py [--plugin-root PATH]

Plugin root resolution: $CLAUDE_PLUGIN_ROOT (set by the harness) or --plugin-root.
The root must contain skills/repo-meta-structure/references/checklist.md and
skills/project-memory/references/checklist.md.

Stdlib-only (no pyyaml): the manifest is parsed with a tailored reader, same stance as
scripts/translate.py in dotfiles-agents.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys

EXIT_OK = 0  # table printed — gaps do NOT change the exit code (report, don't police)
EXIT_ERROR = 2  # hard error: no partial table

CHECKLIST_RELPATHS = (
    os.path.join("skills", "repo-meta-structure", "references", "checklist.md"),
    os.path.join("skills", "project-memory", "references", "checklist.md"),
)

MANIFEST_RELPATH = os.path.join("_meta", "mise-en-place.yml")

# The one script-sourced row (see module docstring). Everything else comes from the
# standards' checklist files.
HOOK_ROW = {
    "id": "HOOK-01",
    "area": "hooks",
    "type": "no-inline-hooks",
    "arg": os.path.join(".claude", "settings.json"),
    "debt": False,
    "source": "hooks-as-script-plus-config decision",
}

# Verdicts
PASS, GAP, NOT_EVALUABLE = "PASS", "GAP", "N/A"

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


class AuditError(Exception):
    """Hard failure — abort with a single clear error, no partial table."""


# ── checklist loading ─────────────────────────────────────────────────────────────────


def load_checklists(plugin_root):
    """Parse the standards' checklist tables into ordered row dicts.

    Errors (AuditError) if a checklist file is missing or yields zero rows — a broken
    install must never silently audit against a partial checklist.
    """
    rows = []
    for rel in CHECKLIST_RELPATHS:
        path = os.path.join(plugin_root, rel)
        if not os.path.isfile(path):
            raise AuditError(
                f"checklist file missing: {path} — broken plugin install; "
                f"refusing to audit against a partial checklist"
            )
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        file_rows = parse_checklist(text)
        if not file_rows:
            raise AuditError(f"checklist file has no parseable rows: {path}")
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


# ── manifest (variance) loading ───────────────────────────────────────────────────────

KNOWN_SCALAR_KEYS = {"default_branch"}
KNOWN_LIST_KEYS = {"required_folders", "required_files"}


def load_manifest(repo):
    """Tailored stdlib reader for `_meta/mise-en-place.yml`.

    Returns {} when absent (a missing manifest is not a gap in v1 — defaults apply).
    Consumes only the audit-side fields: `default_branch` (scalar), `required_folders`
    and `required_files` (lists). Unknown keys — the scaffold/board fields — are skipped
    without error. Malformed *known* fields or unparseable top-level syntax abort.
    """
    path = os.path.join(repo, MANIFEST_RELPATH)
    if not os.path.isfile(path):
        return {}
    manifest = {}
    current_key = None  # known list key currently collecting items
    in_unknown_block = False
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line[0].isspace():  # top-level line
                current_key, in_unknown_block = None, False
                m = re.match(r"^([\w-]+):\s*(.*?)\s*(?:#.*)?$", line)
                if not m:
                    raise AuditError(
                        f"malformed manifest {MANIFEST_RELPATH} line {lineno}: {stripped!r} "
                        f"(expected `key: value` or `key:` + list items)"
                    )
                key, value = m.group(1), m.group(2)
                if key in KNOWN_SCALAR_KEYS:
                    if not value:
                        raise AuditError(
                            f"malformed manifest {MANIFEST_RELPATH} line {lineno}: "
                            f"`{key}` needs a scalar value"
                        )
                    manifest[key] = value.strip("\"'")
                elif key in KNOWN_LIST_KEYS:
                    if value and value != "[]":
                        m_inline = re.match(r"^\[(.*)\]$", value)
                        if not m_inline:
                            raise AuditError(
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
                else:
                    in_unknown_block = True  # scaffold-owned field: tolerate its block
            else:  # indented line
                m_item = re.match(r"^\s+-\s+(.*?)\s*(?:#.*)?$", line)
                if current_key is not None:
                    if not m_item:
                        raise AuditError(
                            f"malformed manifest {MANIFEST_RELPATH} line {lineno}: "
                            f"expected `- item` under `{current_key}`, got {stripped!r}"
                        )
                    manifest[current_key].append(m_item.group(1).strip("\"'"))
                elif in_unknown_block:
                    continue  # nested content of a field this audit does not consume
                else:
                    raise AuditError(
                        f"malformed manifest {MANIFEST_RELPATH} line {lineno}: "
                        f"unexpected indented line {stripped!r}"
                    )
    return manifest


def variance_rows(manifest):
    """Extra rows declared by the repo's manifest (checked, not just excused)."""
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


# ── check execution ───────────────────────────────────────────────────────────────────


def git_toplevel(cwd):
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:  # pragma: no cover — git always present in CI
        raise AuditError(f"git not available: {e}") from e
    if r.returncode != 0:
        raise AuditError(f"not a git repository: {cwd} (audit runs from a repo root)")
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
        raise AuditError(f"git check-ignore failed for {probe!r}: {r.stderr.strip()}")
    return r.returncode


def check_path_exists(repo, arg):
    full = os.path.join(repo, arg)
    want_dir = arg.endswith("/")
    if want_dir:
        ok = os.path.isdir(full)
        return (PASS, arg) if ok else (GAP, f"missing directory: {arg}")
    ok = os.path.isfile(full)
    return (PASS, arg) if ok else (GAP, f"missing file: {arg}")


def check_flag_if_present(repo, arg, debt):
    present = os.path.exists(os.path.join(repo, arg))
    if not present:
        return PASS, f"absent: {arg}"
    if debt:
        return (
            GAP,
            f"migration debt: {arg} present — fold into the standard replacement",
        )
    return GAP, f"present at root: {arg} — content belongs in _meta/"


def check_gitignore(repo, arg, want_ignored):
    code = check_ignore(repo, arg)
    ignored = code == 0
    if want_ignored:
        return (
            (PASS, f"ignored: {arg}") if ignored else (GAP, f"probe not ignored: {arg}")
        )
    return (
        (PASS, f"tracked (not ignored): {arg}")
        if not ignored
        else (GAP, f"probe is ignored: {arg} — expected tracked but an ignore rule matches")
    )


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


def check_frontmatter_has(repo, field):
    docs = plans_scope(repo)
    if not docs:
        return PASS, "no in-scope planning docs"
    missing = [
        os.path.relpath(doc, repo) for doc in docs if field not in frontmatter_keys(doc)
    ]
    if not missing:
        return PASS, f"`{field}` present in all {len(docs)} in-scope docs"
    return GAP, "; ".join(f"{doc}: missing `{field}`" for doc in missing)


def check_index_links_resolve(repo, arg):
    index = os.path.join(repo, arg)
    if not os.path.isfile(index):
        return (
            NOT_EVALUABLE,
            f"index absent ({arg}) — the gap is the index-presence row's",
        )
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
    if not dangling:
        return PASS, f"all relative links in {arg} resolve"
    return GAP, "; ".join(dangling)


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
    """True when the command is a plain invocation of a script by path.

    Raw inline shell (pipelines, chains, substitutions, bare builtins) is what HOOK-01
    flags; a command that just runs a hook-directory script — optionally through an
    interpreter, optionally behind env-var path prefixes — passes. Packaging depth
    (config.json + directory shape) waits for the hook-composition standard.
    """
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


def check_no_inline_hooks(repo, arg):
    path = os.path.join(repo, arg)
    if not os.path.isfile(path):
        return PASS, f"no {arg} — no hooks defined inline"
    try:
        with open(path, encoding="utf-8") as fh:
            settings = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        return GAP, f"cannot parse {arg}: {e}"
    cmds = hook_commands(settings)
    if not cmds:
        return PASS, f"no hooks defined in {arg}"
    inline = [c for c in cmds if not is_script_invocation(c)]
    if not inline:
        return PASS, f"{len(cmds)} hook command(s), all plain script invocations"
    shown = "; ".join(
        f"inline hook command: {c if len(c) <= 60 else c[:57] + '...'}" for c in inline
    )
    return GAP, f"{shown} — hooks belong in script + config directories, not inline"


DISPATCH = {
    "path-exists": lambda repo, row: check_path_exists(repo, row["arg"]),
    "gitignore-tracks": lambda repo, row: check_gitignore(repo, row["arg"], False),
    "gitignore-ignores": lambda repo, row: check_gitignore(repo, row["arg"], True),
    "frontmatter-has": lambda repo, row: check_frontmatter_has(repo, row["arg"]),
    "flag-if-present": lambda repo, row: check_flag_if_present(
        repo, row["arg"], row["debt"]
    ),
    "index-links-resolve": lambda repo, row: check_index_links_resolve(
        repo, row["arg"]
    ),
    "no-inline-hooks": lambda repo, row: check_no_inline_hooks(repo, row["arg"]),
}


def run_audit(repo, rows):
    results = []
    for row in rows:
        runner = DISPATCH.get(row["type"])
        if runner is None:
            raise AuditError(
                f"unknown check type `{row['type']}` in row {row['id']} — "
                f"the closed vocabulary is: {', '.join(sorted(DISPATCH))}. "
                f"New check types are an audit-script change."
            )
        verdict, detail = runner(repo, row)
        results.append({**row, "verdict": verdict, "detail": detail})
    return results


# ── output ────────────────────────────────────────────────────────────────────────────


def render_table(repo, results, manifest):
    lines = [f"Compliance audit — {repo}"]
    if manifest:
        knobs = []
        if manifest.get("default_branch"):
            knobs.append(f"default_branch={manifest['default_branch']}")
        for k in ("required_folders", "required_files"):
            if manifest.get(k):
                knobs.append(f"{k}={len(manifest[k])}")
        lines.append(
            "Manifest variance applied (_meta/mise-en-place.yml): "
            + (", ".join(knobs) if knobs else "no audit-side knobs")
        )
    lines.append("")
    headers = ("ID", "Area", "Verdict", "Detail")
    table = [headers] + [
        (r["id"], r["area"], r["verdict"], r["detail"]) for r in results
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
    n_pass = sum(1 for r in results if r["verdict"] == PASS)
    n_gap = sum(1 for r in results if r["verdict"] == GAP)
    n_na = sum(1 for r in results if r["verdict"] == NOT_EVALUABLE)
    summary = f"{n_pass} pass / {n_gap} gap"
    if n_na:
        summary += f" ({n_na} not evaluable)"
    lines += ["", summary]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Read-only repo compliance audit (reports, never polices)."
    )
    ap.add_argument(
        "--plugin-root",
        default=os.environ.get("CLAUDE_PLUGIN_ROOT", ""),
        help="Plugin root containing skills/<standard>/references/checklist.md "
        "(default: $CLAUDE_PLUGIN_ROOT)",
    )
    args = ap.parse_args(argv)

    try:
        if not args.plugin_root:
            raise AuditError(
                "no plugin root: set $CLAUDE_PLUGIN_ROOT or pass --plugin-root "
                "(must contain the standards' skills/*/references/checklist.md)"
            )
        repo = git_toplevel(os.getcwd())
        rows = load_checklists(args.plugin_root)
        rows.append(dict(HOOK_ROW))
        manifest = load_manifest(repo)
        rows.extend(variance_rows(manifest))
        results = run_audit(repo, rows)
    except AuditError as e:
        print(f"audit error: {e}", file=sys.stderr)
        return EXIT_ERROR

    print(render_table(repo, results, manifest))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

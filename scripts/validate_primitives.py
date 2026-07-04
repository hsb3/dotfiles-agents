#!/usr/bin/env python3
"""Primitive CONTENT validation (issue #22, deliverable B).

The drift guards prove consistency (roster matches disk, committed targets match a rebuild) but
never look INSIDE a primitive. This guard does: it validates that each source primitive is
well-formed before the build ever renders it, plus the roster cross-checks check_roster.py omits.

What it checks:
  - skill : SKILL.md at the source root with frontmatter `name` + `description`
  - agent : the .md has frontmatter with `name` + `description`
  - mcp   : the spec JSON has `name` and `transport` in {stdio, http}; stdio => `command`,
            http => `url`; any secret-named env/header value is a ${VAR} placeholder, not a literal
  - roster: `origin` in {authored, sourced}, `targets` subset of the real targets, `summary` set
  - externals mcp specs (externals.yaml kind: mcp) get the same mcp-spec checks
  - portability (issue #79, mirrors the workbench gate): no machine-tied content (hard-banned
    paths; ~/dotfiles / /Applications/ / machine-local tools only with a covering `requires:`
    declaration); rostered stdio mcp specs carry `install` provenance; hook configs are
    handler references only, inline prose capped at 20 words

Stdlib-only (reuses translate.py's parsers), so `make ci` stays zero-install. Exit 0 = clean;
exit 1 = problems (prints every one). `--json` emits the findings as JSON.

Usage: python3 scripts/validate_primitives.py [--json]   (run from the repo root)
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translate as T  # reuse the roster/externals parsers + REPO root

VALID_TARGETS = {"claude-code", "opencode", "claude-agents"}
VALID_ORIGIN = {"authored", "sourced"}
VALID_TRANSPORT = {"stdio", "http"}
SECRET_HINT = re.compile(r"(token|secret|key|password|passwd|pat|credential)", re.I)
PLACEHOLDER = re.compile(r"^\$\{[^}]+\}$")
# XML/angle-bracket tag in a SKILL.md description — Claude Cowork refuses to load such skills
# ("SKILL.md description cannot contain XML tags"). Skill-specific: agent descriptions may use
# `<example>` blocks, so this is checked only for skills. Requires a letter (or `/`) right
# after `<` so bare comparisons like `< 5` aren't matched; `[^>\n]*` keeps a tag on one line.
XML_TAG = re.compile(r"</?[A-Za-z][^>\n]*>")

# ── Portability checks (issue #79; mirror of the workbench gate H5-broadened/H6, wb#32) ──
TEXT_EXT = (".md", ".json", ".sh", ".py", ".js", ".ts", ".yaml", ".yml", ".toml")
# Hard bans — always a defect, no declaration excuses them.
HARD_MACHINE = (
    (re.compile(r"/Users/[A-Za-z]"), "machine-absolute path /Users/..."),
    (re.compile(r"hsb-2026"), "personal vault name hsb-2026"),
    (
        re.compile(r"--break-system-packages"),
        "non-portable pip flag --break-system-packages",
    ),
    (
        re.compile(r"(?:~|\$HOME)/(?:Documents|Desktop)/"),
        "personal home-layout path (~/Documents, ~/Desktop)",
    ),
)
# Declared-or-flagged — legal only with a covering `requires:` entry on the roster row.
DOTFILES_PATH = re.compile(r"(?:~|\$HOME)/(?:dotfiles|Developer)\b")
APP_PATH = re.compile(r"/Applications/")
# Machine-local tools (custom ~/.local/bin scripts + custom MCP binaries). Distinctive names
# only — ambiguous words (secret, skills, speak) are omitted; precision over recall.
LOCAL_TOOLS = (
    "agy",
    "capture-console-errors",
    "cc-hooks",
    "cc-project-memory",
    "check-tool-updates",
    "da-prune-sessions",
    "dcode",
    "fetch-docs",
    "fufo-excalidraw-wire",
    "mcp-audio",
    "mcp-deck-builder",
    "mcp-secrets-sync",
    "migrate-claude-memory",
    "models-dev",
    "project-activity",
    "speak_gemini",
)
LOCAL_TOOL_RX = {
    t: re.compile(rf"(?<![\w./-]){re.escape(t)}(?![\w-])") for t in LOCAL_TOOLS
}
HOOK_PROSE_MAX_WORDS = 20


def frontmatter_block(text):
    """Return the raw frontmatter body of a `---` block, or None."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else None


def frontmatter_keys(text):
    """Return the set of top-level frontmatter keys in a `---` block (best-effort, stdlib)."""
    fm = frontmatter_block(text)
    if fm is None:
        return set()
    return {km.group(1) for ln in fm.split("\n") if (km := re.match(r"^([\w-]+):", ln))}


def frontmatter_field(text, key):
    """Full value of a top-level frontmatter field, incl. indented folded/continued lines."""
    fm = frontmatter_block(text)
    if fm is None:
        return ""
    m = re.search(rf"^{re.escape(key)}:(.*?)(?=^\S|\Z)", fm, re.S | re.M)
    return m.group(1) if m else ""


def check_secret_values(mapping, label, problems):
    """Any secret-named env/header value must be a ${VAR} placeholder, never a literal."""
    for k, v in (mapping or {}).items():
        if (
            SECRET_HINT.search(k)
            and isinstance(v, str)
            and v
            and not PLACEHOLDER.match(v)
        ):
            problems.append(
                f"[{label}] secret-looking value for {k!r} is a literal, not a ${{VAR}} placeholder"
            )


def validate_mcp_spec(spec_path, label, problems, require_install=True):
    full = os.path.join(T.REPO, spec_path)
    if not os.path.isfile(full):
        problems.append(f"[{label}] mcp spec not found: {spec_path}")
        return
    try:
        with open(full, encoding="utf-8") as fh:
            spec = json.load(fh)
    except (json.JSONDecodeError, OSError) as e:
        problems.append(f"[{label}] mcp spec is not valid JSON: {e}")
        return
    if not spec.get("name"):
        problems.append(f"[{label}] mcp spec missing `name`")
    transport = spec.get("transport")
    if transport not in VALID_TRANSPORT:
        problems.append(
            f"[{label}] mcp spec `transport` must be one of {sorted(VALID_TRANSPORT)}, got {transport!r}"
        )
    if transport == "stdio" and not spec.get("command"):
        problems.append(f"[{label}] stdio mcp spec missing `command`")
    # A bare PATH command assumes the binary exists; rostered stdio specs must say where it
    # comes from (issue #79). Externals are exempt — their provenance lives in externals.yaml.
    if transport == "stdio" and require_install:
        inst = spec.get("install")
        if (
            not isinstance(inst, dict)
            or not inst.get("upstream")
            or not inst.get("command")
        ):
            problems.append(
                f"[{label}] stdio mcp spec missing `install` provenance "
                f"({{upstream, command}} — where the binary comes from and how to install it)"
            )
    if transport == "http" and not spec.get("url"):
        problems.append(f"[{label}] http mcp spec missing `url`")
    check_secret_values(spec.get("env"), label, problems)
    check_secret_values(spec.get("headers"), label, problems)


def _iter_source_files(full):
    """Yield the text files of a primitive's source (a file, or a walked directory)."""
    if os.path.isfile(full):
        if full.endswith(TEXT_EXT):
            yield full
        return
    for root, _dirs, files in os.walk(full):
        for f in sorted(files):
            if f.endswith(TEXT_EXT):
                yield os.path.join(root, f)


def check_portability(e, problems):
    """Machine-tied content is banned outright or must be declared in `requires:` (issue #79)."""
    eid, src = e.get("id", "<no-id>"), e.get("source", "")
    reqs = set(T._list(e.get("requires", "")))
    has_cli = any(r.startswith("cli:") for r in reqs)
    for fp in _iter_source_files(os.path.join(T.REPO, src)):
        rel = os.path.relpath(fp, T.REPO)
        try:
            with open(fp, encoding="utf-8", errors="ignore") as fh:
                body = fh.read()
        except OSError:
            continue
        for rx, why in HARD_MACHINE:
            if rx.search(body):
                problems.append(f"[{eid}] {why} in {rel}")
        if DOTFILES_PATH.search(body) and "env:dotfiles" not in reqs:
            problems.append(
                f"[{eid}] ~/dotfiles or ~/Developer path in {rel} without "
                f"`requires: [env:dotfiles]` on the roster entry"
            )
        if APP_PATH.search(body) and not has_cli:
            problems.append(
                f"[{eid}] /Applications/ path in {rel} but the roster entry declares "
                f"no `cli:` dependency for the app"
            )
        for tool, rx in LOCAL_TOOL_RX.items():
            if (
                rx.search(body)
                and f"cli:{tool}" not in reqs
                and "env:dotfiles" not in reqs
            ):
                problems.append(
                    f"[{eid}] references machine-local tool `{tool}` in {rel} — declare "
                    f"`requires: [cli:{tool}]` (or env:dotfiles) on the roster entry"
                )


def _walk_hook_config(node, label, problems):
    if isinstance(node, dict):
        if node.get("type") == "command":
            cmd = node.get("command", "")
            if "hooks-handlers/" not in cmd:
                problems.append(
                    f"[{label}] inline command is not a hooks-handlers/ reference: {cmd[:70]!r}"
                )
        if node.get("type") == "prompt":
            words = len(node.get("prompt", "").split())
            if words > HOOK_PROSE_MAX_WORDS:
                problems.append(
                    f"[{label}] inline prompt is {words} words (max {HOOK_PROSE_MAX_WORDS} — "
                    f"move the prose to a file beside the handlers)"
                )
        for v in node.values():
            _walk_hook_config(v, label, problems)
    elif isinstance(node, list):
        for v in node:
            _walk_hook_config(v, label, problems)


def check_hook_configs(problems):
    """Hook configs are config + handler references only — no inline scripts or prose (issue #79)."""
    hooks_root = os.path.join(T.REPO, "primitives-core", "hooks")
    if not os.path.isdir(hooks_root):
        return
    for plugin in sorted(os.listdir(hooks_root)):
        cfg = os.path.join(hooks_root, plugin, "hooks", "hooks.json")
        if not os.path.isfile(cfg):
            continue
        try:
            with open(cfg, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as e:
            problems.append(f"[hooks:{plugin}] hooks.json unreadable: {e}")
            continue
        _walk_hook_config(data, f"hooks:{plugin}", problems)


def validate_entry(e, problems):
    eid, t, src = e.get("id", "<no-id>"), e.get("type"), e.get("source", "")
    # roster cross-checks check_roster.py does not do
    if e.get("origin") not in VALID_ORIGIN:
        problems.append(
            f"[{eid}] `origin` must be one of {sorted(VALID_ORIGIN)}, got {e.get('origin')!r}"
        )
    bad_targets = set(e.get("targets", [])) - VALID_TARGETS
    if bad_targets:
        problems.append(f"[{eid}] unknown target(s): {sorted(bad_targets)}")
    if not e.get("summary", "").strip():
        problems.append(f"[{eid}] empty `summary`")
    # per-type content checks
    full = os.path.join(T.REPO, src)
    if t == "skill":
        skill_md = os.path.join(full, "SKILL.md")
        if not os.path.isfile(skill_md):
            problems.append(f"[{eid}] skill missing SKILL.md at root")
        else:
            with open(skill_md, encoding="utf-8") as fh:
                text = fh.read()
            keys = frontmatter_keys(text)
            for need in ("name", "description"):
                if need not in keys:
                    problems.append(f"[{eid}] SKILL.md frontmatter missing `{need}`")
            tags = XML_TAG.findall(frontmatter_field(text, "description"))
            if tags:
                found = ", ".join(sorted(set(tags)))
                problems.append(
                    f"[{eid}] SKILL.md description contains XML tag(s) {found} — "
                    f"Claude Cowork refuses to load skills whose description has "
                    f"angle-bracket tags (use a bracket-free placeholder)"
                )
    elif t == "agent":
        if os.path.isfile(full):
            with open(full, encoding="utf-8") as fh:
                keys = frontmatter_keys(fh.read())
            for need in ("name", "description"):
                if need not in keys:
                    problems.append(f"[{eid}] agent frontmatter missing `{need}`")
    elif t == "mcp":
        validate_mcp_spec(src, eid, problems)


def main():
    as_json = "--json" in sys.argv
    problems = []
    roster = T.parse_roster(T.ROSTER)
    for e in roster:
        validate_entry(e, problems)
        check_portability(e, problems)
    check_hook_configs(problems)
    # externals kind: mcp specs (install provenance lives in externals.yaml, not the spec)
    for ext in T.parse_externals(T.EXTERNALS):
        if ext.get("kind") == "mcp":
            validate_mcp_spec(
                ext.get("spec", ""),
                f"external:{ext.get('id')}",
                problems,
                require_install=False,
            )

    if as_json:
        print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
        return 1 if problems else 0
    if problems:
        print(f"✗ primitive validation: {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1
    n_mcp = sum(1 for e in roster if e.get("type") == "mcp")
    print(
        f"✓ primitives valid — {len(roster)} entries content-checked ({n_mcp} mcp specs + externals)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

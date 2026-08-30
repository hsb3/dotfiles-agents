#!/usr/bin/env python3
"""gen_opencode.py — build the opencode laydown from primitives-core at INSTALL TIME (ADR 0017).

opencode has no marketplace: distribution is a LAYDOWN (directories it discovers on disk)
plus a mergeable config fragment. This generator turns the roster's `targets: [.., opencode]`
membership and the translation.yaml capability matrix into a laydown tree — built into a
consumer-chosen directory when installing, NEVER tracked (the dist/opencode lane retired
with task-3). Consumers run `scripts/install_opencode.sh` from a clone, which builds to a
tempdir and executes the generated installer; `--out` is the direct entry point:

  skills/<id>/            native — copied verbatim from primitives-core/skills/<id>/
                          (validated: opencode name regex ^[a-z0-9]+(-[a-z0-9]+)*$, <=64;
                          description <= 1024 — a violation FAILS the build, never skips)
  agents/<id>.md          transform — frontmatter remapped per the cc-to-opencode mapping:
                          `name` dropped (filename carries it), `mode: subagent` added,
                          bare model aliases pinned to provider-prefixed refs
                          (translation.yaml model_aliases), the CC `tools:` allowlist
                          inverted into opencode's permission map (read/write/bash),
                          CC-only keys (effort, color) dropped, maxTurns -> steps; body verbatim
  opencode.jsonc          the mergeable config fragment (schema ref; mcp entries would
                          render here — none rostered yet)
  install.sh              the laydown installer: --global or --project <dir>
  README.md               generated lane README incl. the EXCLUSIONS manifest — every
                          primitive that does NOT travel, with its reason (no silent caps)

Atelier is NOT in this lane: its opencode port ships from its own repo, hand-authored against
opencode's real agent model under the parity contract (docs/atelier-parity.md), so every
atelier member is rostered `targets: [claude-code]` and this generator no longer emits it.

Hooks and commands are `unsupported` in the matrix (opencode's only event surface is TS-on-Bun
plugins; opencode does have commands, but the drive-a-skill body needs a per-command authoring
pass — full reasons in translation.yaml). They appear in the exclusions manifest, never in the
tree, so the laydown stays skills + agents.

Deterministic and stdlib-only:

  python3 scripts/gen_opencode.py --out DIR   build the laydown into DIR (absent or empty)
"""

import argparse
import filecmp
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from check_roster import parse_roster  # noqa: E402

ROSTER = os.path.join(REPO, "primitives-core.yaml")
TRANSLATION = os.path.join(REPO, "translation.yaml")

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_SKILL_NAME = 64
MAX_DESCRIPTION = 1024

# CC tool names -> opencode permission buckets (allow when granted, deny otherwise).
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
BASH_TOOLS = {"Bash"}


def parse_translation(path):
    """Tailored line parser for translation.yaml's controlled format (three entry lists)."""
    section, entry = None, None
    out = {"matrix": [], "model_aliases": [], "exclusions": []}
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = re.match(r"^(matrix|model_aliases|exclusions):\s*$", line)
            if m:
                section = m.group(1)
                entry = None
                continue
            m = re.match(r"^  - ([a-z_]+):\s*(.*)$", line)
            if m and section:
                entry = {m.group(1): m.group(2).strip().strip('"')}
                out[section].append(entry)
                continue
            m = re.match(r"^    ([a-z_]+):\s*(.*)$", line)
            if m and entry is not None:
                entry[m.group(1)] = m.group(2).strip().strip('"')
    return out


def treatment_for(translation, ptype):
    for row in translation["matrix"]:
        if row.get("type") == ptype and row.get("target") == "opencode":
            return row.get("treatment"), row.get("reason", "")
    return "unsupported", "no matrix row for this type"


def opencode_members(entries):
    return [e for e in entries if "opencode" in _targets(e)]


def _targets(entry):
    v = entry.get("targets", "")
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip() for x in v[1:-1].split(",") if x.strip()]
    return [v] if v else []


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("agent file has no frontmatter block")
    fm = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if km:
            fm[km.group(1)] = km.group(2).strip()
    return fm, m.group(2)


def transform_agent(text, aliases):
    """CC agent .md -> opencode agent .md per the mapping table."""
    fm, body = split_frontmatter(text)
    out = ["---"]
    out.append(f"description: {fm.get('description', '')}")
    out.append("mode: subagent")
    model = fm.get("model", "")
    if model:
        ref = aliases.get(model, model if "/" in model else "")
        if ref:
            out.append(f"model: {ref}")
    if fm.get("maxTurns"):
        out.append(f"steps: {fm['maxTurns']}")
    # CC `color:` is dropped: opencode expects hex/theme-token colors and rejects CC's
    # named values at config load (verified live on opencode 1.18.11)
    tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
    out.append("permission:")
    out.append("  read: allow")
    out.append(f"  write: {'allow' if tools & WRITE_TOOLS else 'deny'}")
    out.append(f"  bash: {'allow' if tools & BASH_TOOLS else 'deny'}")
    out.append("---")
    return "\n".join(out) + "\n" + body


def skill_problems(sid, src):
    problems = []
    if not SKILL_NAME_RE.match(sid) or len(sid) > MAX_SKILL_NAME:
        problems.append(f"skill {sid}: name fails opencode regex/length — invisible to opencode")
    with open(os.path.join(src, "SKILL.md"), encoding="utf-8") as fh:
        body = fh.read()
    m = re.search(r"^description:\s*(.*?)(?=^\S)", body, re.M | re.S)
    desc = " ".join((m.group(1) if m else "").split()).lstrip(">").strip()
    if not desc:
        problems.append(f"skill {sid}: missing description frontmatter")
    elif len(desc) > MAX_DESCRIPTION:
        problems.append(f"skill {sid}: description {len(desc)} > {MAX_DESCRIPTION} chars")
    return problems


INSTALL_SH = """#!/usr/bin/env sh
# Lay down the opencode lane: skills + agents into an opencode config root.
# Generated by scripts/gen_opencode.py — do not hand-edit.
# usage: ./install.sh --global | --project <dir>
set -eu
case "${1:-}" in
  --global) ROOT="${XDG_CONFIG_HOME:-$HOME/.config}/opencode" ;;
  --project) ROOT="${2:?usage: install.sh --project <dir>}/.opencode" ;;
  *) echo "usage: install.sh --global | --project <dir>" >&2; exit 2 ;;
esac
HERE="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
mkdir -p "$ROOT/skills" "$ROOT/agents"
for d in "$HERE"/skills/*/; do
  n="$(basename "$d")"
  rm -rf "$ROOT/skills/$n"
  cp -R "$d" "$ROOT/skills/$n"
done
for f in "$HERE"/agents/*.md; do
  cp "$f" "$ROOT/agents/$(basename "$f")"
done
echo "opencode laydown complete -> $ROOT (skills/ + agents/). Restart opencode to discover."
"""

FRAGMENT = """// opencode.jsonc — mergeable config fragment for this lane.
// Generated by scripts/gen_opencode.py — do not hand-edit.
// Merge into ./opencode.jsonc, .opencode/opencode.jsonc, or the global config
// (~/.config/opencode/opencode.jsonc). Arrays concatenate, objects deep-merge.
// mcp entries from the roster render here. None reach this lane today — the rostered
// one targets claude-code only, so the manifest records it as an exclusion.
{
  "$schema": "https://opencode.ai/config.json"
}
"""


def build(out_root, entries, translation):
    problems = []
    aliases = {r["alias"]: r["ref"] for r in translation["model_aliases"] if "alias" in r}
    excluded_ids = {r["id"]: r.get("reason", "") for r in translation["exclusions"] if "id" in r}
    members = opencode_members(entries)

    shipped = {"skill": [], "agent": []}
    excluded = []  # (id, type, reason)
    for e in entries:
        eid, ptype = e["id"], e["type"]
        # Every roster type reaches treatment_for(); a type absent here is a SILENT skip,
        # not a recorded exclusion. Commands land on translation.yaml's `type: command`
        # matrix row (treatment: unsupported), which carries the reason the manifest prints.
        if ptype not in ("skill", "agent", "command", "hook", "mcp"):
            continue
        if eid in excluded_ids:
            if "opencode" in _targets(e):
                problems.append(
                    f"{eid}: listed in translation.yaml exclusions but roster targets opencode — "
                    "resolve the disagreement")
            excluded.append((eid, ptype, excluded_ids[eid]))
            continue
        treatment, reason = treatment_for(translation, ptype)
        if treatment == "unsupported":
            excluded.append((eid, ptype, reason))
            continue
        if e not in members:
            excluded.append((eid, ptype, "roster targets do not include opencode"))
            continue
        src = os.path.join(REPO, e["source"])
        if ptype == "skill":
            problems.extend(skill_problems(eid, src))
            shutil.copytree(src, os.path.join(out_root, "skills", eid), ignore=IGNORE)
            shipped["skill"].append(eid)
        elif ptype == "agent":
            with open(src, encoding="utf-8") as fh:
                text = fh.read()
            os.makedirs(os.path.join(out_root, "agents"), exist_ok=True)
            with open(os.path.join(out_root, "agents", f"{eid}.md"), "w", encoding="utf-8") as fh:
                fh.write(transform_agent(text, aliases))
            shipped["agent"].append(eid)

    with open(os.path.join(out_root, "install.sh"), "w", encoding="utf-8") as fh:
        fh.write(INSTALL_SH)
    os.chmod(os.path.join(out_root, "install.sh"), 0o755)
    with open(os.path.join(out_root, "opencode.jsonc"), "w", encoding="utf-8") as fh:
        fh.write(FRAGMENT)

    lines = [
        "# opencode lane",
        "",
        "_Generated at install time by `scripts/gen_opencode.py` from `primitives-core/` +",
        "`translation.yaml` (ADR 0017; never tracked). opencode has no marketplace — install",
        "by laydown:_",
        "",
        "```sh",
        "./install.sh --global            # ~/.config/opencode/{skills,agents}/",
        "./install.sh --project <dir>     # <dir>/.opencode/{skills,agents}/",
        "```",
        "",
        f"Ships {len(shipped['skill'])} skills (verbatim; opencode also reads `.claude/skills/`"
        " natively — this lane is the explicit, deterministic copy) and"
        f" {len(shipped['agent'])} agents (frontmatter remapped: `mode: subagent`,"
        " provider-prefixed models, CC tool allowlists inverted to permission maps).",
        "",
        "## Not in this lane (and why)",
        "",
        "| Primitive | Type | Reason |",
        "|---|---|---|",
    ]
    for eid, ptype, reason in sorted(excluded):
        lines.append(f"| `{eid}` | {ptype} | {reason} |")
    lines += [
        "",
        "Agent-tool caveat: CC-only orchestration tools (Agent, SendMessage) have no opencode",
        "equivalent; remapped agents keep their briefs but cannot spawn sub-agents there.",
        "",
    ]
    with open(os.path.join(out_root, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return problems


def _identical(a, b):
    if os.path.isdir(a) and os.path.isdir(b):
        cmp = filecmp.dircmp(a, b)
        if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
            return False
        return all(_identical(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs)
    if not (os.path.isfile(a) and os.path.isfile(b)):
        return False
    return filecmp.cmp(a, b, shallow=False)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out", required=True, metavar="DIR",
        help="build the laydown into DIR (must be absent or empty — never clobbers)",
    )
    args = ap.parse_args(argv)
    out = os.path.abspath(args.out)
    if os.path.isdir(out) and os.listdir(out):
        print(f"✗ opencode laydown — refusing to build into non-empty dir: {out}")
        return 1
    entries = parse_roster(ROSTER)
    translation = parse_translation(TRANSLATION)
    os.makedirs(out, exist_ok=True)
    problems = build(out, entries, translation)
    if problems:
        print(f"✗ opencode laydown — {len(problems)} problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    n_skills = len(os.listdir(os.path.join(out, "skills"))) if os.path.isdir(
        os.path.join(out, "skills")) else 0
    print(f"✓ opencode laydown built — {out} ({n_skills} skills + agents + installer)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

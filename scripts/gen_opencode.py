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
  agents/<id>.md          transform — frontmatter remapped from translation.yaml's declared
                          matrix, never hardcoded sets (decision-009): `field_treatments`
                          says what each key does (map / drop-with-notice / unsupported),
                          `tool_capabilities` inverts the CC `tools:` allowlist into
                          opencode's read/write/bash permission map, and a bare CC `model:`
                          alias resolves through the SHARED tier map
                          (primitives-core/hooks/_lib/model_catalog.json): keyword -> tier
                          -> the active provider's id. An undeclared field, tool or alias
                          FAILS the build; anything the matrix says does not travel prints
                          a notice. Body verbatim
  opencode.jsonc          the mergeable config fragment (schema ref plus the `mcp` block
                          every roster mcp entry targeting opencode renders into; both
                          rostered entries are claude-code-only, so today it is the ref
                          alone and each lands in the exclusions manifest instead)
  install.sh              the laydown installer: --global or --project <dir>; it copies the
                          README below into $ROOT as dotfiles-agents-laydown.md, since the
                          lane's tempdir dies with the wrapper
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
import json
import os
import re
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "primitives-core", "hooks", "_lib"))

import model_tiers  # noqa: E402

from check_roster import (  # noqa: E402
    parse_roster,
    parse_translation,
    split_frontmatter,
    tool_row,
)

ROSTER = os.path.join(REPO, "primitives-core.yaml")
TRANSLATION = os.path.join(REPO, "translation.yaml")

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_SKILL_NAME = 64
MAX_DESCRIPTION = 1024

#: opencode expands `{env:VAR}`, never CC's `${VAR}` (opencode-expertise,
#: references/extension-surfaces.md) — an unconverted ref ships as a literal string.
ENV_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


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


def _model_row(translation, alias):
    return next((r for r in translation["model_aliases"] if r.get("alias") == alias), None)


def _catalog():
    """The shared tier map, loaded once. A broken catalog is a build failure, not a default."""
    global _CATALOG
    if _CATALOG is None:
        _CATALOG = model_tiers.load()
    return _CATALOG


_CATALOG = None


def _tier_for_keyword(catalog, keyword):
    return next(
        (t for t in model_tiers.tiers(catalog)
         if model_tiers.claude_code_keyword(catalog, t) == keyword),
        None,
    )


def _resolve_model(translation, agent_id, model, catalog=None):
    """A CC `model:` value -> the ref opencode needs. Returns (ref-or-None, problems, notices).

    A bare CC alias is this harness's rendering of a dispatch tier, so it resolves through
    the SHARED map (model_catalog.json), not through a per-target pin: keyword -> tier ->
    active provider's model id. That is what keeps a provider switch to one edit.
    """
    if "/" in model:
        return model, [], []
    row = _model_row(translation, model)
    if row is None:
        return None, [f"{agent_id}: model alias `{model}` has no translation.yaml "
                      "model_aliases row — pin it or declare it unsupported"], []
    if row.get("opencode") == "unsupported":
        return None, [], [f"{agent_id}: model `{model}` does not travel, so the agent runs on "
                          f"opencode's default — {row.get('reason', 'no reason declared')}"]
    if row.get("ref"):
        return None, [f"{agent_id}: model_aliases row for `{model}` pins `ref: {row['ref']}` "
                      "— a second tier-to-id map; the alias resolves through "
                      "primitives-core/hooks/_lib/model_catalog.json"], []
    if row.get("resolves") != "tier":
        return None, [f"{agent_id}: model_aliases row for `{model}` declares neither "
                      "`resolves: tier` nor `opencode: unsupported`"], []
    catalog = catalog or _catalog()
    tier = _tier_for_keyword(catalog, model)
    if tier is None:
        return None, [f"{agent_id}: model alias `{model}` renders no tier in the shared map "
                      "— no tier declares it as its `claude_code_keyword`"], []
    concrete = model_tiers.model_for(catalog, tier)
    if concrete is None:
        provider = model_tiers.active_provider(catalog)
        return None, [f"{agent_id}: tier `{tier}` has no model for the active provider "
                      f"`{provider}` in the shared map"], []
    return f"{model_tiers.active_provider(catalog)}/{concrete}", [], []


#: opencode keys whose position in the emitted block is pinned (byte-stability for the agents
#: already laid down); every other declared `map` target appends after them, in field order.
PINNED_KEYS = ("model", "steps")


def transform_agent(text, translation, agent_id, catalog=None):
    """CC agent .md -> opencode agent .md, driven entirely by translation.yaml's matrix.

    Returns (text, problems, notices): anything the matrix does not name is a PROBLEM, and
    anything it declares does not travel is a printed NOTICE — never a silent drop
    (decision-009). Emission is driven FROM the `field_treatments` rows, so a declared `map`
    row the emitter has no special case for still travels. Notice order follows the
    frontmatter, so builds stay diff-identical.
    """
    fm, body = split_frontmatter(text)
    problems, notices = [], []
    rows = {r["field"]: r for r in translation["field_treatments"] if "field" in r}
    values, tools = {}, ""

    for key, raw in fm.items():
        row = rows.get(key)
        if row is None:
            problems.append(
                f"{agent_id}: frontmatter key `{key}` has no translation.yaml "
                "field_treatments row — declare a treatment for it")
            continue
        treatment, why = row.get("treatment"), row.get("reason", "no reason declared")
        if treatment == "unsupported":
            problems.append(
                f"{agent_id}: frontmatter key `{key}` is `treatment: unsupported` for "
                f"opencode — {why}")
            continue
        if treatment == "drop-with-notice":
            notices.append(f"{agent_id}: dropped `{key}` — {why}")
            continue
        if treatment != "map":
            problems.append(
                f"{agent_id}: frontmatter key `{key}` has unknown treatment {treatment!r}")
            continue
        to = row.get("opencode", "")
        if not to:
            problems.append(
                f"{agent_id}: field_treatments row `{key}` is `treatment: map` with no "
                "`opencode:` target key — nothing says where it lands")
            continue
        if to == "filename":
            continue  # identity travels as agents/<id>.md, never as a key
        if not raw:
            problems.append(
                f"{agent_id}: frontmatter key `{key}` is empty, so opencode's `{to}` would "
                "be written blank — give it a value or drop the key")
            continue
        if to == "permission":
            tools = raw
        elif key == "model":
            ref, mp, mn = _resolve_model(translation, agent_id, raw, catalog)
            problems.extend(mp)
            notices.extend(mn)
            if ref:
                values[to] = ref
        else:
            values[to] = raw

    out = ["---"]
    if "description" in values:
        out.append(f"description: {values.pop('description')}")
    out.append("mode: subagent")
    for key in PINNED_KEYS:
        if key in values:
            out.append(f"{key}: {values.pop(key)}")
    out.extend(f"{k}: {v}" for k, v in values.items())

    granted, seen = {"read": False, "write": False, "bash": False}, []
    for tool in (t.strip() for t in tools.split(",")):
        if tool and tool not in seen:
            seen.append(tool)
    for tool in seen:
        row = tool_row(translation, tool)
        if row is None:
            problems.append(
                f"{agent_id}: tool `{tool}` has no translation.yaml tool_capabilities row "
                "(exact `tool:` or a declared `prefix:`) — declare its capability")
        elif row.get("opencode") in granted:
            granted[row["opencode"]] = True
        elif row.get("opencode") == "unsupported":
            notices.append(
                f"{agent_id}: tool `{tool}` grants no opencode permission — "
                f"{row.get('reason', 'no reason declared')}")
        else:
            problems.append(
                f"{agent_id}: tool_capabilities row for `{tool}` has unknown opencode "
                f"bucket {row.get('opencode')!r}")
    out.append("permission:")
    out.extend(f"  {b}: {'allow' if granted[b] else 'deny'}" for b in ("read", "write", "bash"))
    out.append("---")
    return "\n".join(out) + "\n" + body, problems, notices


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
RECORD=dotfiles-agents-laydown.md
mkdir -p "$ROOT/skills" "$ROOT/agents"
ns=0
for d in "$HERE"/skills/*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"
  rm -rf "$ROOT/skills/$n"
  cp -R "$d" "$ROOT/skills/$n"
  ns=$((ns + 1))
done
na=0
for f in "$HERE"/agents/*.md; do
  [ -f "$f" ] || continue
  cp "$f" "$ROOT/agents/$(basename "$f")"
  na=$((na + 1))
done
# The lane is built in a tempdir the wrapper deletes on exit, so the exclusions manifest
# has to land in $ROOT here or nobody ever reads it.
cp "$HERE/README.md" "$ROOT/$RECORD"
echo "opencode laydown complete -> $ROOT (skills: $ns, agents: $na). Hooks do not travel through this laydown; $ROOT/$RECORD lists every primitive left behind and why."
echo "Restart opencode to discover."
"""

FRAGMENT_HEADER = """// opencode.jsonc — mergeable config fragment for this lane.
// Generated by scripts/gen_opencode.py — do not hand-edit.
// Merge into ./opencode.jsonc, .opencode/opencode.jsonc, or the global config
// (~/.config/opencode/opencode.jsonc). Arrays concatenate, objects deep-merge.
// Every roster mcp entry that targets opencode renders into the `mcp` block below; one
// that does not is a row in the generated README's exclusions manifest.
"""


def _env_refs(value):
    """Rewrite CC `${VAR}` refs to opencode `{env:VAR}`, anywhere in a JSON value."""
    if isinstance(value, str):
        return ENV_REF.sub(r"{env:\1}", value)
    if isinstance(value, dict):
        return {k: _env_refs(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_env_refs(v) for v in value]
    return value


def render_mcp(eid, path):
    """One `.mcp.json` -> opencode `mcp` config entries. Returns (servers, problems).

    http/sse -> `{type: remote, url, headers}`; stdio -> `{type: local, command,
    environment}` (cc-to-opencode-mapping.md). A spec that will not render is a PROBLEM,
    never a skip — the whole point of this branch is that nothing drops without a trace.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            items = sorted(json.load(fh)["mcpServers"].items())
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        return {}, [f"{eid}: mcp spec {path} has no readable `mcpServers` object — {exc}"]
    if not items:
        return {}, [f"{eid}: mcp spec {path} declares no servers — nothing to render"]
    servers, problems = {}, []
    for name, cfg in items:
        cfg = cfg if isinstance(cfg, dict) else {}
        if cfg.get("url"):
            entry = {"type": "remote", "url": cfg["url"]}
            if cfg.get("headers"):
                entry["headers"] = cfg["headers"]
        elif cfg.get("command"):
            argv = cfg["command"]
            entry = {
                "type": "local",
                "command": (list(argv) if isinstance(argv, list) else [argv])
                + list(cfg.get("args") or []),
            }
            if cfg.get("env"):
                entry["environment"] = cfg["env"]
        else:
            problems.append(
                f"{eid}: server {name!r} declares neither `url` nor `command` — no opencode "
                "transport to render it into"
            )
            continue
        servers[name] = _env_refs(entry)
    return servers, problems


def render_fragment(servers):
    """The opencode.jsonc body — schema ref, plus an `mcp` block when anything rendered."""
    config = {"$schema": "https://opencode.ai/config.json"}
    if servers:
        config["mcp"] = servers
    return FRAGMENT_HEADER + json.dumps(config, indent=2, sort_keys=True) + "\n"


def build(out_root, entries, translation, catalog=None):
    """Lay the tree down. Returns (problems, notices) — see transform_agent for the split."""
    problems, notices = [], []
    excluded_ids = {r["id"]: r.get("reason", "") for r in translation["exclusions"] if "id" in r}
    members = opencode_members(entries)

    shipped = {"skill": [], "agent": [], "mcp": []}
    mcp_servers = {}
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
            rendered, agent_problems, agent_notices = transform_agent(
                text, translation, eid, catalog)
            problems.extend(agent_problems)
            notices.extend(agent_notices)
            os.makedirs(os.path.join(out_root, "agents"), exist_ok=True)
            with open(os.path.join(out_root, "agents", f"{eid}.md"), "w", encoding="utf-8") as fh:
                fh.write(rendered)
            shipped["agent"].append(eid)
        elif ptype == "mcp":
            servers, mcp_problems = render_mcp(eid, src)
            problems.extend(mcp_problems)
            problems.extend(
                f"{eid}: server name {name!r} collides with a server an earlier mcp entry "
                "already rendered, and opencode's `mcp` block is one flat namespace, so "
                "this one would overwrite it"
                for name in servers if name in mcp_servers
            )
            mcp_servers.update(servers)
            shipped["mcp"].append(eid)
        # No `ptype == "command"` branch by design (matrix: unsupported). Adding one means
        # never laying a command down while a skill it names is absent from this same
        # laydown — ship the skill with it, or give the command a documented fallback.

    with open(os.path.join(out_root, "install.sh"), "w", encoding="utf-8") as fh:
        fh.write(INSTALL_SH)
    os.chmod(os.path.join(out_root, "install.sh"), 0o755)
    with open(os.path.join(out_root, "opencode.jsonc"), "w", encoding="utf-8") as fh:
        fh.write(render_fragment(mcp_servers))

    lines = [
        "# opencode lane",
        "",
        "_Generated at install time by `scripts/gen_opencode.py` from `primitives-core/` +",
        "`translation.yaml` (ADR 0017; never tracked). opencode has no marketplace — install",
        "by laydown:_",
        "",
        "```sh",
        "sh scripts/install_opencode.sh --global          # ~/.config/opencode/{skills,agents}/",
        "sh scripts/install_opencode.sh --project <dir>   # <dir>/.opencode/{skills,agents}/",
        "```",
        "",
        "_If you are reading this file inside an installed tree, it was copied here as the",
        "record of that laydown — the `install.sh` that placed it lived in a build tempdir",
        "that is already gone. Re-run the command above from a checkout to update._",
        "",
        f"Ships {len(shipped['skill'])} skills (verbatim; opencode also reads `.claude/skills/`"
        " natively — this lane is the explicit, deterministic copy) and"
        f" {len(shipped['agent'])} agents (frontmatter remapped: `mode: subagent`,"
        " provider-prefixed models, CC tool allowlists inverted to permission maps).",
    ]
    if mcp_servers:
        n = len(mcp_servers)
        ids = ", ".join(f"`{i}`" for i in sorted(shipped["mcp"]))
        lines += [
            "",
            f"Registers {n} MCP server{'' if n == 1 else 's'} in `opencode.jsonc`, from {ids}"
            " — reshaped from the roster's `.mcp.json` specs (`{env:VAR}` refs,"
            " `remote`/`local` transports). Merge that fragment into your config;"
            " `install.sh` does not.",
        ]
    lines += [
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
    return problems, notices


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
    problems, notices = build(out, entries, translation)
    if notices:
        print(f"ℹ opencode laydown — {len(notices)} capability notice(s):")
        for n in notices:
            print(f"  - {n}")
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

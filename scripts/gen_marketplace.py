#!/usr/bin/env python3
"""gen_marketplace.py — assemble the Claude Code marketplace from primitives-core.

This is the repo's reference generator: it turns the hand-authored inputs — the roster
(primitives-core.yaml, which records membership via each entry's `plugins:` field), the
bundle metadata (plugins.yaml), and each bundle's README source
(bundles/<id>/README.md) — into generated, committed, drift-guarded
artifacts under the claude-code dist lane, dist/claude-code/ (ADR 0008; the publish
workflow lifts this lane to the ROOT of `main`, which is why every internal path below is
lane-relative):

  plugins/<bundle>/.claude-plugin/plugin.json   the CC plugin manifest (name == bundle id)
  plugins/<bundle>/skills/<id>/                 each member skill body, copied verbatim from
                                                primitives-core/skills/<id>/
  plugins/<bundle>/agents/<id>.md               each member agent body, copied verbatim from
                                                its primitives-core/agents/ source (single .md
                                                file); the shipped file is keyed on the roster
                                                id, mirroring skills/<id>/ and hooks/<id>/
  plugins/<bundle>/README.md                    the bundle's value/proof README, copied
                                                verbatim from its source (optional — a bundle
                                                with no README source ships without one)
  .claude-plugin/marketplace.json               the marketplace root listing every bundle,
                                                each source pointing at ./plugins/<bundle>
  PLUGINS.md                                    a generated inventory of every distributed
                                                plugin (name, kind, version, description,
                                                contents, install command) at the lane root

Every distributed plugin (bundle, kit, or standalone skill) must ship its own
plugins/<id>/README.md — asserted by readme_coverage_problems() as part of --check (issue
#144); a bundle/standalone README source with no committed README is a build failure, not the
additive-only tolerance _copy_bundle_readme/gen_standalone._copy_standalone_readme apply while
assembling the tree.

A Claude Code marketplace installs a *plugin*, and a plugin is a directory holding
`.claude-plugin/plugin.json` plus its skills. A bundle is a curated subset of the roster's
skills, so it cannot point straight at primitives-core (which holds every skill); the subset
is assembled here. The skill BODY still lives once in primitives-core/skills/<id>/, and a
bundle's README source lives once in bundles/<id>/README.md — the assembled
copies under plugins/ are generated output and are never hand-edited.

Deterministic and stdlib-only (stable ordering, no clocks/random), so a `--check` run never
false-fails. Two modes:

  python3 scripts/gen_marketplace.py            regenerate plugins/ + marketplace.json in place
  python3 scripts/gen_marketplace.py --check    build to a temp dir, diff vs committed, exit 1
                                                on any drift (this is `make build-check`)

Regenerate + drift-guard is the repo invariant for every generated artifact: a deterministic
generator plus a `--check` mode that rebuilds into a tempdir and diffs against the committed
copy. `make ci` runs the `--check`; no generated file is ever hand-edited.
"""

import argparse
import filecmp
import json
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import gen_standalone  # noqa: E402
from check_roster import parse_roster  # noqa: E402

ROSTER = os.path.join(REPO, "primitives-core.yaml")
PLUGINS_YAML = os.path.join(REPO, "plugins.yaml")
# The claude-code dist lane (ADR 0008): all generated marketplace artifacts live under
# dist/claude-code/ on dev; publish lifts the lane's contents to the root of `main`.
DIST = os.path.join(REPO, "dist", "claude-code")
PLUGINS_DIR = os.path.join(DIST, "plugins")
BUNDLES_DIR = os.path.join(REPO, "bundles")
MARKETPLACE = os.path.join(DIST, ".claude-plugin", "marketplace.json")
PLUGINS_MD = os.path.join(DIST, "PLUGINS.md")

IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")

# The distribution identity. This is the name-keyed marketplace ref that installed plugins
# resolve against (`<plugin>@dotfiles-agents`); it is the one identity the entry gate accepts
# at the marketplace root and must be preserved across the rebuild.
MARKETPLACE_NAME = "dotfiles-agents"

# The allowed `kind:` vocabulary for plugins.yaml entries — the PLUGINS.md inventory category.
# "standalone skill" is NOT in this set: standalone wrappers come from skill-catalog.yaml and
# get that kind assigned during assembly, never via plugins.yaml.
PLUGIN_KINDS = ("bundle", "plugin")
MARKETPLACE_SCHEMA = "https://anthropic.com/claude-code/marketplace.schema.json"
METADATA = {
    "version": "0.3.0",
    "description": (
        "Two desk bundles — code-desk (slim next-release execution under a documented repo "
        "standard) and exec-desk (the executive-desk overhead: planning, comms, board "
        "triage, deck themes) — plus three kits (foreman-kit: tiered delegation agents and "
        "session-discipline hooks; diagrams: structural diagrams; obsidian-toolkit: "
        "Obsidian plugin-dev guidance) and eight standalone one-skill plugins: "
        "github-project-board, private-fork, opencode-expertise, owner-signoff, "
        "pptx-themes, deep-research, dataviz, and update-config."
    ),
}


def _unquote(v):
    v = (v or "").strip()
    if len(v) >= 2 and v[0] in "'\"" and v[-1] == v[0]:
        return v[1:-1]
    return v


def _list(v):
    v = (v or "").strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip() for x in inner.split(",")] if inner else []
    return [v] if v else []


def parse_plugins_yaml(path):
    """Parse plugins.yaml into (owner_name, [{id, kind, version, description}]). Tailored line
    parser for our controlled format — no pyyaml, so it runs in CI with zero install."""
    owner_name = ""
    plugins, cur = [], None
    section = None  # 'owner' | 'plugins' | None
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if re.match(r"^owner:\s*$", line):
                section, cur = "owner", None
                continue
            if re.match(r"^plugins:\s*$", line):
                if cur is not None:
                    plugins.append(cur)
                    cur = None
                section = "plugins"
                continue
            if re.match(r"^\S", line):  # any other top-level key ends a section
                section = None
                continue
            if section == "owner":
                m = re.match(r"^  name:\s*(.*)$", line)
                if m:
                    owner_name = _unquote(m.group(1))
                continue
            if section == "plugins":
                m = re.match(r"^  - id:\s*(.*)$", line)
                if m:
                    if cur is not None:
                        plugins.append(cur)
                    cur = {"id": _unquote(m.group(1))}
                    continue
                m = re.match(r"^    (\w+):\s*(.*)$", line)
                if m and cur is not None:
                    cur[m.group(1)] = _unquote(m.group(2))
    if cur is not None:
        plugins.append(cur)
    return owner_name, plugins


def plugin_meta_problems(plugin_meta):
    """Validate the parsed plugins.yaml entries. `kind:` is REQUIRED on every entry and must
    be one of PLUGIN_KINDS — a missing kind used to silently default to "bundle" (PR #145
    review flag), a latent mislabeling risk for future kits. Returns a list of problems
    (empty = clean), each naming the offending entry."""
    allowed = ", ".join(PLUGIN_KINDS)
    problems = []
    for meta in plugin_meta:
        pid = meta.get("id") or "(missing id)"
        kind = meta.get("kind")
        if not kind:
            problems.append(
                f"plugins.yaml: entry '{pid}' is missing required field `kind` "
                f"(allowed: {allowed}) — no silent default"
            )
        elif kind not in PLUGIN_KINDS:
            problems.append(
                f"plugins.yaml: entry '{pid}' has invalid kind '{kind}' (allowed: {allowed})"
            )
    return problems


def bundle_members(roster):
    """Map each bundle id -> sorted list of the skill ids that name it in `plugins:`."""
    return _members_of_type(roster, "skill")


def bundle_hooks(roster):
    """Map each bundle id -> sorted list of the hook ids that name it in `plugins:`."""
    return _members_of_type(roster, "hook")


def bundle_agents(roster):
    """Map each bundle id -> sorted list of the agent ids that name it in `plugins:`."""
    return _members_of_type(roster, "agent")


def _members_of_type(roster, wanted):
    members = {}
    for e in roster:
        if e.get("type") != wanted:
            continue
        for bundle in _list(e.get("plugins", "")):
            members.setdefault(bundle, []).append(e["id"])
    return {b: sorted(ids) for b, ids in members.items()}


def _hook_command(name, cfg):
    """The plugin hooks-manifest command for one hook: an env prefix (sorted, deterministic)
    then `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<name>/hook.py"`."""
    env = cfg.get("env") or {}
    prefix = "".join(f"{k}={env[k]} " for k in sorted(env))
    return f'{prefix}python3 "${{CLAUDE_PLUGIN_ROOT}}/hooks/{name}/hook.py"'


def build_hooks_manifest(hook_ids, src_by_id):
    """Synthesize the plugin `hooks/hooks.json` from each hook's committed config.json (which
    carries its event binding). Returns the manifest dict, or None if the bundle has no hooks.
    Deterministic: hooks grouped per event, ordered by hook id."""
    if not hook_ids:
        return None
    events = {}
    for name in sorted(hook_ids):
        cfg_path = os.path.join(REPO, src_by_id[name], "config.json")
        with open(cfg_path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        events.setdefault(cfg["event"], []).append(
            {
                "matcher": cfg.get("matcher", "*"),
                "hooks": [
                    {
                        "type": "command",
                        "command": _hook_command(name, cfg),
                        "timeout": cfg.get("timeout", 10),
                        "statusMessage": cfg.get("statusMessage", ""),
                    }
                ],
            }
        )
    return {"hooks": events}


def _copy_bundle_readme(bundle, proot):
    """Copy bundles/<bundle>/README.md -> <proot>/README.md if the source
    exists. Additive only: a bundle with no README source ships without one — this must
    never fail the build."""
    src = os.path.join(BUNDLES_DIR, bundle, "README.md")
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(proot, "README.md"))


def build_marketplace(out_root):
    """Assemble every bundle under out_root/plugins/ and write out_root/.claude-plugin/
    marketplace.json. Returns the marketplace dict. Bundles with no members are skipped."""
    owner_name, plugin_meta = parse_plugins_yaml(PLUGINS_YAML)
    meta_problems = plugin_meta_problems(plugin_meta)
    if meta_problems:
        raise ValueError(
            "invalid plugins.yaml — "
            + f"{len(meta_problems)} problem(s):\n"
            + "\n".join(f"  - {p}" for p in meta_problems)
        )
    author = {"name": owner_name}
    roster = parse_roster(ROSTER)
    src_by_id = {e["id"]: e["source"] for e in roster}
    members = bundle_members(roster)
    hooks = bundle_hooks(roster)
    agents = bundle_agents(roster)

    plugins_out = os.path.join(out_root, "plugins")
    entries = []
    # PLUGINS.md (issue #144): per-entry inventory metadata, gathered alongside assembly so it
    # is derived from the SAME data the plugin.json / marketplace.json entries are built from —
    # never a second, divergeable source. `kind` is a plain-English inventory category (bundle /
    # plugin / standalone skill), NOT the skill-catalog's structural distinction. It is required
    # on every plugins.yaml entry (validated above in plugin_meta_problems — no silent default).
    kind_of = {}
    contents_of = {}
    for meta in plugin_meta:
        bundle = meta["id"]
        ids = members.get(bundle, [])
        hook_ids = hooks.get(bundle, [])
        agent_ids = agents.get(bundle, [])
        if not ids and not hook_ids and not agent_ids:
            continue  # a metadata-only bundle with no roster members does not ship yet
        kind_of[bundle] = meta["kind"]
        contents_of[bundle] = {"skills": ids, "hooks": hook_ids, "agents": agent_ids}
        proot = os.path.join(plugins_out, bundle)
        os.makedirs(os.path.join(proot, ".claude-plugin"), exist_ok=True)
        manifest = {
            "name": bundle,
            "description": meta.get("description", ""),
            "version": meta.get("version", "0.0.1"),
            "author": author,
        }
        with open(os.path.join(proot, ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump(manifest, fh, indent=2, sort_keys=True)
            fh.write("\n")
        for skill_id in ids:
            shutil.copytree(
                os.path.join(REPO, src_by_id[skill_id]),
                os.path.join(proot, "skills", skill_id),
                ignore=IGNORE,
            )
        for hook_id in hook_ids:
            shutil.copytree(
                os.path.join(REPO, src_by_id[hook_id]),
                os.path.join(proot, "hooks", hook_id),
                ignore=IGNORE,
            )
        hooks_manifest = build_hooks_manifest(hook_ids, src_by_id)
        if hooks_manifest is not None:
            with open(os.path.join(proot, "hooks", "hooks.json"), "w") as fh:
                json.dump(hooks_manifest, fh, indent=2, sort_keys=True)
                fh.write("\n")
        if agent_ids:
            os.makedirs(os.path.join(proot, "agents"), exist_ok=True)
            for agent_id in agent_ids:
                src = src_by_id[agent_id]  # primitives-core/agents/<file>.md — a single file
                # Key the shipped artifact on the roster id (like skills/<skill_id> and
                # hooks/<hook_id>), NOT the source filename — otherwise a source-filename ≠ id
                # mismatch ships silently, uncaught by the roster/identity guards.
                shutil.copy2(
                    os.path.join(REPO, src),
                    os.path.join(proot, "agents", f"{agent_id}.md"),
                )
        _copy_bundle_readme(bundle, proot)
        entries.append(
            {
                "name": bundle,
                "source": f"./plugins/{bundle}",
                "description": meta.get("description", ""),
                "version": meta.get("version", "0.0.1"),
                "author": author,
            }
        )

    # Standalone one-skill wrappers (D4): gen_standalone emits each catalogued skill as its own
    # plugin under plugins/<id>/, and its marketplace entries are merged here so the one
    # committed marketplace.json covers bundles AND standalone installs. A standalone plugin
    # name is the skill id (guaranteed distinct from bundle ids by check_skill_catalog).
    gen_standalone.build_standalone(plugins_out)
    for entry in gen_standalone.standalone_entries():
        entries.append(entry)
        kind_of[entry["name"]] = "standalone skill"
        contents_of[entry["name"]] = {"skills": [entry["name"]], "hooks": [], "agents": []}

    marketplace = {
        "$schema": MARKETPLACE_SCHEMA,
        "name": MARKETPLACE_NAME,
        "owner": author,
        "metadata": METADATA,
        "plugins": sorted(entries, key=lambda p: p["name"]),
    }
    os.makedirs(os.path.join(out_root, ".claude-plugin"), exist_ok=True)
    with open(os.path.join(out_root, ".claude-plugin", "marketplace.json"), "w") as fh:
        json.dump(marketplace, fh, indent=2, sort_keys=True)
        fh.write("\n")
    _write_plugins_md(out_root, marketplace, kind_of, contents_of)
    return marketplace


def _contents_line(contents):
    """One human line per non-empty primitive type, e.g. '2 skills — foreman, handoff'."""
    parts = []
    for label, ids in (("skill", contents["skills"]), ("hook", contents["hooks"]), ("agent", contents["agents"])):
        if not ids:
            continue
        plural = label if len(ids) == 1 else f"{label}s"
        parts.append(f"{len(ids)} {plural} — {', '.join(ids)}")
    return "; ".join(parts) if parts else "(no members)"


def _write_plugins_md(out_root, marketplace, kind_of, contents_of):
    """Render PLUGINS.md: one section per distributed plugin (name, kind, version, description,
    contents summary, install command), sorted the same as marketplace.json (by name).
    Deterministic — reads only the marketplace dict + the kind/contents gathered during
    assembly, so a rebuild with unchanged source is byte-identical output."""
    lines = [
        "# Plugin inventory",
        "",
        "<!-- GENERATED FILE — do not hand-edit. Regenerate via `make build` "
        "(scripts/gen_marketplace.py); `make build-check` fails on drift. -->",
        "",
        f"Every plugin distributed by the `{MARKETPLACE_NAME}` marketplace, generated from "
        "`plugins.yaml` + `primitives-core.yaml` (bundles/kits) and `skill-catalog.yaml` "
        "(standalone skills).",
        "",
    ]
    for entry in marketplace["plugins"]:
        name = entry["name"]
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- **Kind:** {kind_of.get(name, 'standalone skill')}")
        lines.append(f"- **Version:** {entry['version']}")
        lines.append(f"- **Description:** {entry['description']}")
        lines.append(f"- **Ships:** {_contents_line(contents_of.get(name, {'skills': [], 'hooks': [], 'agents': []}))}")
        lines.append(f"- **Install:** `claude plugin install {name}@{MARKETPLACE_NAME}`")
        lines.append("")
    with open(os.path.join(out_root, "PLUGINS.md"), "w") as fh:
        fh.write("\n".join(lines).rstrip("\n") + "\n")


def readme_coverage_problems(out_root, marketplace):
    """D3 (issue #144): every distributed plugin must ship plugins/<id>/README.md. Returns a
    list of problems (empty = clean); red-able by removing any README source, since a missing
    source means `_copy_bundle_readme` / `_copy_standalone_readme` write nothing."""
    problems = []
    for entry in marketplace["plugins"]:
        name = entry["name"]
        readme = os.path.join(out_root, "plugins", name, "README.md")
        if not os.path.isfile(readme):
            problems.append(f"plugins/{name}/README.md: missing (every distributed plugin must ship a README)")
    return problems


def _identical(a, b):
    """True iff paths a and b are byte-identical (recursive for dirs, exact for files)."""
    if os.path.isdir(a) or os.path.isdir(b):
        if not (os.path.isdir(a) and os.path.isdir(b)):
            return False
        # ignore OS litter: Finder drops .DS_Store into browsed dirs, which would make
        # the drift check false-fail against a freshly generated tree
        cmp = filecmp.dircmp(a, b, ignore=filecmp.DEFAULT_IGNORES + [".DS_Store"])
        if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
            return False
        _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
        if mismatch or errors:
            return False
        return all(
            _identical(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs
        )
    if not (os.path.isfile(a) and os.path.isfile(b)):
        return False
    return filecmp.cmp(a, b, shallow=False)


def check():
    """Rebuild into a temp dir and diff vs the committed artifacts. Returns problem list."""
    tmp = tempfile.mkdtemp(prefix="gen-marketplace-check-")
    problems = []
    try:
        marketplace = build_marketplace(tmp)
        pairs = [
            (os.path.join(tmp, "plugins"), PLUGINS_DIR, "plugins/"),
            (
                os.path.join(tmp, ".claude-plugin", "marketplace.json"),
                MARKETPLACE,
                ".claude-plugin/marketplace.json",
            ),
            (os.path.join(tmp, "PLUGINS.md"), PLUGINS_MD, "PLUGINS.md"),
        ]
        for built, committed, label in pairs:
            if not os.path.exists(committed):
                problems.append(f"{label}: missing (run `make build` and commit)")
            elif not _identical(built, committed):
                problems.append(f"{label}: drift — committed copy != freshly generated")
        # D3 (issue #144): every distributed plugin ships plugins/<id>/README.md. Checked
        # against the freshly-built tmp tree, same as the drift pairs above.
        problems.extend(readme_coverage_problems(tmp, marketplace))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return problems


def regenerate():
    """Regenerate the committed dist/claude-code/ lane in place."""
    if os.path.isdir(PLUGINS_DIR):
        shutil.rmtree(PLUGINS_DIR)
    os.makedirs(DIST, exist_ok=True)
    m = build_marketplace(DIST)
    return m


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="gen_marketplace.py", description=__doc__.split("\n")[0]
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="build to a temp dir and diff vs the committed artifacts (exit 1 on drift)",
    )
    args = p.parse_args(argv)

    try:
        if args.check:
            problems = check()
            if problems:
                print(f"✗ marketplace drift: {len(problems)} problem(s)")
                for pr in problems:
                    print(f"  - {pr}")
                return 1
            print("✓ marketplace artifacts match source — no drift")
            return 0

        m = regenerate()
    except ValueError as e:
        # Bad hand-authored input (e.g. a plugins.yaml entry with a missing/invalid `kind`)
        # fails loudly in both modes — never a silent default.
        print(f"✗ {e}")
        return 1
    n = len(m["plugins"])
    names = ", ".join(pl["name"] for pl in m["plugins"])
    print(f"✓ regenerated marketplace — {n} plugin(s): {names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

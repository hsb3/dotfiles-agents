#!/usr/bin/env python3
"""Translation service (Phase 3, issue #6).

Reads the roster (primitives-core.yaml), plugin metadata (plugins.yaml), the capability config
(primitives-core-translation-config.yaml), and the externals tracker (externals.yaml); renders
each primitive into each target per its capability cell; writes static bundles under targets/ +
a content-hash lock (primitives-core-translation-results.json).

Scope (technical-plan §2.1): skills native (copy) · agents transform (opencode frontmatter) ·
Claude Code marketplace assembly · claude-agents (CMA) render — static POST /v1/agents and
/v1/skills payloads under targets/claude-agents/ (#6) · mcp render — neutral connection specs
(primitives-core/mcp/<name>.json for self-authored + externals.yaml kind:mcp / externals/mcp/
for third-party) -> each target's mcp config fragment (CC mcpServers, opencode mcp, CMA
mcp_servers[]; CMA is remote-only so local stdio servers record a skip). Hooks ship to
claude-code only.

Deterministic: stable ordering, no clocks/timestamps in output — so the --check drift guard never
false-fails. Stdlib-only (tailored parsers, no pyyaml) so it runs in CI with zero install.

Usage:
  python3 scripts/translate.py            # build targets/ + results lock in place
  python3 scripts/translate.py --check    # build to a temp dir, diff vs committed; exit 1 on drift
"""

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(REPO, "primitives-core.yaml")
PLUGINS_YAML = os.path.join(REPO, "plugins.yaml")
EXTERNALS = os.path.join(REPO, "externals.yaml")
CONFIG = os.path.join(REPO, "primitives-core-translation-config.yaml")
RESULTS = os.path.join(REPO, "primitives-core-translation-results.json")
TARGETS = ("claude-code", "opencode", "claude-agents")
IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc")
MARKETPLACE_SCHEMA = "https://anthropic.com/claude-code/marketplace.schema.json"
OWNER = {"name": "Henry S. Burden III"}


# ── parsing ────────────────────────────────────────────────────────────────────────────
def _list(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip() for x in inner.split(",")] if inner else []
    return [v] if v else []


def parse_roster(path):
    entries, cur, in_list = [], None, False
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if re.match(r"^primitives:\s*(\[\s*\])?\s*$", line):
            in_list = True
            continue
        if not in_list:
            continue
        m = re.match(r"^  - (\w+):\s*(.*)$", line)
        if m:
            if cur:
                entries.append(cur)
            cur = {m.group(1): m.group(2).strip()}
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip()
    if cur:
        entries.append(cur)
    for e in entries:
        e["targets"] = _list(e.get("targets", ""))
        e["plugins"] = _list(e.get("plugins", ""))
    return entries


def parse_externals(path):
    """Parse externals.yaml's `externals:` list into dicts (flat fields; targets via _list).
    Only kind: mcp entries are rendered today; skill/plugin entries are clone-at-build (pending)."""
    entries, cur, in_list = [], None, False
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if re.match(r"^externals:\s*$", line):
            in_list = True
            continue
        if not in_list:
            continue
        m = re.match(r"^  - (\w+):\s*(.*)$", line)
        if m:
            if cur:
                entries.append(cur)
            cur = {m.group(1): m.group(2).strip()}
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m and cur is not None:
            cur[m.group(1)] = m.group(2).strip()
    if cur:
        entries.append(cur)
    for e in entries:
        e["targets"] = _list(e.get("targets", ""))
    return entries


def parse_plugins(path):
    meta, cur = {}, None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        m = re.match(r"^  - id:\s*(.*)$", line)
        if m:
            cur = m.group(1).strip()
            meta[cur] = {}
            continue
        m = re.match(r'^    (\w+):\s*"?(.*?)"?\s*$', line)
        if m and cur:
            meta[cur][m.group(1)] = m.group(2)
    return meta


def parse_capabilities(path):
    """capabilities[type][target] = capability string (native/transform/render/unsupported)."""
    caps, cur_type, in_caps = {}, None, False
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if re.match(r"^capabilities:\s*$", line):
            in_caps = True
            continue
        if not in_caps:
            continue
        m = re.match(r"^  (\w+):\s*$", line)
        if m:
            cur_type = m.group(1)
            caps[cur_type] = {}
            continue
        m = re.match(r"^    ([\w-]+):\s*\{[^}]*capability:\s*(\w+)", line)
        if m and cur_type:
            caps[cur_type][m.group(1)] = m.group(2)
    return caps


def parse_cma_options(path):
    """Top-level `cma:` block -> options dict (e.g. default_model). Defaults applied by caller."""
    opts, in_cma = {}, False
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if re.match(r"^cma:\s*$", line):
            in_cma = True
            continue
        if in_cma:
            m = re.match(r"^  (\w+):\s*(.*?)\s*$", line)
            if m:
                opts[m.group(1)] = m.group(2)
            elif line and not line.startswith((" ", "#")):
                break  # next top-level key
    return opts


# ── helpers ────────────────────────────────────────────────────────────────────────────
def copy_into(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src):
        shutil.copytree(src, dst, ignore=IGNORE, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)


def sha256_path(path):
    """Content fingerprint: a file's bytes, or a dir's files hashed in globally-sorted relpath
    order (NOT os.walk order — that varies by filesystem and would break the cross-platform lock)."""
    h = hashlib.sha256()
    if os.path.isfile(path):
        h.update(open(path, "rb").read())
        return h.hexdigest()
    items = []
    for root, _d, files in os.walk(path):
        for f in files:
            if f == ".DS_Store":
                continue
            fp = os.path.join(root, f)
            items.append((os.path.relpath(fp, path).replace(os.sep, "/"), fp))
    for rel, fp in sorted(items):
        h.update(rel.encode())
        h.update(open(fp, "rb").read())
    return h.hexdigest()


def transform_agent_opencode(src_path):
    """CC agent .md -> opencode agent .md: keep description (verbatim), drop name/model/color,
    add `mode: subagent`. Description is preserved byte-for-byte (it carries literal \\n /
    <example> blocks that re-serialization would corrupt)."""
    text = open(src_path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return "---\nmode: subagent\n---\n" + text
    fm, body = m.group(1).split("\n"), m.group(2)
    out, skipping = [], False
    for ln in fm:
        key = re.match(r"^([\w-]+):", ln)
        if key:
            skipping = key.group(1) in {"name", "model", "color"}
            if not skipping:
                out.append(ln)
        elif not skipping:
            out.append(ln)
    out.append("mode: subagent")
    return "---\n" + "\n".join(out) + "\n---\n" + body


def agent_system(src_path):
    """CC agent .md -> the `system` string for a CMA payload: the body with frontmatter stripped
    (leading/trailing whitespace trimmed). Frontmatter carries name/model/color; the persona that
    drives behavior is the body."""
    text = open(src_path, encoding="utf-8").read()
    m = re.match(r"^---\n.*?\n---\n?(.*)$", text, re.S)
    return (m.group(1) if m else text).strip()


def skill_display_title(skill_dir):
    """Extract the `name:` from a skill's SKILL.md frontmatter (CMA derives name/description from
    the uploaded SKILL.md; we surface the name as display_title on the build-sheet). Falls back to
    the folder name if absent."""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if os.path.isfile(skill_md):
        text = open(skill_md, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        if m:
            for ln in m.group(1).split("\n"):
                km = re.match(r"^name:\s*(.+?)\s*$", ln)
                if km:
                    return km.group(1).strip().strip("'\"")
    return os.path.basename(skill_dir.rstrip("/"))


# ── mcp render: neutral connection spec -> each target's mcp config schema ───────────────
def load_mcp_spec(src_path):
    """Read a neutral mcp connection spec (primitives-core/mcp/<name>.json)."""
    return json.load(open(src_path, encoding="utf-8"))


def mcp_to_claude(spec):
    """Neutral spec -> a Claude Code mcpServers fragment (merge into .mcp.json / ~/.claude.json)."""
    if spec.get("transport") == "http":
        entry = {"type": "http", "url": spec["url"]}
        if spec.get("headers"):
            entry["headers"] = spec["headers"]
    else:
        entry = {
            "type": "stdio",
            "command": spec["command"],
            "args": spec.get("args", []),
            "env": spec.get("env", {}),
        }
    return {"mcpServers": {spec["name"]: entry}}


def mcp_to_opencode(spec):
    """Neutral spec -> an opencode `mcp` fragment (type: local|remote; command is one array)."""
    if spec.get("transport") == "http":
        entry = {"type": "remote", "url": spec["url"], "enabled": True}
        if spec.get("headers"):
            entry["headers"] = spec["headers"]
    else:
        entry = {
            "type": "local",
            "command": [spec["command"], *spec.get("args", [])],
            "enabled": True,
        }
        if spec.get("env"):
            entry["environment"] = spec["env"]
    return {"mcp": {spec["name"]: entry}}


def mcp_to_cma(spec):
    """Neutral spec -> a CMA mcp_servers[] entry. CMA is remote-only — callers gate on transport."""
    return {"mcp_servers": [{"type": "url", "url": spec["url"], "name": spec["name"]}]}


def write_json(path, payload):
    """Deterministic JSON write (sorted keys, trailing newline) for a generated fragment."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


# ── build ──────────────────────────────────────────────────────────────────────────────
def render_marketplace(built_plugins, source_prefix):
    """Marketplace catalog for the built plugins, with `source` under source_prefix.

    Two catalogs are emitted from the same data: the in-target one (prefix `./plugins/`,
    beside the plugin folders — used by a local-path add of `targets/claude-code`) and the
    repo-root one (prefix `./targets/claude-code/plugins/` — used by the `owner/repo`
    shorthand, which only reads `.claude-plugin/marketplace.json` at the repo root)."""
    plugins = sorted(
        (
            {
                "name": p["name"],
                "source": f"{source_prefix}{p['name']}",
                "description": p["description"],
                "version": p["version"],
                "author": OWNER,
            }
            for p in built_plugins
        ),
        key=lambda x: x["name"],
    )
    return {
        "$schema": MARKETPLACE_SCHEMA,
        "name": "dotfiles-agents",
        "owner": OWNER,
        "metadata": {
            "version": "0.1.0",
            "description": "Proven coding-agent extenders, generated from primitives-core.",
        },
        "plugins": plugins,
    }


def write_root_marketplace(dest_root, built_plugins):
    """Emit the repo-root `.claude-plugin/marketplace.json` (sources into targets/)."""
    market = render_marketplace(built_plugins, "./targets/claude-code/plugins/")
    d = os.path.join(dest_root, ".claude-plugin")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "marketplace.json"), "w") as fh:
        json.dump(market, fh, indent=2)
        fh.write("\n")
    return market


def build(out_root, roster, plugins_meta, caps, cma_model, externals):
    """Render all targets under out_root. Returns the results dict."""
    results = {t: {} for t in TARGETS}
    for t in TARGETS:
        os.makedirs(os.path.join(out_root, t), exist_ok=True)
        open(os.path.join(out_root, t, ".gitkeep"), "w").close()

    def rec(target, pid, capability, dest=None, skipped=False, reason=None):
        r = {"capability": capability, "skipped": skipped}
        if dest:
            r["destination"] = dest
            r["sha256"] = sha256_path(os.path.join(out_root, dest))
        if reason:
            r["reason"] = reason
        results[target][pid] = r

    # ---- claude-code: core raw (skills/agents) + toggle plugin bundles + marketplace ----
    cc = os.path.join(out_root, "claude-code")
    for e in sorted(roster, key=lambda x: x["id"]):
        if "claude-code" not in e["targets"]:
            continue
        t, pid, src = e["type"], e["id"], os.path.join(REPO, e["source"])
        cap = caps.get(t, {}).get("claude-code", "native")
        if t == "mcp":
            # mcp is config, not a folder/plugin member — emit a mergeable fragment (shelf-agnostic)
            d = f"claude-code/mcp/{pid}.json"
            write_json(os.path.join(out_root, d), mcp_to_claude(load_mcp_spec(src)))
            rec("claude-code", pid, cap, d)
            continue
        if e["shelf"] == "core":
            if t == "skill":
                d = f"claude-code/skills/{pid}"
            elif t == "agent":
                d = f"claude-code/agents/{pid}.md"
            else:
                continue
            copy_into(src, os.path.join(out_root, d))
            rec("claude-code", pid, cap, d)
        # toggle members are placed during plugin assembly below

    # plugin assembly (plugin members -> plugins/<p>/)
    built_plugins = []
    plugin_ids = sorted({p for e in roster for p in e["plugins"]})
    for p in plugin_ids:
        members = [
            e for e in roster if p in e["plugins"] and "claude-code" in e["targets"]
        ]
        if not members:
            continue
        proot = os.path.join(cc, "plugins", p)
        # .claude-plugin/plugin.json
        meta = plugins_meta.get(p, {})
        pj = {
            "name": p,
            "description": meta.get("description", ""),
            "version": meta.get("version", "0.0.1"),
            "author": OWNER,
        }
        os.makedirs(os.path.join(proot, ".claude-plugin"), exist_ok=True)
        with open(os.path.join(proot, ".claude-plugin", "plugin.json"), "w") as fh:
            json.dump(pj, fh, indent=2, sort_keys=True)
            fh.write("\n")
        hooks_done = False
        for e in sorted(members, key=lambda x: x["id"]):
            t, pid, src = e["type"], e["id"], os.path.join(REPO, e["source"])
            if t == "skill":
                d = f"claude-code/plugins/{p}/skills/{pid}"
                copy_into(src, os.path.join(out_root, d))
                rec("claude-code", pid, caps["skill"]["claude-code"], d)
            elif t == "agent":
                d = f"claude-code/plugins/{p}/agents/{pid}.md"
                copy_into(src, os.path.join(out_root, d))
                rec("claude-code", pid, caps["agent"]["claude-code"], d)
            elif t == "hook":
                # the whole per-plugin hook fragment (hooks/ + hooks-handlers/) — copy once
                if not hooks_done:
                    frag = os.path.join(REPO, "primitives-core", "hooks", p)
                    for sub in ("hooks", "hooks-handlers"):
                        s = os.path.join(frag, sub)
                        if os.path.isdir(s):
                            copy_into(s, os.path.join(proot, sub))
                    hooks_done = True
                d = f"claude-code/plugins/{p}/hooks-handlers/{pid}.sh"
                rec("claude-code", pid, caps["hook"]["claude-code"], d)
        built_plugins.append(
            {
                "name": p,
                "description": meta.get("description", ""),
                "version": meta.get("version", "0.0.1"),
            }
        )

    # in-target catalog (beside the plugin folders; local-path add of targets/claude-code)
    market = render_marketplace(built_plugins, "./plugins/")
    os.makedirs(os.path.join(cc, ".claude-plugin"), exist_ok=True)
    with open(os.path.join(cc, ".claude-plugin", "marketplace.json"), "w") as fh:
        json.dump(market, fh, indent=2)
        fh.write("\n")

    # ---- opencode: all skills raw + all agents transformed (hooks unsupported) ----
    for e in sorted(roster, key=lambda x: x["id"]):
        if "opencode" not in e["targets"]:
            continue
        t, pid, src = e["type"], e["id"], os.path.join(REPO, e["source"])
        cap = caps.get(t, {}).get("opencode", "unsupported")
        if t == "skill":
            d = f"opencode/skills/{pid}"
            copy_into(src, os.path.join(out_root, d))
            rec("opencode", pid, cap, d)
        elif t == "agent":
            d = f"opencode/agents/{pid}.md"
            os.makedirs(os.path.dirname(os.path.join(out_root, d)), exist_ok=True)
            open(os.path.join(out_root, d), "w").write(transform_agent_opencode(src))
            rec("opencode", pid, cap, d)
        elif t == "mcp":
            d = f"opencode/mcp/{pid}.json"
            write_json(os.path.join(out_root, d), mcp_to_opencode(load_mcp_spec(src)))
            rec("opencode", pid, cap, d)
        elif t == "hook":
            rec(
                "opencode",
                pid,
                cap,
                skipped=True,
                reason="opencode hooks unsupported (CC-only)",
            )

    # ---- claude-agents (CMA): static API payloads — agents POST /v1/agents, skills POST /v1/skills ----
    # Deterministic, committed, drift-guarded artifacts; deploy (the actual POST) is dotfiles-bootstrap's
    # concern. Contract: CANON.md "Resolved — managed-agents (CMA) contract".
    for e in sorted(roster, key=lambda x: x["id"]):
        if "claude-agents" not in e["targets"]:
            continue
        t, pid, src = e["type"], e["id"], os.path.join(REPO, e["source"])
        cap = caps.get(t, {}).get("claude-agents", "render")
        if t == "agent":
            # BetaManagedAgentsCreateAgentParams: name+model required; system from the body.
            payload = {
                "name": pid,
                "model": cma_model,
                "system": agent_system(src),
                "tools": [],
                "skills": [],
                "metadata": {},
            }
            d = f"claude-agents/agents/{pid}.json"
            os.makedirs(os.path.dirname(os.path.join(out_root, d)), exist_ok=True)
            with open(os.path.join(out_root, d), "w") as fh:
                json.dump(payload, fh, indent=2, sort_keys=True)
                fh.write("\n")
            rec("claude-agents", pid, cap, d)
        elif t == "skill":
            # POST /v1/skills multipart: the skill folder uploads as-is (SKILL.md at root); a
            # sidecar .upload.json describes the multipart (file list + display_title).
            folder = f"claude-agents/skills/{pid}"
            copy_into(src, os.path.join(out_root, folder))
            files = sorted(
                os.path.relpath(
                    os.path.join(dp, f), os.path.join(out_root, folder)
                ).replace(os.sep, "/")
                for dp, _d, fs in os.walk(os.path.join(out_root, folder))
                for f in fs
                if f != ".DS_Store"
            )
            sheet = {
                "endpoint": "POST /v1/skills",
                "display_title": skill_display_title(src),
                "files": files,
            }
            d = f"claude-agents/skills/{pid}.upload.json"
            with open(os.path.join(out_root, d), "w") as fh:
                json.dump(sheet, fh, indent=2, sort_keys=True)
                fh.write("\n")
            # fingerprint the folder (the upload set) — the sheet's sha is implied by its inputs.
            rec("claude-agents", pid, cap, folder)
        elif t == "mcp":
            # CMA mcp_servers[] are remote-only; a local stdio server has no CMA equivalent.
            spec = load_mcp_spec(src)
            if spec.get("transport") == "http":
                d = f"claude-agents/mcp/{pid}.json"
                write_json(os.path.join(out_root, d), mcp_to_cma(spec))
                rec("claude-agents", pid, cap, d)
            else:
                rec(
                    "claude-agents",
                    pid,
                    cap,
                    skipped=True,
                    reason="CMA mcp_servers are remote-only; this server is local stdio",
                )
        else:
            rec(
                "claude-agents",
                pid,
                caps.get(t, {}).get("claude-agents", "unsupported"),
                skipped=True,
                reason="no CMA equivalent for this primitive type",
            )

    # ---- externals: third-party mcp connection specs (externals.yaml kind: mcp) ----
    # skill/plugin externals are clone-at-build (not implemented yet); only mcp renders today.
    for ext in sorted(externals, key=lambda x: x["id"]):
        if ext.get("kind") != "mcp":
            continue
        pid = ext["id"]
        spec = load_mcp_spec(os.path.join(REPO, ext["spec"]))
        spec.setdefault("name", pid)
        tgs = ext.get("targets", [])
        if "claude-code" in tgs:
            d = f"claude-code/mcp/{pid}.json"
            write_json(os.path.join(out_root, d), mcp_to_claude(spec))
            rec("claude-code", pid, "render", d)
        if "opencode" in tgs:
            d = f"opencode/mcp/{pid}.json"
            write_json(os.path.join(out_root, d), mcp_to_opencode(spec))
            rec("opencode", pid, "render", d)
        if "claude-agents" in tgs:
            if spec.get("transport") == "http":
                d = f"claude-agents/mcp/{pid}.json"
                write_json(os.path.join(out_root, d), mcp_to_cma(spec))
                rec("claude-agents", pid, "render", d)
            else:
                rec(
                    "claude-agents",
                    pid,
                    "render",
                    skipped=True,
                    reason="CMA mcp_servers are remote-only; this server is local stdio",
                )

    return results, built_plugins


def write_results(path, results):
    payload = {
        "_note": "GENERATED by scripts/translate.py — do not hand-edit. CI regenerates and fails on drift.",
        "version": 1,
        "generated": True,
        "results": results,
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


CMA_DEFAULT_MODEL = (
    "claude-sonnet-4-5"  # fallback if the config omits cma.default_model
)


def load_inputs():
    cma = parse_cma_options(CONFIG)
    return (
        parse_roster(ROSTER),
        parse_plugins(PLUGINS_YAML),
        parse_capabilities(CONFIG),
        cma.get("default_model", CMA_DEFAULT_MODEL),
        parse_externals(EXTERNALS),
    )


def summarize(results):
    parts = []
    for t in TARGETS:
        built = sum(1 for r in results[t].values() if not r["skipped"])
        skipped = sum(1 for r in results[t].values() if r["skipped"])
        parts.append(f"{t}: {built} built, {skipped} skipped")
    return " · ".join(parts)


def diff_trees(a, b):
    """Return list of path-level differences between dirs a and b."""
    diffs = []

    def files(root):
        out = {}
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if f == ".DS_Store":
                    continue
                fp = os.path.join(dp, f)
                out[os.path.relpath(fp, root)] = fp
        return out

    fa, fb = files(a), files(b)
    for rel in sorted(set(fa) - set(fb)):
        diffs.append(f"only in generated: {rel}")
    for rel in sorted(set(fb) - set(fa)):
        diffs.append(f"only in committed: {rel}")
    for rel in sorted(set(fa) & set(fb)):
        if open(fa[rel], "rb").read() != open(fb[rel], "rb").read():
            diffs.append(f"differs: {rel}")
    return diffs


def main():
    check = "--check" in sys.argv
    roster, plugins_meta, caps, cma_model, externals = load_inputs()

    if check:
        tmp = tempfile.mkdtemp(prefix="translate-check-")
        try:
            results, built = build(
                tmp, roster, plugins_meta, caps, cma_model, externals
            )
            # compare only the generated per-target subdirs (targets/README.md is curated)
            problems = []
            for t in TARGETS:
                problems += diff_trees(
                    os.path.join(tmp, t), os.path.join(REPO, "targets", t)
                )
            # the repo-root marketplace catalog (owner/repo shorthand add) is generated too
            root_mp = os.path.join(REPO, ".claude-plugin", "marketplace.json")
            gen_root = render_marketplace(built, "./targets/claude-code/plugins/")
            committed_root = (
                json.load(open(root_mp)) if os.path.exists(root_mp) else None
            )
            if committed_root != gen_root:
                problems.append(".claude-plugin/marketplace.json (repo root) is stale")
            committed = json.load(open(RESULTS)) if os.path.exists(RESULTS) else {}
            if committed.get("results") != results:
                problems.append("primitives-core-translation-results.json is stale")
            if problems:
                print(
                    f"✗ targets/ drift: {len(problems)} problem(s) — run `make build`"
                )
                for p in problems[:50]:
                    print(f"  - {p}")
                return 1
            print(f"✓ targets/ in sync — {summarize(results)}")
            return 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # in-place build (clean stale, then build recreates dirs + .gitkeep)
    tgt = os.path.join(REPO, "targets")
    for t in TARGETS:
        shutil.rmtree(os.path.join(tgt, t), ignore_errors=True)
    results, built = build(tgt, roster, plugins_meta, caps, cma_model, externals)
    write_results(RESULTS, results)
    write_root_marketplace(REPO, built)
    print(f"✓ built targets/ — {summarize(results)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

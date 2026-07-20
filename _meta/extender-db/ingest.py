"""Populate the extender-db from this repo (idempotent, upsert-by-slug).

    python3 _meta/extender-db/ingest.py

What it loads:
  1. extenders + files   - every roster skill/agent/hook: parsed frontmatter (hooks carry
                           none), entrypoint body, full file inventory with content + sha256.
  2. distributions       - plugins.yaml bundles/plugins + skill-catalog.yaml standalones,
                           with a members relation resolved against the roster.
  3. frontmatter_dimensions - one row per (kind, key): spec-known keys get their
                           requirement level; unknown observed keys land as `custom`.
  4. frameworks + framework_elements - seeded mental models (see FRAMEWORKS below).
  5. assessments         - mechanical checks (assessor `mechanical-v1`) of each skill
                           against the Anthropic Agent Skills spec, each agent against
                           the Claude Code subagent schema, and each hook against the
                           hook-dir-layout framework. Judgment-based assessments
                           (archetype tagging, section taxonomy) are left to humans/agents
                           writing rows with a different `assessor` value.
  6. externals.yaml rows - third-party extenders recorded by reference (origin `external`,
                           no file ingest) so curation queries cover the full curated surface.
"""

import ast
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from check_roster import parse_roster  # noqa: E402
from gen_marketplace import parse_plugins_yaml  # noqa: E402
from pb import PB, esc  # noqa: E402

ROSTER = os.path.join(REPO, "primitives-core.yaml")
PLUGINS_YAML = os.path.join(REPO, "plugins.yaml")
CATALOG = os.path.join(REPO, "skill-catalog.yaml")
EXTERNALS = os.path.join(REPO, "externals.yaml")

LANG_BY_EXT = {
    ".py": "python", ".sh": "shell", ".js": "javascript", ".ts": "typescript",
    ".md": "markdown", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".txt": "text", ".css": "css", ".html": "html",
}

# Spec-known frontmatter keys: (kind, key) -> (requirement, description, framework_slug)
FRONTMATTER_SPEC = {
    ("skill", "name"): ("required", "Skill identifier; lowercase kebab, <=64 chars.", "anthropic-agent-skills"),
    ("skill", "description"): ("required", "What the skill does AND when to use it; the only always-in-context trigger surface (<=1024 chars).", "anthropic-agent-skills"),
    ("skill", "license"): ("optional", "License of the skill content.", "anthropic-agent-skills"),
    ("skill", "allowed-tools"): ("harness", "Claude Code: restricts tools available while the skill is active.", "anthropic-agent-skills"),
    ("agent", "name"): ("required", "Subagent identifier used to dispatch it.", "claude-code-subagents"),
    ("agent", "description"): ("required", "Delegation trigger: tells the main loop when to route work here.", "claude-code-subagents"),
    ("agent", "tools"): ("harness", "Least-privilege tool allowlist for the persona.", "claude-code-subagents"),
    ("agent", "model"): ("harness", "Default model tier the persona dispatches on.", "claude-code-subagents"),
    ("agent", "effort"): ("harness", "Default reasoning effort for the persona.", "claude-code-subagents"),
    ("agent", "maxTurns"): ("harness", "Turn budget cap for one dispatch.", "claude-code-subagents"),
    ("agent", "color"): ("harness", "Display color in the harness UI.", "claude-code-subagents"),
}

FRAMEWORKS = [
    {
        "slug": "anthropic-agent-skills",
        "name": "Anthropic Agent Skills structure",
        "source_org": "Anthropic",
        "source_url": "https://code.claude.com/docs/en/skills",
        "kind": "authoring-spec",
        "applies_to": ["skill"],
        "status": "active",
        "summary": "The published Agent Skills format: a folder with a SKILL.md entrypoint (YAML frontmatter name+description, markdown body) plus optional bundled resources, loaded via three-level progressive disclosure.",
        "elements": [
            ("skill-md-entrypoint", "SKILL.md entrypoint", "component", "The skill is a directory with SKILL.md at its root.", "SKILL.md exists at the folder root."),
            ("frontmatter-name", "name frontmatter", "rule", "Required identifier, lowercase kebab-case.", "frontmatter has `name`, <=64 chars."),
            ("frontmatter-description", "description frontmatter", "rule", "Required; states what the skill does and when to use it (trigger cues, third person). The only part always in context.", "frontmatter has `description`, <=1024 chars."),
            ("progressive-disclosure", "Progressive disclosure", "principle", "Three levels: metadata always in context; SKILL.md body loaded on trigger; bundled files read only as needed.", "Detail is pushed out of SKILL.md into bundled files rather than inlined."),
            ("references-dir", "references/ resources", "component", "Reference documents the agent reads as needed (level 3).", "references/ directory present with files."),
            ("scripts-dir", "scripts/ resources", "component", "Executable helpers for deterministic operations.", "scripts/ directory present with files."),
            ("assets-dir", "assets/ resources", "component", "Templates and files used in the skill's output.", "assets/ directory present with files."),
            ("concise-body", "Concise SKILL.md body", "rule", "Keep the body lean (guideline: under ~500 lines); move depth to references.", "SKILL.md is <=500 lines."),
            ("scripts-over-generation", "Scripts for deterministic work", "principle", "Operations that must be exact ship as scripts instead of freehand generation.", "Deterministic steps (rendering, API calls, transforms) are backed by scripts/."),
        ],
    },
    {
        "slug": "claude-code-subagents",
        "name": "Claude Code subagent schema",
        "source_org": "Anthropic",
        "source_url": "https://code.claude.com/docs/en/sub-agents",
        "kind": "schema-spec",
        "applies_to": ["agent"],
        "status": "active",
        "summary": "The subagent persona format: one markdown file whose frontmatter (name, description, tools, model) configures dispatch and whose body is the persona's system prompt.",
        "elements": [
            ("frontmatter-name", "name frontmatter", "rule", "Required dispatch identifier.", "frontmatter has `name`."),
            ("frontmatter-description", "description frontmatter", "rule", "Required; the delegation trigger the main loop matches against.", "frontmatter has `description`."),
            ("tools-allowlist", "tools allowlist", "dimension", "Least-privilege tool set for the persona.", "frontmatter has `tools`."),
            ("model-tier", "model tier", "dimension", "Persona pinned to a model/effort tier appropriate to its work.", "frontmatter has `model`."),
            ("system-prompt-body", "system-prompt body", "component", "The markdown body is the persona's system prompt.", "non-empty body below the frontmatter."),
            ("single-responsibility", "single responsibility", "principle", "One persona does one job; scope creep splits into a new persona.", "The body describes one coherent role, not several."),
        ],
    },
    {
        "slug": "hsb3-skill-archetypes",
        "name": "hsb3 skill archetypes",
        "source_org": "internal",
        "source_url": "",
        "kind": "archetype-set",
        "applies_to": ["skill"],
        "status": "candidate",
        "summary": "Internal working taxonomy of what a skill fundamentally IS, derived from the shipped catalog. Not mutually exclusive; assess a primary archetype per skill. Candidate status: revise as the catalog grows or if Anthropic publishes a canonical set.",
        "elements": [
            ("workflow-procedure", "Workflow / procedure", "archetype", "Encodes a repeatable multi-step procedure the agent executes end to end (e.g. handoff, private-fork, board-triage).", "Body is dominated by ordered steps/protocol the agent performs."),
            ("domain-expertise", "Domain expertise pack", "archetype", "Teaches the agent a domain, tool, or API it would otherwise guess at (e.g. obsidian-*, opencode-expertise, mermaid).", "Body is dominated by reference knowledge, not procedure."),
            ("deliverable-producer", "Deliverable producer", "archetype", "Produces a recurring artifact to a house standard (e.g. comms, pptx-themes, readme-value-and-proof).", "Output is a named artifact with format/quality rules."),
            ("guardrail-override", "Guardrail / override", "archetype", "Pins defaults or overrides behavior another surface would get wrong (e.g. house palette rules overriding a base skill).", "Body states precedence ('this skill wins') or bans defaults."),
            ("orchestration-delegation", "Orchestration / delegation", "archetype", "Structures how work is split across agents (e.g. foreman).", "Body is about dispatching/verifying other agents."),
            ("scaffold-auditor", "Scaffold / auditor", "archetype", "Stands up or audits repo/project structure against a documented standard (e.g. mise-en-place-scaffold, repo-compliance-audit).", "Body maps a standard onto a repo and creates/checks conformance."),
        ],
    },
    {
        "slug": "skill-section-taxonomy",
        "name": "SKILL.md section taxonomy",
        "source_org": "internal",
        "source_url": "",
        "kind": "section-taxonomy",
        "applies_to": ["skill"],
        "status": "candidate",
        "summary": "The recurring section types observed across SKILL.md bodies; used to analyze composition (which sections a skill carries) and as a checklist when authoring new ones.",
        "elements": [
            ("purpose-overview", "Purpose / overview", "section", "Opening statement of what the skill accomplishes.", "First section states the goal in 1-3 sentences."),
            ("trigger-when-to-use", "Trigger / when to use", "section", "Beyond frontmatter: explicit in-body invocation and skip conditions.", "A section enumerates use/skip cases."),
            ("prerequisites", "Prerequisites", "section", "CLIs, env state, or MCP servers that must exist first.", "A section lists dependencies before the workflow."),
            ("workflow-steps", "Workflow steps", "section", "Ordered procedure the agent follows.", "Numbered or staged steps present."),
            ("reference-pointers", "Reference pointers", "section", "Links into references/ or external docs for depth.", "Body points at bundled or external references."),
            ("examples", "Examples", "section", "Worked input/output or command examples.", "At least one concrete example block."),
            ("anti-patterns", "Anti-patterns / pitfalls", "section", "What NOT to do; known failure modes.", "A pitfalls/anti-pattern/common-mistakes section exists."),
            ("output-format", "Output format contract", "section", "Exact shape of the deliverable the skill produces.", "A section specifies the output's structure."),
            ("integration-partners", "Integration partners", "section", "Co-homed hooks/skills/agents this skill is load-bearing with.", "Body names sibling components and the shared contract."),
        ],
    },
    {
        "slug": "hook-dir-layout",
        "name": "Hook directory layout",
        "source_org": "internal",
        "source_url": "https://github.com/hsb3/dotfiles-agents/blob/dev/scripts/check_hook_layout.py",
        "kind": "schema-spec",
        "applies_to": ["hook"],
        "status": "active",
        "summary": "The ratified hook-dir layout enforced by scripts/check_hook_layout.py: each hook is a directory `hooks/<name>/` whose handler is `hook.py` (legacy flat `.sh` handlers and the old `hooks-handlers/` tree are banned), plus the stdlib-only rule from primitives-core/README.md ('hooks/<name>/ ... Claude-Code-only; stdlib-only (no pip/npm deps)').",
        "elements": [
            ("hook-py-entrypoint", "hook.py entrypoint", "component", "The hook's handler lives at `hook.py` inside its own `<name>/` directory (ratified layout).", "hook.py exists in the hook's directory."),
            ("python-only-handler", "Python-only handler", "rule", "No legacy `.sh` handler — check_hook_layout.py bans `.sh` files anywhere under a hook.", "No `.sh` file present in the hook's file inventory."),
            ("stdlib-only-imports", "stdlib-only imports", "rule", "The handler ships zero third-party dependencies (Python 3 stdlib only) — primitives-core/README.md's hook row.", "hook.py's top-level imports resolve to the Python stdlib only."),
            ("config-present", "config co-located", "component", "Optional `config.json`/`hook.json` sits beside `hook.py` in the same directory.", "config.json or hook.json present in the hook's directory (optional)."),
        ],
    },
    {
        "slug": "dotfiles-agents-roster-schema",
        "name": "dotfiles-agents roster entry schema",
        "source_org": "internal",
        "source_url": "https://github.com/hsb3/dotfiles-agents/blob/dev/primitives-core/README.md",
        "kind": "schema-spec",
        "applies_to": ["skill", "agent", "hook", "mcp"],
        "status": "active",
        "summary": "This repo's manifest schema (primitives-core.yaml): id/type/source/shelf/origin/disposition/targets/plugins/requires, with origin:sourced requiring upstream+ref. Enforced by scripts/check_roster.py.",
        "elements": [
            ("shelf", "shelf", "dimension", "core vs toggle shelving.", "Roster entry carries shelf."),
            ("origin-provenance", "origin provenance", "rule", "authored vs sourced is immutable; sourced requires non-null upstream+ref.", "origin:sourced entries have upstream and ref."),
            ("disposition", "disposition", "dimension", "qualified | grandfathered-pending-use | demoted | untriaged.", "Roster entry carries disposition."),
            ("plugin-membership", "plugin membership", "dimension", "Which bundles ship the primitive (plugins: []).", "Roster entry lists its bundles."),
            ("requires-capabilities", "requires capabilities", "dimension", "Capability words {hooks, local-mcp, hosted-mcp} + cli:/env: dependency declarations.", "Dependencies declared in requires, not prose-only."),
        ],
    },
]


# ---------- parsing helpers ----------

def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].replace('\\"', '"')
    return v


def parse_list(v):
    """'[a, b]' -> ['a','b']; '' / 'null' / '[]' -> []."""
    v = (v or "").strip()
    if v in ("", "null", "[]", "~"):
        return []
    if v.startswith("[") and v.endswith("]"):
        return [unquote(x) for x in v[1:-1].split(",") if x.strip()]
    return [unquote(v)]


def parse_frontmatter(text):
    """Flat `key: value` frontmatter between --- fences. Returns (dict, body).
    Multi-line/nested YAML values are out of scope for the shipped extenders (all flat)."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([\w][\w.-]*):\s*(.*)$", line)
        if km:
            val = unquote(km.group(2))
            if re.fullmatch(r"-?\d+", val):
                val = int(val)
            elif val in ("true", "false"):
                val = val == "true"
            fm[km.group(1)] = val
    return fm, text[m.end():]


def classify_role(relpath, entry_file):
    if relpath == entry_file:
        return "entrypoint"
    top = relpath.split("/")[0]
    base = os.path.basename(relpath)
    if top == "references":
        return "reference"
    if top == "scripts":
        return "script"
    if top == "assets":
        return "asset"
    if top in ("templates",):
        return "template"
    if top in ("evals", "eval"):
        return "eval"
    if base.upper().startswith("LICENSE"):
        return "license"
    if base.lower().endswith((".md", ".txt")):
        return "doc"
    if base.lower().endswith((".json", ".yaml", ".yml", ".toml")):
        return "config"
    return "other"


def scan_files(abs_source, entry_file):
    """Yield dicts for every file under a skill dir (or the single agent file)."""
    out = []
    if os.path.isfile(abs_source):
        paths = [(abs_source, os.path.basename(abs_source))]
    else:
        paths = []
        for root, dirs, names in os.walk(abs_source):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in sorted(names):
                if n.startswith("."):
                    continue
                ap = os.path.join(root, n)
                paths.append((ap, os.path.relpath(ap, abs_source)))
    for ap, rel in sorted(paths, key=lambda t: t[1]):
        raw = open(ap, "rb").read()
        try:
            content = raw.decode("utf-8")
            is_binary = False
        except UnicodeDecodeError:
            content, is_binary = "", True
        out.append({
            "relpath": rel,
            "role": classify_role(rel, entry_file),
            "content": content,
            "is_binary": is_binary,
            "size_bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "language": LANG_BY_EXT.get(os.path.splitext(rel)[1].lower(), ""),
        })
    return out


def parse_catalog_ids(path):
    ids = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^  - id:\s*(\S+)", line)
            if m:
                ids.append(m.group(1))
    return ids


def parse_externals(path):
    """Parse externals.yaml's `externals:` list into dicts. Tailored line parser (see
    parse_roster / parse_plugins_yaml) — no pyyaml, controlled flat-key format only."""
    entries, cur = [], None
    in_list = False
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if re.match(r"^externals:\s*$", line):
            in_list = True
            continue
        if not in_list:
            continue
        if re.match(r"^\S", line):  # a later top-level key ends the list
            in_list = False
            continue
        m = re.match(r"^  - id:\s*(.*)$", line)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {"id": unquote(m.group(1))}
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m and cur is not None:
            cur[m.group(1)] = unquote(m.group(2))
    if cur is not None:
        entries.append(cur)
    return entries


def stdlib_import_violations(source):
    """Return the sorted list of top-level (module-level) import roots in `source` that are
    NOT in the Python 3 stdlib (sys.stdlib_module_names, 3.10+). None if `source` fails to
    parse as Python."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    stdlib = sys.stdlib_module_names
    bad = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in stdlib:
                    bad.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                root = node.module.split(".")[0]
                if root not in stdlib:
                    bad.add(node.module)
    return sorted(bad)


# ---------- ingest passes ----------

def ingest_frameworks(pb):
    fw_ids, el_ids = {}, {}
    for fw in FRAMEWORKS:
        body = {k: fw[k] for k in ("slug", "name", "source_org", "source_url", "kind", "applies_to", "status", "summary")}
        rec, created = pb.upsert("frameworks", f"slug='{esc(fw['slug'])}'", body)
        fw_ids[fw["slug"]] = rec["id"]
        for i, (slug, name, ekind, desc, criteria) in enumerate(fw["elements"]):
            el, _ = pb.upsert(
                "framework_elements",
                f"framework='{rec['id']}' && slug='{esc(slug)}'",
                {"framework": rec["id"], "slug": slug, "name": name,
                 "element_kind": ekind, "description": desc, "criteria": criteria,
                 "sort_order": i},
            )
            el_ids[(fw["slug"], slug)] = el["id"]
        print(f"framework {'created' if created else 'updated'}: {fw['slug']} ({len(fw['elements'])} elements)")
    return fw_ids, el_ids


def ingest_extenders(pb):
    entries = [e for e in parse_roster(ROSTER) if e.get("type") in ("skill", "agent", "hook")]
    ext_ids = {}      # roster id -> record id
    ext_meta = {}     # roster id -> dict used by later passes
    for e in entries:
        kind = e["type"]
        source = e["source"]
        abs_source = os.path.join(REPO, source)
        if kind == "skill":
            entry_file = "SKILL.md"
        elif kind == "hook":
            entry_file = "hook.py"
        else:
            entry_file = os.path.basename(source)
        files = scan_files(abs_source, entry_file)
        entry = next((f for f in files if f["role"] == "entrypoint"), None)
        if kind == "hook":
            # Hooks carry no frontmatter (hook.py is plain Python, not a fenced doc) — the
            # roster summary is the description source instead (see below).
            fm, body = {}, ""
        else:
            fm, body = parse_frontmatter(entry["content"]) if entry else ({}, "")
        upstream = unquote(e.get("upstream", "")) if e.get("upstream", "null") != "null" else ""
        rec, created = pb.upsert("extenders", f"slug='{esc(e['id'])}'", {
            "slug": e["id"],
            "name": str(fm.get("name", e["id"])),
            "kind": kind,
            "description": str(fm.get("description", "")) or unquote(e.get("summary", "")),
            "origin": e.get("origin", ""),
            "upstream": upstream,
            "upstream_ref": unquote(e.get("ref", "")) if e.get("ref", "null") != "null" else "",
            "repo_path": source,
            "shelf": e.get("shelf", ""),
            "disposition": e.get("disposition", ""),
            "requires": parse_list(e.get("requires", "")),
            "frontmatter": fm,
            "body": body,
            "entry_file": entry_file,
            "file_count": len(files),
            "total_bytes": sum(f["size_bytes"] for f in files),
            "word_count": len(body.split()),
        })
        ext_ids[e["id"]] = rec["id"]
        ext_meta[e["id"]] = {
            "kind": kind, "fm": fm, "body": body, "files": files,
            "plugins": parse_list(e.get("plugins", "")), "record": rec,
        }
        # files: upsert current, delete stale
        current = set()
        for f in files:
            pb.upsert("files", f"extender='{rec['id']}' && relpath='{esc(f['relpath'])}'",
                      {**f, "extender": rec["id"]})
            current.add(f["relpath"])
        for stale in pb.list_all("files", f"extender='{rec['id']}'"):
            if stale["relpath"] not in current:
                pb.delete("files", stale["id"])
        print(f"extender {'created' if created else 'updated'}: {kind}/{e['id']} ({len(files)} files)")
    return ext_ids, ext_meta


def ingest_distributions(pb, ext_ids, ext_meta):
    _owner, plugins = parse_plugins_yaml(PLUGINS_YAML)
    for p in plugins:
        members = [ext_ids[rid] for rid, m in ext_meta.items() if p["id"] in m["plugins"]]
        pb.upsert("distributions", f"slug='{esc(p['id'])}'", {
            "slug": p["id"], "kind": p["kind"] if p["kind"] in ("bundle", "plugin") else "plugin",
            "version": p.get("version", ""), "description": p.get("description", ""),
            "members": members,
        })
        print(f"distribution: {p['id']} ({len(members)} members)")
    for sid in parse_catalog_ids(CATALOG):
        if sid not in ext_ids:
            continue
        pb.upsert("distributions", f"slug='{esc(sid)}-standalone'", {
            "slug": f"{sid}-standalone", "kind": "standalone",
            "version": "", "description": f"One-skill standalone install of {sid} (skill-catalog.yaml).",
            "members": [ext_ids[sid]],
        })
        print(f"distribution: {sid}-standalone")


def ingest_externals(pb):
    """externals.yaml -> extenders rows with origin `external` (no file scan, no
    distribution membership — third-party items are recorded by reference only, per
    ADR 0015 / the README expansion path)."""
    n = 0
    for e in parse_externals(EXTERNALS):
        rec, created = pb.upsert("extenders", f"slug='{esc(e['id'])}'", {
            "slug": e["id"],
            "name": e["id"],
            "kind": e.get("kind", ""),
            "description": e.get("provides", ""),
            "origin": "external",
            "upstream": e.get("upstream", ""),
            "upstream_ref": e.get("ref", ""),
            "repo_path": "",
            "shelf": "",
            "disposition": "",
            "requires": [],
            "frontmatter": {},
            "body": "",
            "entry_file": "",
            "file_count": 0,
            "total_bytes": 0,
            "word_count": 0,
        })
        print(f"external {'created' if created else 'updated'}: {e['id']} ({e.get('kind', '')})")
        n += 1
    print(f"externals: {n}")


def ingest_dimensions(pb, ext_meta, fw_ids):
    counts = {}
    for m in ext_meta.values():
        for key in m["fm"]:
            counts[(m["kind"], key)] = counts.get((m["kind"], key), 0) + 1
    keys = set(counts) | set(FRONTMATTER_SPEC)
    for kind, key in sorted(keys):
        req, desc, fw_slug = FRONTMATTER_SPEC.get((kind, key), ("custom", "", None))
        pb.upsert("frontmatter_dimensions",
                  f"key='{esc(key)}' && applies_to='{esc(kind)}'", {
                      "key": key, "applies_to": kind, "requirement": req,
                      "description": desc,
                      "spec_framework": fw_ids.get(fw_slug, "") if fw_slug else "",
                      "observed_count": counts.get((kind, key), 0),
                  })
    print(f"frontmatter dimensions: {len(keys)}")


def assess(pb, ext_rec_id, fw_id, el_id, verdict, evidence):
    pb.upsert(
        "assessments",
        f"extender='{ext_rec_id}' && framework='{fw_id}' && element='{el_id}' && assessor='mechanical-v1'",
        {"extender": ext_rec_id, "framework": fw_id, "element": el_id,
         "verdict": verdict, "evidence": evidence, "assessor": "mechanical-v1"},
    )


def ingest_assessments(pb, ext_ids, ext_meta, fw_ids, el_ids):
    n = 0
    for rid, m in ext_meta.items():
        ext = ext_ids[rid]
        fm, files = m["fm"], m["files"]
        if m["kind"] == "skill":
            fw = fw_ids["anthropic-agent-skills"]
            def el(s):
                return el_ids[("anthropic-agent-skills", s)]
            has_entry = any(f["role"] == "entrypoint" for f in files)
            assess(pb, ext, fw, el("skill-md-entrypoint"),
                   "present" if has_entry else "absent",
                   "SKILL.md at folder root" if has_entry else "no SKILL.md found")
            name = str(fm.get("name", ""))
            assess(pb, ext, fw, el("frontmatter-name"),
                   "present" if name and len(name) <= 64 else ("partial" if name else "absent"),
                   f"name={name!r} ({len(name)} chars)")
            desc = str(fm.get("description", ""))
            assess(pb, ext, fw, el("frontmatter-description"),
                   "present" if desc and len(desc) <= 1024 else ("partial" if desc else "absent"),
                   f"{len(desc)} chars")
            entry = next((f for f in files if f["role"] == "entrypoint"), None)
            lines = entry["content"].count("\n") + 1 if entry else 0
            assess(pb, ext, fw, el("concise-body"),
                   "present" if lines <= 500 else "partial", f"{lines} lines")
            for dirname, slug in (("references", "references-dir"), ("scripts", "scripts-dir"), ("assets", "assets-dir")):
                have = [f for f in files if f["relpath"].startswith(dirname + "/")]
                assess(pb, ext, fw, el(slug),
                       "present" if have else "absent",
                       f"{len(have)} file(s)" if have else "not bundled (optional)")
            n += 7
        elif m["kind"] == "agent":
            fw = fw_ids["claude-code-subagents"]
            def el(s):
                return el_ids[("claude-code-subagents", s)]
            for key, slug in (("name", "frontmatter-name"), ("description", "frontmatter-description"),
                              ("tools", "tools-allowlist"), ("model", "model-tier")):
                assess(pb, ext, fw, el(slug),
                       "present" if fm.get(key) else "absent", f"{key}={fm.get(key)!r}")
            assess(pb, ext, fw, el("system-prompt-body"),
                   "present" if m["body"].strip() else "absent",
                   f"{len(m['body'].split())} words")
            n += 5
        elif m["kind"] == "hook":
            fw = fw_ids["hook-dir-layout"]
            def el(s):
                return el_ids[("hook-dir-layout", s)]
            hook_py = next((f for f in files if f["relpath"] == "hook.py"), None)
            assess(pb, ext, fw, el("hook-py-entrypoint"),
                   "present" if hook_py else "absent",
                   "hook.py in the hook's directory" if hook_py else "no hook.py found")
            shell_files = [f["relpath"] for f in files if f["relpath"].endswith(".sh")]
            assess(pb, ext, fw, el("python-only-handler"),
                   "absent" if shell_files else "present",
                   f"legacy .sh handler(s): {shell_files}" if shell_files else "no .sh handler")
            if hook_py is None:
                assess(pb, ext, fw, el("stdlib-only-imports"), "absent", "no hook.py to scan")
            else:
                violations = stdlib_import_violations(hook_py["content"])
                if violations is None:
                    assess(pb, ext, fw, el("stdlib-only-imports"), "partial", "hook.py did not parse as Python")
                elif violations:
                    assess(pb, ext, fw, el("stdlib-only-imports"), "partial", f"non-stdlib imports: {violations}")
                else:
                    assess(pb, ext, fw, el("stdlib-only-imports"), "present", "all top-level imports are stdlib")
            config_files = [f["relpath"] for f in files if f["relpath"] in ("config.json", "hook.json")]
            assess(pb, ext, fw, el("config-present"),
                   "present" if config_files else "absent",
                   f"{len(config_files)} file(s)" if config_files else "not bundled (optional)")
            n += 4
    print(f"mechanical assessments: {n}")


def main():
    pb = PB()
    fw_ids, el_ids = ingest_frameworks(pb)
    ext_ids, ext_meta = ingest_extenders(pb)
    ingest_distributions(pb, ext_ids, ext_meta)
    ingest_dimensions(pb, ext_meta, fw_ids)
    ingest_assessments(pb, ext_ids, ext_meta, fw_ids, el_ids)
    ingest_externals(pb)
    print("done.")


if __name__ == "__main__":
    main()

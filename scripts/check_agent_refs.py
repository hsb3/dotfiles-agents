#!/usr/bin/env python3
"""Agent-reference gate — no shipped body may route work through an agent that does not exist.

A skill, command, or hook that names a subagent nobody ships fails silently at the worst
moment: the dispatch either resolves to `general-purpose` or errors mid-run, and nothing in
the repo says so. `board-triage` shipped exactly that defect (a `board-analyst` agent that
existed nowhere) until f7a1f3a; the guard that fix left behind covered that one skill by
name, so the same mistake in any other body stayed invisible. This gate is the roster-wide
version.

## What counts as a reference

Precision is the design goal: a gate that fires on prose ("dispatch a scout agent") is worse
than one that only reads references written the way this repo actually writes them. Two
shapes count, and only these two:

  1. **A key with a literal value** — `subagent_type`, `agent_type`, or `agent` followed by
     `:` or `=` and either a QUOTED name, or a bare name that is the whole rest of the line
     (the YAML-frontmatter shape). This is the Task-tool parameter, the hook-stdin field,
     and the command-frontmatter key. The quoting requirement is what separates a literal
     from an expression: `"agent_type": agent_type` and `agent_type = payload.get(...)` are
     code reading the field, and `settle an agent: its delegation row` is prose with a colon
     in it. Neither names an agent; measured against this tree, dropping the requirement
     turned six such lines into false positives.
  2. **A backticked name adjacent to the word agent/subagent** — ``​`scout` agents``,
     ``a `manager` subagent``, ``the agent `reviewer```. Optional `**bold**` wrappers around
     the backticks are read through, because that is how the original `board-analyst` defect
     was written. Adjacency is required: `` `strategist`), which is never a spawned agent ``
     is prose about a role, not a dispatch.

Unbackticked prose is never a reference, in either direction. That is a deliberate recall
sacrifice: an agent named only in running text is not something a reader would mistake for a
wired dispatch either.

## What resolves

A name resolves when, after dropping any `<plugin>:` prefix and case-folding, it is:

  * a **roster agent** — derived, never hardcoded, as the union of `primitives-core/agents/*.md`
    stems and the `type: agent` ids in `primitives-core.yaml`. The union is deliberate: roster
    ↔ disk drift is `make check`'s job, and reporting it here too would give one defect two
    unrelated red gates. `agents/README.md` documents the family rather than being one, the
    same exemption `check_roster.py` applies.
  * a **harness built-in** — an agent the CLI ships rather than this marketplace. Naming one is
    correct, so it is not a violation; see `HARNESS_BUILTINS`.

The `<plugin>:` prefix is dropped because a namespaced dispatch names the same role as its
bare form (`atelier:builder` is `builder`), matching what `worktree-isolation/hook.py`
already does at runtime.

`EXEMPTIONS` is the narrow escape, keyed `(relpath, name)` with a written reason, for a body
that names an agent belonging to some OTHER vocabulary. Each is checked for staleness, so an
exemption cannot outlive the line that justified it.

Run standalone to see every reference the extractor pulls — the tool for auditing the rule
itself rather than trusting it:

    python3 scripts/check_agent_refs.py --report

Stdlib-only, deterministic (sorted output, no clocks, no network). Exit 0 = clean;
exit 1 = a body names something that does not resolve.
Usage: python3 scripts/check_agent_refs.py   (run from the repo root)
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_roster  # noqa: E402  (reuse its tailored roster line parser)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_ROOT = os.path.join(REPO, "primitives-core")
AGENTS_DIR = os.path.join(SCAN_ROOT, "agents")
ROSTER = os.path.join(REPO, "primitives-core.yaml")

# Text surfaces that can carry a dispatch. Schemas, licences, and rendered assets cannot.
SCAN_SUFFIXES = (".md", ".py", ".json", ".yml", ".yaml", ".sh", ".ts", ".js")

# Agents the harness itself ships, so naming one is correct and not this roster's business.
# `explore`, `plan`, `fork` and `general-purpose` are the set this repo's own bodies already
# name as built-in (delegation/references/activation.md and worktree-isolation/hook.py);
# the two `*-setup` agents come with the CLI on the same footing.
HARNESS_BUILTINS = frozenset({
    "general-purpose",
    "explore",
    "plan",
    "fork",
    "statusline-setup",
    "output-style-setup",
})

# Documented false positives, keyed (relpath, lowercased name) with the reason.
#
# The rule reads a reference the way this repo writes one. A body that documents a DIFFERENT
# harness, or that names a role deliberately having no agent file, collides with that by
# coincidence. Enumerating those beats loosening the rule for every body — a narrow exemption
# is auditable, a loose rule is not. `stale_exemptions()` makes each keep earning its place.
EXEMPTIONS = {
    ("primitives-core/skills/opencode-expertise/references/extension-surfaces.md", "build"): (
        "opencode command frontmatter (`agent: build`) — opencode's own primary agent, "
        "documented as that harness's surface, not a dispatch of this roster"
    ),
    ("primitives-core/skills/delegation/SKILL.md", "strategist"): (
        "the role noun for the session itself; that same line says outright there is no "
        "`strategist` agent file here, so the reference is the absence, not a dispatch"
    ),
}

_NAME = r"(?:(?P<ns>[A-Za-z0-9_-]+):)?(?P<name>[A-Za-z][A-Za-z0-9_-]*)"
_BACKTICKED = r"`" + _NAME + r"`"

_KEYS = r"(?:subagent_type|agent_type|agent)"
# 1a. key with a QUOTED value: "subagent_type": "x" / subagent_type='x' / `agent_type`:"x".
#     The quotes are what separate a literal from an expression: `"agent_type": agent_type`
#     and `agent_type = payload.get(...)` are code reading the field, not naming an agent.
KEY_QUOTED = re.compile(
    r"(?<![\w-])[\"'`]?" + _KEYS + r"[\"'`]?\s*[:=]\s*(?P<q>[\"'`])" + _NAME + r"(?P=q)"
)
# 1b. YAML frontmatter, where a scalar is bare — but then the key/value IS the whole line,
#     which prose colons ("Two kinds of row settle an agent: its delegation row") are not.
KEY_YAML = re.compile(r"^\s*" + _KEYS + r":[ \t]+" + _NAME + r"[ \t]*$")
# 2a. `name` agent   2b. agent `name`
BACKTICK_BEFORE = re.compile(_BACKTICKED + r"\*{0,2}\s+(?:sub)?agents?(?![\w-])")
BACKTICK_AFTER = re.compile(r"(?<![\w-])(?:sub)?agents?\s+" + _BACKTICKED)

RULES = (
    ("key", KEY_QUOTED),
    ("key", KEY_YAML),
    ("backticked", BACKTICK_BEFORE),
    ("backticked", BACKTICK_AFTER),
)


class Ref(object):
    """One extracted agent reference: where it is, what it names, which rule saw it."""

    __slots__ = ("rel", "lineno", "name", "rule", "line")

    def __init__(self, rel, lineno, name, rule, line):
        self.rel = rel
        self.lineno = lineno
        self.name = name
        self.rule = rule
        self.line = line

    @property
    def key(self):
        return (self.rel, self.name.lower())

    def __repr__(self):
        return "Ref(%s:%d, %s)" % (self.rel, self.lineno, self.name)


def references(text, rel):
    """Every agent reference in `text`, sorted by (line, name). `rel` labels the source."""
    found = {}
    for lineno, line in enumerate(text.splitlines(), 1):
        for rule, pattern in RULES:
            for m in pattern.finditer(line):
                name = m.group("name")
                found.setdefault((lineno, name.lower()), Ref(rel, lineno, name, rule, line.strip()))
    return [found[k] for k in sorted(found)]


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _scan_files(root):
    """Every scannable file under `root`, sorted, deterministic."""
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.startswith("."))
        for name in sorted(files):
            if name.endswith(SCAN_SUFFIXES):
                yield os.path.join(dirpath, name)


def scan(root=SCAN_ROOT, rel_base=REPO):
    """Every reference under `root`, as a flat sorted list."""
    out = []
    for path in _scan_files(root):
        rel = os.path.relpath(path, rel_base)
        out.extend(references(_read(path), rel))
    return out


def disk_agents():
    """Agent ids from `primitives-core/agents/*.md`. README documents the family, not an agent."""
    if not os.path.isdir(AGENTS_DIR):
        return set()
    return {
        f[:-3].lower() for f in os.listdir(AGENTS_DIR)
        if f.endswith(".md") and f.lower() != "readme.md"
    }


def manifest_agents():
    """Agent ids declared `type: agent` in the roster."""
    if not os.path.isfile(ROSTER):
        return set()
    return {
        e["id"].lower() for e in check_roster.parse_roster(ROSTER)
        if e.get("type") == "agent" and e.get("id")
    }


def roster_agents():
    """The set of agent ids that exist, derived from disk and the roster (never hardcoded)."""
    return disk_agents() | manifest_agents()


def check_tree(root, rel_base, agents):
    """Violations under `root`: references naming something outside `agents` or the built-ins."""
    resolvable = set(agents) | HARNESS_BUILTINS
    problems = []
    for ref in scan(root, rel_base):
        name = ref.name.lower()
        if name in resolvable or ref.key in EXEMPTIONS:
            continue
        problems.append(
            "%s:%d: names agent `%s`, which is no roster agent and no harness built-in "
            "— in: %s" % (ref.rel, ref.lineno, ref.name, ref.line)
        )
    return sorted(set(problems))


def stale_exemptions():
    """Exemptions that suppress nothing any more — a hole nobody remembers opening."""
    out = []
    live = {r.key for r in scan()}
    for (rel, name) in sorted(EXEMPTIONS):
        if (rel, name) not in live:
            out.append(
                "EXEMPTIONS[%r, %r]: stale — no such reference in the tree; remove it" % (rel, name)
            )
    return out


def problems():
    return sorted(set(check_tree(SCAN_ROOT, REPO, roster_agents()) + stale_exemptions()))


def report(root, rel_base, agents):
    refs = scan(root, rel_base)
    print("roster agents: %s" % ", ".join(sorted(agents)))
    print("harness built-ins: %s" % ", ".join(sorted(HARNESS_BUILTINS)))
    print("")
    print("%-16s %-12s %-9s %s" % ("name", "resolves", "rule", "site"))
    for ref in sorted(refs, key=lambda r: (r.name.lower(), r.rel, r.lineno)):
        name = ref.name.lower()
        if ref.key in EXEMPTIONS:
            verdict = "exempt"
        elif name in agents:
            verdict = "roster"
        elif name in HARNESS_BUILTINS:
            verdict = "built-in"
        else:
            verdict = "DANGLING"
        print("%-16s %-12s %-9s %s:%d" % (ref.name, verdict, ref.rule, ref.rel, ref.lineno))
    print("")
    print("%d reference(s) over %d distinct name(s)"
          % (len(refs), len({r.name.lower() for r in refs})))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="check_agent_refs.py",
        description="No shipped body names an agent that does not exist.",
    )
    parser.add_argument("--root", default=SCAN_ROOT, help="tree to scan (default: primitives-core/)")
    parser.add_argument("--report", action="store_true", help="print every extracted reference")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    # Report paths relative to the tree's root, so a fixture tree named `primitives-core/`
    # yields the same repo-shaped relpaths `EXEMPTIONS` is keyed by.
    rel_base = os.path.dirname(root) if os.path.basename(root) == "primitives-core" else root
    agents = roster_agents()

    if args.report:
        return report(root, rel_base, agents)

    probs = check_tree(root, rel_base, agents)
    if root == SCAN_ROOT:
        probs = sorted(set(probs + stale_exemptions()))
    if probs:
        print("✗ agent-refs: %d dangling agent reference(s)" % len(probs), file=sys.stderr)
        for p in probs:
            print("  - %s" % p, file=sys.stderr)
        return 1
    print("✓ agent-refs clean — every named agent resolves to a roster agent or a harness built-in")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Membership gate for the `solo-skills` aggregate.

`solo-skills` exists to carry every skill that stands on its own, so its membership is
not a curatorial choice — it is a derivable set, and this gate derives it. A skill
stands on its own when it needs no sibling skill, no agent, and no hook to function.
That is a property of the SKILL, not of how it happens to be packaged.

**Eligibility cannot be read from metadata.** None of the ineligible skills is caught by
the roster's `requires:` field, and two express the dependency as a hardcoded relative
path built inside a bundled Python script (`mise-en-place-scaffold/scripts/scaffold.py`
and `repo-compliance-audit/scripts/audit.py` both do `os.path.join("skills", ...)`,
which never forms the literal substring `skills/<id>`). So this gate reads bodies and
scripts, and it reads them differently because the two carry dependencies differently:

  1. **Sibling path in prose** — `skills/<other-id>` or a `[[other-id]]` wikilink inside
     `SKILL.md`, `references/`, or `examples/*.md`. A path is a dependency; a prose
     mention of another skill by name is not, so only path- and wikilink-shaped
     references count here. `examples/*.md` (a playbook, a worked write-up) is prose the
     same way `references/` is — comms' own advisor-board playbook says "Invoke the
     `presentations` skill for palette..." as authoring guidance, not a requirement the
     worked example needs to run, exactly the conversational case this rule is built to
     let through.
  2. **Sibling id in bundled code** — any other skill's id appearing anywhere under
     `scripts/` or `examples/`, in a file with a source extension (`.md` is not one — see
     `CODE_SUFFIXES`). Code does not mention skills conversationally, so an id in a
     script is a dependency even when it never forms a literal path. `examples/` counts
     because a bundled sample is code a consumer runs: `comms`' advisor-board sample
     once required `~/.claude/skills/presentations/...` for its palette, so the sample was
     broken on any install without that sibling while the skill shipped solo (it now
     reads its own theme tokens instead, and the code rule catches a regression).
  3. **Named-agent dispatch** — a roster agent id in backticks. A skill that dispatches
     this repo's agents cannot run without them.
  4. **Hook coupling in bundled code** — a `primitives-core/hooks/` directory name
     appearing in the skill's code. `activation/scripts/activation.py` resolves
     `os.path.join(root, n, "hook.py")` over its `HOOK_NAMES`, so the literal
     `hooks/<name>` never forms and only the id is visible — the same shape rule 2
     exists for. Prose naming a hook is documentation and does not count.

**A string match is EVIDENCE of coupling, not the definition of it.** The definition is a
real runtime dependency: the skill does not function without the other primitive. No
static scan can decide that, so every rule above reads a textual signal and the gate takes
the conservative reading — a match excludes the skill from `solo-skills`. That trades false
exclusions for false inclusions deliberately: a wrongly-excluded skill is one bundle short
and visible in `--report`, while a wrongly-included one ships broken to every consumer.
Rules 1 and 3 narrow the signal at the point where prose is genuinely conversational
(path- and wikilink-shaped only; backticked agent ids only); rules 2 and 4 do not, because
code does not mention siblings conversationally. A match that is provably not a dependency
is retired through a named, audited exemption, never by loosening the rule.

Two known blind spots, recorded so nobody re-derives them:

  * **Rule 2 scans only `CODE_SUFFIXES`**, so a bundled `examples/` asset with any other
    extension is never scanned — a sample `Makefile`, `Dockerfile`, `.toml`, `.yaml`,
    `.sql`, or an extensionless script naming a sibling skill passes this gate unseen.
    Widening the scan is a separate decision (`.md` and `.json` are excluded on purpose,
    for the reason stated at `CODE_SUFFIXES`, and a wider net changes eligibility for
    live skills), so this is a statement of the boundary, not a TODO.
  * **A bare backticked skill name in prose is invisible to rule 1 BY DESIGN** — only
    `skills/<id>` paths and `[[wikilinks]]` count, because a prose mention is not a
    dependency and this gate's question is whether a skill can stand alone. The
    consequence for a DIFFERENT question — whether a bundle ships everything its own
    bodies point at — is owned by `scripts/check_skill_refs.py`, which reads exactly that
    backticked form. Neither gate is the other's fallback.

The gate is bidirectional:

  - an ineligible skill inside `solo-skills` is red (membership must not drift in), and
  - a standalone-capable skill with NO topical plugin, outside `solo-skills`, is red
    (membership must not silently fall behind).

The second direction narrowed on 2026-09-08 (decision-020): the topical plugin owns a
skill, and `solo-skills` is the home for skills with no topical plugin. "Has a topical
plugin" is DERIVED from the symlink assemblies — any `plugins/<id>/skills/<skill>` where
`<id>` is not `solo-skills` — never from a hand-maintained list, so a skill acquires or
loses its topical home the moment the assembly changes.

The narrowing is PERMISSIVE and stays that way: this gate does not force a dual-homed
skill out of `solo-skills`, and one that stayed would still be green. Nothing is dual-homed
with it any more, though — the ruling was swept across the remaining eighteen on 2026-09-08
(kata `8tw0`), so a skill a topical plugin owns ships only from that plugin and
`solo-skills` is exactly the skills with nowhere topical to live. The permissiveness now
describes what this gate REFUSES to decide, not a population it tolerates.

**One skill has TWO topical homes, by deliberate exception** (owner ruling 2026-09-08):
`project-memory` is owned topically by `code-desk` and shipped mechanically by
`mise-en-place`, whose `audit.py` and `scaffold.py` both load
`skills/project-memory/references/checklist.md` off their own plugin root and abort without
it. Exactly-one-home is the rule and this is the recorded exception to it; either way the
skill is not a `solo-skills` member, so this gate reads it as topically homed like any
other.

What survives is the case the direction exists for — a skill nothing else ships being
quietly left out of the everything-bundle.

One narrow escape exists: `SYSTEM_EXEMPTIONS`, for a skill that is standalone-CAPABLE
(no sibling, agent, or hook need) but prescribes a system the consumer must opt into
deliberately — either an in-repo system this marketplace defines, or an external one (a
daemon, an app, a toolchain) they have to stand up and choose. What is prescribed is
still a property of the skill; shipping it in the everything-bundle would push that
system's conventions on every install. Each entry names its reason and the plugin that
carries the skill instead (owner ruling 2026-09-01, the code-desk split; widened to
external systems by owner ruling 2026-09-07). An exempted skill found INSIDE solo-skills
is red — the exemption and the membership contradict each other.

Run standalone for a full report on every skill, which is the tool for answering "is this
new skill standalone-capable?":

    python3 scripts/check_solo_skills.py --report
"""

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO, "primitives-core", "skills")
AGENTS_DIR = os.path.join(REPO, "primitives-core", "agents")
HOOKS_DIR = os.path.join(REPO, "primitives-core", "hooks")
SOLO_SKILLS_DIR = os.path.join(REPO, "plugins", "solo-skills", "skills")
PLUGINS_DIR = os.path.join(REPO, "plugins")

PROSE_NAMES = ("SKILL.md",)
PROSE_DIRS = ("references", "examples")
CODE_DIRS = ("scripts", "examples")

# Text extensions worth scanning inside the code dirs — a dependency lives in source,
# not in a compiled artifact or a binary asset. Sample DATA (`.json`, `.md`) is excluded
# by the same reasoning: it imports nothing.
CODE_SUFFIXES = (".py", ".sh", ".bash", ".zsh", ".js", ".ts", ".rb", ".pl")

# Documented false positives for the agent rule, keyed (skill_id, agent_id).
#
# The agent rule is deliberately blunt: a backticked roster-agent id in prose counts as
# a dispatch, because that is exactly what a dispatch looks like in this repo's own
# skills. A skill that documents a DIFFERENT harness will collide with that by
# coincidence. Those cases are enumerated here, with the reason, rather than weakening
# the rule for every skill — a narrow exemption someone can audit beats a loose rule
# nobody can.
#
# Exemptions are themselves checked: one that no longer matches anything is reported as
# stale, so this list cannot quietly outlive the line that justified it.
AGENT_EXEMPTIONS = {
    ("opencode-expertise", "scout"): (
        "documents opencode's own built-in subagent named `scout`, listed beside "
        "`build`/`plan`/`general`/`explore`; not a dispatch of this repo's scout"
    ),
}

# Standalone-capable skills deliberately kept OUT of solo-skills: each prescribes an
# opt-in system, in-repo or external (owner ruling 2026-09-01 — the code-desk split;
# widened to external systems 2026-09-07). Keyed by skill id, value names the reason and
# the plugin that carries the skill instead.
SYSTEM_EXEMPTIONS = {
    "bun": (
        "makes bun the default JS/TS runtime, package manager, test runner and bundler — "
        "a toolchain policy a consumer adopts per repo, shipped only by the bun plugin"
    ),
    "kenn-forge": (
        "drives a kenn-forge daemon the consumer must have running on their own machine — "
        "an opt-in external system, shipped only by the kenn-forge plugin"
    ),
    "planning-desk": (
        "stands up a _meta/plans/ desk in the consuming repo, read through a tracker "
        "adapter — an opt-in planning system, shipped only by the mise-en-place plugin"
    ),
    "repo-meta-structure": (
        "defines the _meta/ directory standard the mise-en-place system enforces — "
        "opt-in prescriptions, shipped only by the mise-en-place plugin"
    ),
}


def _skill_ids():
    if not os.path.isdir(SKILLS_DIR):
        return []
    return sorted(
        d for d in os.listdir(SKILLS_DIR)
        if os.path.isdir(os.path.join(SKILLS_DIR, d)) and not d.startswith(".")
    )


def _agent_ids():
    if not os.path.isdir(AGENTS_DIR):
        return []
    return sorted(
        f[:-3] for f in os.listdir(AGENTS_DIR)
        if f.endswith(".md") and not f.startswith(".")
    )


def _hook_ids():
    if not os.path.isdir(HOOKS_DIR):
        return []
    return sorted(
        d for d in os.listdir(HOOKS_DIR)
        if os.path.isdir(os.path.join(HOOKS_DIR, d)) and not d.startswith((".", "_"))
    )


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def _prose_files(sdir):
    for name in PROSE_NAMES:
        p = os.path.join(sdir, name)
        if os.path.isfile(p):
            yield p
    for sub in PROSE_DIRS:
        d = os.path.join(sdir, sub)
        if not os.path.isdir(d):
            continue
        for root, _dirs, files in os.walk(d):
            for f in sorted(files):
                if f.endswith(".md"):
                    yield os.path.join(root, f)


def _code_files(sdir):
    for sub in CODE_DIRS:
        d = os.path.join(sdir, sub)
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in sorted(files):
                if f.endswith(CODE_SUFFIXES):
                    yield os.path.join(root, f)


def _rel(path):
    return os.path.relpath(path, REPO)


def dependencies(skill_id, skill_ids, agent_ids, hook_ids=()):
    """Return a list of human-readable dependency findings for one skill."""
    sdir = os.path.join(SKILLS_DIR, skill_id)
    siblings = [s for s in skill_ids if s != skill_id]
    found = []

    # 1. Sibling path or wikilink in prose.
    for path in _prose_files(sdir):
        text = _read(path)
        for sib in siblings:
            for pat, kind in (
                (rf"skills/{re.escape(sib)}(?![\w-])", "path"),
                (rf"\[\[{re.escape(sib)}\]\]", "wikilink"),
            ):
                m = re.search(pat, text)
                if m:
                    line = text.count("\n", 0, m.start()) + 1
                    found.append(
                        f"references sibling skill `{sib}` by {kind} "
                        f"at {_rel(path)}:{line}"
                    )
                    break

    # 2 and 4, over one pass of the bundled code: a sibling skill's id, and a hook id.
    for path in _code_files(sdir):
        text = _read(path)
        for sib in siblings:
            m = re.search(rf"(?<![\w-]){re.escape(sib)}(?![\w-])", text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                found.append(
                    f"bundled script names sibling skill `{sib}` "
                    f"at {_rel(path)}:{line}"
                )
        for hook in hook_ids:
            m = re.search(rf"(?<![\w-]){re.escape(hook)}(?![\w-])", text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                found.append(
                    f"bundled script resolves hook `{hook}` at {_rel(path)}:{line}"
                )

    # 3. Named-agent dispatch in prose. An optional `<plugin>:` prefix is allowed so the
    # namespaced form (`atelier:manager`) is caught alongside the bare one.
    for path in _prose_files(sdir):
        text = _read(path)
        for agent in agent_ids:
            if (skill_id, agent) in AGENT_EXEMPTIONS:
                continue
            m = re.search(rf"`(?:[\w-]+:)?{re.escape(agent)}`", text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                found.append(
                    f"dispatches agent `{agent}` at {_rel(path)}:{line}"
                )

    return sorted(set(found))


def stale_exemptions(skill_ids, agent_ids):
    """Report exemptions that no longer suppress anything — an exemption must keep earning
    its place, or it becomes a permanent hole nobody remembers opening."""
    out = []
    for skill_id in sorted(SYSTEM_EXEMPTIONS):
        if skill_id not in skill_ids:
            out.append(
                f"SYSTEM_EXEMPTIONS[{skill_id!r}]: no such skill — remove it"
            )
    for (skill_id, agent) in sorted(AGENT_EXEMPTIONS):
        if skill_id not in skill_ids:
            out.append(
                f"AGENT_EXEMPTIONS[{skill_id!r}, {agent!r}]: no such skill — remove it"
            )
            continue
        if agent not in agent_ids:
            out.append(
                f"AGENT_EXEMPTIONS[{skill_id!r}, {agent!r}]: no such agent — remove it"
            )
            continue
        sdir = os.path.join(SKILLS_DIR, skill_id)
        hit = any(
            re.search(rf"`(?:[\w-]+:)?{re.escape(agent)}`", _read(p))
            for p in _prose_files(sdir)
        )
        if not hit:
            out.append(
                f"AGENT_EXEMPTIONS[{skill_id!r}, {agent!r}]: stale — the skill no longer "
                "mentions that agent, so the exemption suppresses nothing; remove it"
            )
    return out


def _topical_homes():
    """Skill ids shipped by some plugin OTHER than solo-skills (decision-020)."""
    out = set()
    if not os.path.isdir(PLUGINS_DIR):
        return out
    for plugin in sorted(os.listdir(PLUGINS_DIR)):
        if plugin == "solo-skills" or plugin.startswith("."):
            continue
        d = os.path.join(PLUGINS_DIR, plugin, "skills")
        if os.path.isdir(d):
            out.update(x for x in os.listdir(d) if not x.startswith("."))
    return out


def _members():
    if not os.path.isdir(SOLO_SKILLS_DIR):
        return None
    return sorted(
        d for d in os.listdir(SOLO_SKILLS_DIR) if not d.startswith(".")
    )


def problems():
    skill_ids = _skill_ids()
    agent_ids = _agent_ids()
    hook_ids = _hook_ids()
    members = _members()
    topical = _topical_homes()
    if members is None:
        return ["plugins/solo-skills/skills/: missing — the solo-skills assembly has no skills directory"]

    out = list(stale_exemptions(skill_ids, agent_ids))
    eligible = []
    for sid in skill_ids:
        deps = dependencies(sid, skill_ids, agent_ids, hook_ids)
        if not deps:
            eligible.append(sid)
        elif sid in members:
            detail = "; ".join(deps)
            out.append(
                f"plugins/solo-skills/skills/{sid}: not standalone-capable — {detail}"
            )

    for sid in eligible:
        if sid in SYSTEM_EXEMPTIONS:
            if sid in members:
                out.append(
                    f"plugins/solo-skills/skills/{sid}: present but SYSTEM_EXEMPTIONS "
                    f"excludes it ({SYSTEM_EXEMPTIONS[sid]}) — remove the symlink or "
                    "the exemption"
                )
            continue
        if sid not in members and sid not in topical:
            out.append(
                f"primitives-core/skills/{sid}: standalone-capable but absent from "
                "solo-skills — the plugin claims every such skill with no topical "
                "plugin; add the symlink, give it a topical plugin, or give the skill "
                "a real dependency"
            )

    for sid in members:
        if sid not in skill_ids:
            out.append(
                f"plugins/solo-skills/skills/{sid}: no such skill in primitives-core"
            )

    return out


def report():
    skill_ids = _skill_ids()
    agent_ids = _agent_ids()
    hook_ids = _hook_ids()
    eligible, blocked = [], []
    for sid in skill_ids:
        deps = dependencies(sid, skill_ids, agent_ids, hook_ids)
        (eligible if not deps else blocked).append((sid, deps))
    print(f"standalone-capable ({len(eligible)}):")
    for sid, _ in eligible:
        print(f"  {sid}")
    print(f"\nnot standalone-capable ({len(blocked)}):")
    for sid, deps in blocked:
        print(f"  {sid}")
        for d in deps:
            print(f"      {d}")
    return 0


def main():
    if "--report" in sys.argv:
        return report()
    probs = problems()
    if probs:
        print("✗ solo-skills membership drift:", file=sys.stderr)
        for p in probs:
            print(f"  - {p}", file=sys.stderr)
        return 1
    members = _members() or []
    print(
        f"✓ solo-skills membership clean — {len(members)} skills, each verified "
        "standalone-capable (no sibling path, no sibling id in bundled code, no agent "
        "dispatch, no hook resolved from bundled code); every standalone-capable skill "
        "is a member, has a topical plugin, or is system-exempted "
        f"({len(SYSTEM_EXEMPTIONS)} exempted)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

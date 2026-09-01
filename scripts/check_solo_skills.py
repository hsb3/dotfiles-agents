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
     `SKILL.md` or `references/`. A path is a dependency; a prose mention of another
     skill by name is not, so only path- and wikilink-shaped references count here.
  2. **Sibling id in bundled code** — any other skill's id appearing anywhere under
     `scripts/`. Code does not mention skills conversationally, so an id in a script is
     a dependency even when it never forms a literal path.
  3. **Named-agent dispatch** — a roster agent id in backticks. A skill that dispatches
     this repo's agents cannot run without them.

The gate is bidirectional, because the plugin's own description promises *every*
standalone-capable skill:

  - an ineligible skill inside `solo-skills` is red (membership must not drift in), and
  - an eligible skill outside it is red (membership must not silently fall behind).

The second direction is what keeps the catalog's claim honest as skills are added. A new
skill that genuinely should not ship solo must earn that by carrying a real dependency,
not by being quietly left out.

One narrow escape exists: `SYSTEM_EXEMPTIONS`, for a skill that is standalone-CAPABLE
(no sibling, agent, or hook need) but prescribes an opt-in in-repo system a consumer
must choose deliberately — shipping it in the everything-bundle would push that system's
conventions on every install. Each entry names its reason and the plugin that carries the
skill instead (owner ruling 2026-09-01, the code-desk split). An exempted skill found
INSIDE solo-skills is red — the exemption and the membership contradict each other.

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
SOLO_SKILLS_DIR = os.path.join(REPO, "plugins", "solo-skills", "skills")

PROSE_NAMES = ("SKILL.md",)
PROSE_DIRS = ("references",)
CODE_DIRS = ("scripts",)

# Text extensions worth scanning inside scripts/ — a dependency lives in source, not in
# a compiled artifact or a binary asset.
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
# opt-in in-repo system (owner ruling 2026-09-01 — the code-desk split). Keyed by skill
# id, value names the reason and the plugin that carries the skill instead.
SYSTEM_EXEMPTIONS = {
    "planning-desk": (
        "stands up a GitHub-issue-backed _meta/plans/ desk in the consuming repo — an "
        "opt-in planning system, shipped only by the mise-en-place plugin"
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


def dependencies(skill_id, skill_ids, agent_ids):
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

    # 2. Sibling id anywhere in bundled code.
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


def _members():
    if not os.path.isdir(SOLO_SKILLS_DIR):
        return None
    return sorted(
        d for d in os.listdir(SOLO_SKILLS_DIR) if not d.startswith(".")
    )


def problems():
    skill_ids = _skill_ids()
    agent_ids = _agent_ids()
    members = _members()
    if members is None:
        return ["plugins/solo-skills/skills/: missing — the solo-skills assembly has no skills directory"]

    out = list(stale_exemptions(skill_ids, agent_ids))
    eligible = []
    for sid in skill_ids:
        deps = dependencies(sid, skill_ids, agent_ids)
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
        if sid not in members:
            out.append(
                f"primitives-core/skills/{sid}: standalone-capable but absent from "
                "solo-skills — the plugin claims every such skill; add the symlink or "
                "give the skill a real dependency"
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
    eligible, blocked = [], []
    for sid in skill_ids:
        deps = dependencies(sid, skill_ids, agent_ids)
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
        "dispatch); every standalone-capable skill is a member or system-exempted "
        f"({len(SYSTEM_EXEMPTIONS)} exempted)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

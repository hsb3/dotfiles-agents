#!/usr/bin/env python3
"""Cross-bundle skill-citation gate — a shipped body may not point at a skill the reader
does not have.

A skill body that names a sibling skill is making a promise about the consumer's install.
That promise is only true inside a bundle that ships both. `layer-cycle` cites
`test-quality`; `layer-cycle` ships from `atelier` and `solo-skills`, `test-quality` ships
from `solo-skills` only, so every atelier consumer read a pointer into a skill they do not
have. Nothing was red: `check_agent_refs.py` resolves agent names, `check_symlinks.py`
proves links resolve rather than that a bundle is coherent, and the README/catalog gates
say nothing about body content. `check_solo_skills.py` reads sibling skill names but
matches only `skills/<id>` paths and `[[wikilinks]]` — a bare backticked name is invisible
to it BY DESIGN, and that design is right for the question that gate asks (is this skill
standalone-capable), so the blind spot is not a bug in it. It is exactly the citation form
this repo's own style pushes authors toward, which is what this gate reads.

## The rule

A **citation** is a roster skill id in backticks — `` `dataviz` ``, optionally namespaced
`` `diagrams:dataviz` ``, or in the path form `` `skills/dataviz/references/x.md` `` —
inside another skill's `SKILL.md`, `references/**/*.md`, or `examples/**/*.md` (the surface
`check_solo_skills.py` calls prose). It is a violation when some plugin assembly ships the
citing skill and not the cited one.

Backticks are load-bearing and are the whole rule for "is this a reference". A bare
unquoted name cannot be: roster ids include `handoff`, `waves`, `comms` and `diagrams`,
which are ordinary English, and the false-positive rate of an unquoted rule is total.

The **path form is the sharpest case, not an afterthought**: `skills/<id>/...` is how a
bundled script's own documentation names a sibling's asset, so the file is only there if
the bundle ships the sibling — a hard runtime dependency rather than a pointer. Both live
subjects are exactly that (`repo-compliance-audit`'s `audit.py` aborts on a mise-en-place
root), and the gate's first draft missed them by reading only the bare id, while catching
the mirror direction of the same relationship because that one happened to be written
without a path. The English-word objection above does not apply once `skills/` prefixes the
id, so nothing is traded for the widening.

**Dependency vs mention: there is no honest static rule, so this gate takes the
conservative reading.** "Go and use `x`" is a dependency and "see also `x`" is not, but the
difference lives in the verb and the surrounding intent, not in any shape a regex can hold
— and the two are written identically often enough that a rule keyed on imperative verbs
would both miss dependencies and invent them. So a backticked cross-bundle citation is red,
following `check_solo_skills.py`'s own precedent: *a string match is EVIDENCE of coupling,
not the definition of it*, and the conservative reading trades a false red (visible,
audited, one line to exempt) for a false green (a pointer that dead-ends in a consumer's
install, invisible forever). What the gate actually asserts is narrower and defensible on
its own: **a bundle should not print a pointer its own consumer cannot follow**, whether or
not the pointer is load-bearing.

Membership is DERIVED — roster ids for the vocabulary (`type: skill` in
`primitives-core.yaml`), `plugins/<id>/skills/` for who ships what. Never a hand list;
adding or dropping a symlink changes this gate's verdict the moment it lands.

## Limitations, stated rather than papered over

  * **`README.md` is not scanned**, matching `check_solo_skills.py`'s prose surface. Unit
    READMEs are catalog copy about the unit, read next to the other READMEs rather than
    followed as instructions, and they routinely name siblings for orientation —
    `layer-cycle`'s README names `test-quality` to this day. Widening to READMEs is a
    separate decision with its own exemption backlog.
  * **Only skill bodies cite.** A hook, command, or agent naming a skill is not read here;
    those are not shipped per-bundle the same way and had no subjects when this landed.
  * **A skill in no assembly is never a subject** — with no bundle there is no consumer
    whose install could be wrong.
  * **The path form is matched only at the `skills/` prefix**, not through a deeper one
    (`` `${CLAUDE_PLUGIN_ROOT}/skills/<id>/...` ``, `` `.claude/skills/<id>/...` ``).
    Measured across the tree, every such site is either a self-reference or an
    illustrative placeholder that is not a roster id, so widening buys no subject today
    and would start reading example paths as citations.
  * **The gate holds nothing red on the tree it landed in** — every cross-bundle pair is
    exempted or amnestied, so a green run proves no regression, not an empty problem.
    `docs/gotchas.md` asks a deliberate forward-guard to say so; this is that sentence. It
    is not a guard without subjects, though: run against `faa3209` it is red in eight
    places, and the two path-form pairs it now amnesties were live defects when found.

## Exemptions

`EXEMPTIONS` is the narrow escape, following `check_solo_skills.py`'s `SYSTEM_EXEMPTIONS`
shape rather than inventing a second convention: keyed by the `(citing, cited)` pair, with
a written reason. It carries one extra field those tables do not need — an **anchor**, a
literal string that must still appear in the citing skill's scanned prose for the exemption
to hold.

The anchor is what stops a pair-keyed exemption from certifying prose it never read. The
defect that motivated this gate was `layer-cycle` telling the reader to route THROUGH
`test-quality` ("red observed to the `test-quality` bar"), and the fix inlined the substance
so the pointer degraded to a convenience ("red observed against the unfixed code, red again
when the fix is reverted. Fuller bar in `test-quality`."). A bare-pair exemption would
declare both states fine — including the broken one, so the gate as shipped would not have
caught the defect it exists for. Anchoring the exemption to the sentence that JUSTIFIES it
means the exemption self-invalidates the moment that sentence changes, and it is inactive
against any earlier state of the prose where the sentence did not exist yet. Verified: run
this gate against `faa3209` and `layer-cycle` → `test-quality` is red.

The anchor is matched anywhere in the citing skill's scanned prose, not per-file, because
the judgment an entry records is about the skill's relationship to the sibling and the
justifying sentence does not always sit in the file that cites. The cost is that one anchor
covers every citation site of that pair within that skill; the guard that matters — a
rewritten or deleted anchor kills the exemption — is unaffected.

Exemptions are themselves checked: an entry naming a skill that does not exist, or one
whose pair produces no cross-bundle citation at all, is reported as stale, so this table
cannot quietly outlive the line that justified it. So is the anchor's SUBSTANCE, because
the safety property above rests entirely on it and nothing else constrains what an author
types: an anchor must be at least `ANCHOR_MIN_CHARS` (20) characters and must not be part
of either skill id. Twenty is a floor, not a target — below it an anchor stops pinning a
sentence and starts matching any prose (`"e"` matches everything), and every live anchor
clears it with room to spare, the shortest being 24. An id-derived anchor is rejected
because every citation of the pair contains the id, so such an anchor can never be absent
and the self-invalidation never fires. A defective anchor is reported AND deactivates the
entry — an exemption nobody can trust must not suppress anything meanwhile.

Five entries are an AMNESTY, not a clearance — real cross-bundle dependencies that predate
the gate, tracked on kata `kw60` ("three shipped skills cite a sibling their bundle does not
ship"; the two path-form pairs were appended to it). Two of the five break at runtime, not
merely on the page: `repo-compliance-audit`'s `audit.py` refuses to run against a
`mise-en-place` root because `project-memory`'s checklist is not there. Resolving them means
changing a distribution surface (adding a symlink cascades plugin version bumps), which is
an owner decision, not a gate's. This mirrors `check_readme_currency.py`'s landing-commit
anchor: forward-only, with the backlog named out loud. When `kw60` closes, those five
entries are deleted outright.

Run standalone to see every citation the extractor pulls, with its verdict — the tool for
auditing the rule rather than trusting it:

    python3 scripts/check_skill_refs.py --report

Stdlib-only, deterministic (sorted output, no clocks, no network). Exit 0 = clean;
exit 1 = a body cites a skill some bundle shipping it does not carry.
Usage: python3 scripts/check_skill_refs.py   (run from the repo root)
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_roster  # noqa: E402  (reuse its tailored roster line parser)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The prose surface, matching check_solo_skills.py. README.md is deliberately absent.
PROSE_NAMES = ("SKILL.md",)
PROSE_DIRS = ("references", "examples")

# Floor for an anchor's length. Below this it stops pinning a sentence and starts matching
# any prose; every live anchor clears it with room to spare (shortest: 24).
ANCHOR_MIN_CHARS = 20

# (citing skill, cited skill) -> (reason, anchor). The anchor must have substance and must
# still appear in the citing skill's scanned prose, or the entry does not apply; see the
# module docstring.
EXEMPTIONS = {
    ("diagrams", "dataviz"): (
        "scope boundary, not a dependency — the line hands data charts AWAY to dataviz "
        "and says outright they are not this plugin's job, so a consumer without dataviz "
        "is told what this skill will not do, not sent somewhere they cannot go",
        "it is not this plugin's job",
    ),
    ("diagrams", "pptx-themes"): (
        "scope boundary, not a dependency — deck theming is declared owned elsewhere; the "
        "skill renders diagram files and works fully without pptx-themes installed",
        "This plugin renders diagram files",
    ),
    ("mermaid", "dataviz"): (
        "scope boundary, not a dependency — the same data-charts hand-off as diagrams, "
        "written as a restriction on what Mermaid may be used for",
        "Structural diagrams only",
    ),
    ("opencode-sandbox", "bun"): (
        "false positive of the id vocabulary — `bun` here is the RUNTIME BINARY an install "
        "script needs, not this repo's bun skill; nothing about the sentence resolves to a "
        "skill",
        "Needs `bun`. The repository ships a script",
    ),
    ("layer-cycle", "test-quality"): (
        "convenience pointer, not a dependency — the bar it points at is stated inline at "
        "the citation site, so an atelier-only reader has the substance and the citation "
        "only offers more; anchored to that inline sentence, which is exactly what was "
        "missing when this citation shipped broken",
        "red observed against the unfixed code, red again when",
    ),
    # --- amnesty: pre-existing and UNRESOLVED, tracked on kata kw60 -----------------
    # Real cross-bundle dependencies. They are recorded here so the gate can be
    # forward-only; fixing them changes a distribution surface (owner decision). Delete
    # these five entries when kw60 closes — the gate will then be red until the
    # memberships or the bodies change, which is the point.
    ("planning-desk", "task-authoring"): (
        "AMNESTY (kata kw60), pre-existing and unresolved — a real dependency: the desk "
        "says outright that item bodies are written with task-authoring and its rules are "
        "not restated, so a mise-en-place consumer is sent to a skill that bundle does not "
        "ship. Not a clearance; remove this entry when kw60 closes",
        "its rules are not restated here",
    ),
    ("planning-desk", "board-triage"): (
        "AMNESTY (kata kw60), pre-existing and unresolved — a real dependency: "
        "prioritization is delegated to board-triage, which the mise-en-place bundle does "
        "not ship. Not a clearance; remove this entry when kw60 closes",
        "prioritization is the `board-triage` skill's job",
    ),
    ("repo-compliance-audit", "project-memory"): (
        "AMNESTY (kata kw60), pre-existing and unresolved — a real dependency, and the "
        "only one of these that breaks at RUNTIME rather than dead-ending a reader: "
        "`audit.py --plugin-root plugins/mise-en-place` exits with `checklist file "
        "missing: .../skills/project-memory/references/checklist.md`, because "
        "mise-en-place ships this skill and not project-memory. Not a clearance; remove "
        "this entry when kw60 closes",
        "pass `--plugin-root <dir>` pointing at a root that contains",
    ),
    ("mise-en-place-scaffold", "project-memory"): (
        "AMNESTY (kata kw60), pre-existing and unresolved — the same mise-en-place gap "
        "seen from the scaffold: it directs the consumer at a plugin root holding "
        "project-memory's checklist, which that bundle does not ship. Not a clearance; "
        "remove this entry when kw60 closes",
        "(checklist + assets) and",
    ),
    ("project-memory", "repo-compliance-audit"): (
        "AMNESTY (kata kw60), pre-existing and unresolved — a real dependency: the skill "
        "declines to audit and routes the verdict to repo-compliance-audit, which neither "
        "code-desk nor solo-skills ships alongside it. Not a clearance; remove this entry "
        "when kw60 closes",
        "verdicts come from the sibling `repo-compliance-audit` skill",
    ),
}


class Citation(object):
    """One backticked sibling-skill reference: where it is and what it names."""

    __slots__ = ("citing", "cited", "rel", "lineno", "line")

    def __init__(self, citing, cited, rel, lineno, line):
        self.citing = citing
        self.cited = cited
        self.rel = rel
        self.lineno = lineno
        self.line = line

    @property
    def key(self):
        return (self.citing, self.cited)

    @property
    def sort_key(self):
        return (self.citing, self.cited, self.rel, self.lineno)


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ""


def skill_ids(repo):
    """Roster ids of `type: skill`. The vocabulary, derived, never hardcoded."""
    roster = os.path.join(repo, "primitives-core.yaml")
    if not os.path.isfile(roster):
        return []
    return sorted(
        e["id"] for e in check_roster.parse_roster(roster)
        if e.get("type") == "skill" and e.get("id")
    )


def assemblies(repo):
    """{plugin id: set of skill ids it ships}, read from the symlink assemblies."""
    out = {}
    plugins = os.path.join(repo, "plugins")
    if not os.path.isdir(plugins):
        return out
    for plugin in sorted(os.listdir(plugins)):
        if plugin.startswith("."):
            continue
        d = os.path.join(plugins, plugin, "skills")
        if os.path.isdir(d):
            out[plugin] = {x for x in os.listdir(d) if not x.startswith(".")}
    return out


def _prose_files(sdir):
    for name in PROSE_NAMES:
        p = os.path.join(sdir, name)
        if os.path.isfile(p):
            yield p
    for sub in PROSE_DIRS:
        d = os.path.join(sdir, sub)
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            dirs[:] = sorted(x for x in dirs if not x.startswith("."))
            for f in sorted(files):
                if f.endswith(".md"):
                    yield os.path.join(root, f)


def _pattern(sid):
    """`sid` in backticks: the bare id, a namespaced `<plugin>:<id>`, or the `skills/<id>`
    path form with anything after it. The backticks and the trailing `/` anchor both ends,
    so `x-sid`, `skills/sid-extended` and `skills/` alone never match."""
    return re.compile(r"`(?:[\w-]+:)?(?:skills/)?" + re.escape(sid) + r"(?:/[^`]*)?`")


def citations(repo, ids=None):
    """Every backticked sibling-skill citation in the tree, sorted."""
    ids = skill_ids(repo) if ids is None else ids
    patterns = [(sid, _pattern(sid)) for sid in ids]
    out = []
    for citing in ids:
        sdir = os.path.join(repo, "primitives-core", "skills", citing)
        if not os.path.isdir(sdir):
            continue
        for path in _prose_files(sdir):
            rel = os.path.relpath(path, repo)
            for lineno, line in enumerate(_read(path).splitlines(), 1):
                for cited, pat in patterns:
                    if cited != citing and pat.search(line):
                        out.append(Citation(citing, cited, rel, lineno, line.strip()))
    return sorted(out, key=lambda c: c.sort_key)


def _exempts(repo, key):
    """Whether this pair's exemption holds: an anchor with substance, still in the prose."""
    entry = EXEMPTIONS.get(key)
    if entry is None or anchor_defect(key, entry[1]):
        return False
    sdir = os.path.join(repo, "primitives-core", "skills", key[0])
    return any(entry[1] in _read(p) for p in _prose_files(sdir))


def unresolved(repo):
    """{(citing, cited): [(citation, [plugin ids missing the cited skill])]} — every
    citation some bundle cannot follow, before exemptions are applied."""
    plugs = assemblies(repo)
    out = {}
    for cit in citations(repo):
        missing = sorted(
            p for p, members in plugs.items()
            if cit.citing in members and cit.cited not in members
        )
        if missing:
            out.setdefault(cit.key, []).append((cit, missing))
    return out


def anchor_defect(key, anchor):
    """Why this anchor cannot carry the exemption's weight, or None. The gate's whole
    safety property is the anchor, and nothing else constrains what an author puts there."""
    text = anchor.strip()
    if len(text) < ANCHOR_MIN_CHARS:
        return (
            "is under %d characters, so it matches too much prose to pin any particular "
            "sentence" % ANCHOR_MIN_CHARS
        )
    low = text.lower()
    if any(low in sid.lower() for sid in key):
        return (
            "is part of a skill id, which every citation of that pair contains, so it "
            "can never be absent"
        )
    return None


def stale_exemptions(repo, candidates, ids):
    """Entries that suppress nothing, or that rest on an anchor with no substance — either
    way a permanent hole nobody remembers opening."""
    out = []
    for key in sorted(EXEMPTIONS):
        citing, cited = key
        anchor = EXEMPTIONS[key][1]
        missing_ids = [s for s in (citing, cited) if s not in ids]
        if missing_ids:
            out.append(
                "EXEMPTIONS[%r, %r]: no such skill (%s) — remove it"
                % (citing, cited, ", ".join(missing_ids))
            )
            continue
        defect = anchor_defect(key, anchor)
        if defect:
            out.append(
                "EXEMPTIONS[%r, %r]: anchor %r has no substance — it %s; anchor the entry "
                "to the sentence that justifies it" % (citing, cited, anchor, defect)
            )
        if key not in candidates:
            out.append(
                "EXEMPTIONS[%r, %r]: stale — every bundle shipping `%s` now ships `%s` (or "
                "the citation is gone), so the entry suppresses nothing; remove it"
                % (citing, cited, citing, cited)
            )
    return out


def problems(repo=REPO):
    ids = skill_ids(repo)
    candidates = unresolved(repo)
    out = stale_exemptions(repo, candidates, ids)
    for key in sorted(candidates):
        citing, cited = key
        entry = EXEMPTIONS.get(key)
        if _exempts(repo, key):
            continue
        note = ""
        if entry:
            why = anchor_defect(key, entry[1]) or (
                "is absent from this skill's prose, so the reason it records does not "
                "describe this text"
            )
            note = (
                " — its EXEMPTIONS entry is INACTIVE: the anchor %r %s" % (entry[1], why)
            )
        for cit, missing in candidates[key]:
            out.append(
                "%s:%d: cites skill `%s`, which %s %s not ship though %s ship%s `%s`%s "
                "— in: %s"
                % (
                    cit.rel, cit.lineno, cited,
                    ", ".join("plugins/%s" % p for p in missing),
                    "does" if len(missing) == 1 else "do",
                    "it" if len(missing) == 1 else "they",
                    "s" if len(missing) == 1 else "",
                    citing, note, cit.line,
                )
            )
    return sorted(set(out))


def report(repo):
    """Every citation and its verdict. Non-zero exit when any bundle cannot follow one."""
    candidates = unresolved(repo)
    exempt_keys = {k for k in candidates if _exempts(repo, k)}
    print("%-22s %-24s %-10s %s" % ("citing", "cited", "verdict", "site"))
    bad = 0
    for cit in citations(repo):
        if cit.key not in candidates:
            verdict = "shipped"
        elif cit.key in exempt_keys:
            verdict = "exempt"
        else:
            verdict = "MISSING"
            bad += 1
        print("%-22s %-24s %-10s %s:%d" % (cit.citing, cit.cited, verdict, cit.rel, cit.lineno))
    print("")
    print("%d citation(s); %d cross-bundle pair(s), %d exempt; %d unresolved"
          % (len(citations(repo)), len(candidates), len(exempt_keys), bad))
    return 1 if bad else 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="check_skill_refs.py",
        description="No shipped skill body cites a skill its own bundle does not ship.",
    )
    parser.add_argument("--repo", default=REPO, help="repo root to check (default: this one)")
    parser.add_argument("--report", action="store_true",
                        help="print every citation and its verdict")
    args = parser.parse_args(argv)
    repo = os.path.abspath(args.repo)

    if args.report:
        return report(repo)

    probs = problems(repo)
    if probs:
        print("✗ skill-refs: %d cross-bundle citation problem(s)" % len(probs), file=sys.stderr)
        for p in probs:
            print("  - %s" % p, file=sys.stderr)
        return 1
    print(
        "✓ skill-refs clean — every backticked sibling-skill citation resolves inside "
        "every bundle that ships the citing skill (%d exempted pair(s), each anchored to "
        "the prose that justifies it)" % len(EXEMPTIONS)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

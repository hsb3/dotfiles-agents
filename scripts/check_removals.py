#!/usr/bin/env python3
"""Removal gate — a unit that stops shipping must say so in the commit that removes it.

Every other distribution gate watches things that CHANGE. Nothing watched things that
DISAPPEAR: `check_version_bump.py` says so in its own words ("a plugin published on `main`
but deleted on `dev` (a removal has no version to bump)"), and a deletion moves no version,
breaks no symlink, and orphans no roster entry — so a skill can leave the marketplace with
every gate green and no record anywhere a consumer can read. The next `publish.yml` run
lifts the smaller tree onto `main` and the thing is simply gone.

What this proves:

  1. The published unit set is DERIVED from `git ls-tree -r origin/main -- plugins` — plugin
     ids and their member units (`plugins/<id>/{skills,agents,hooks,commands}/<name>`, a
     trailing `.md` stripped). The local set is the same derivation over the on-disk
     `plugins/` assemblies. Both sides come from a tree; there is NO inventory, no removals
     file, nothing anyone maintains by hand. A file that listed what had been removed would
     be one more thing to forget to update, and forgetting is the failure being caught.
  2. A unit on `origin/main` and absent locally is a REMOVAL, and every removal must be
     declared by the commit that removed it. `git log --diff-filter=D -- <both homes>`
     produces the CANDIDATES; each is then confirmed by tree (the path resolves in the
     parent commit and not in the commit itself), newest first, because that pathspec also
     matches a file deleted INSIDE a unit that still ships. Over HEAD's history, which on
     `dev` is the squashed merge commit — the form a removal actually lands in here.
  3. `--notes` renders the same set as a markdown section for the release page, so a removal
     reaches a CONSUMER (decision-013's release mechanism) and not only this gate's exit
     code. It prints nothing when nothing was removed and always exits 0: release notes must
     never be the reason a publish fails.

**A declaration is EVIDENCE, not proof.** The message (subject + body, matched case-
insensitively as one blob) must name the removed unit and contain a removal verb. That is a
string match, and a string match cannot tell a deliberate retirement from a sentence that
happens to contain both. The looser reading is deliberate: the owner ruling put the
declaration in PROSE in the commit message (decision-013), and the two real squash-merged
removals in this repo's history — `2c590d6` ("fold comm-kit into comms", body: "the comm-kit
skill are removed") and `84f9dd7` ("collapse github-project-board into a GitHub Projects
adapter script", body: "…its solo-skills symlink are deleted") — carry no trailer and cannot
retroactively grow one without rewriting landed history. A trailer-only rule would therefore
be red on `dev` from the day it merged. (`84f9dd7` passed on its BODY alone until `collapse`
joined `REMOVAL_VERBS` — that is how brittle a narrow verb list is, and why the list is
wide.) What this gate is actually worth: an UNDECLARED removal, the one nobody wrote a
sentence about, cannot pass silently. The false-PASS side is closed by the TREE check in
`find_removal()`, never by tightening the string rule.

Where it runs: a step in the `drift guards` CI job, NOT in `make ci`. Reaching `origin/main`
needs NETWORK and `make ci` is offline-and-zero-install by design; a job of its own was
equally unavailable because `dev`'s branch protection pins required checks by job NAME, so a
new one would strand every open PR on a check that never reports. Same placement, same two
reasons, as `check_version_bump.py`, `check_vendored_drift.py` and `check_labels.py`.

Network contract — an unreadable published tree is RED, the same house rule every CI-only
gate here follows (decision-016 point 4): a gate that cannot measure is red, never green,
because a step that exits 0 having measured nothing is indistinguishable in the CI summary
from one that measured and found nothing missing. The failure names which case it hit and
says outright that it is not evidence of a removal, so nobody goes hunting for one. A fetch
that fails while a cached `origin/main` still resolves is NOT that case: something real was
compared, so it warns and proceeds. The cost of the ruling is a re-run on a network blip;
that is the cheaper mistake.

Deliberately NOT covered: whether a removal was a GOOD idea (that is review), whether the
declaring sentence is honest (see above), a unit renamed rather than removed (it reads as one
removal plus one addition, and the declaration is where the rename gets explained), and
anything outside `plugins/` — `primitives-core/` is not on `main`, so a primitive that never
shipped in an assembly has no published presence to lose.

Stdlib-only, deterministic. Exit 0 = no undeclared removal; exit 1 = violations, or a
published tree that could not be read.
Usage: python3 scripts/check_removals.py [--notes]   (run from anywhere)
"""

import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_version_bump as bump  # noqa: E402  (both sides of the tree comparison already live there)

REPO = bump.REPO
PUBLISHED_REF = bump.PUBLISHED_REF

# The four primitive kinds an assembly can carry; anything else under plugins/<id>/ is
# bundle furniture (README.md, hooks.json, .claude-plugin/) and cannot be removed as a unit.
KINDS = ("skills", "agents", "hooks", "commands")

# Wide on purpose: a well-written declaration says "drop", "sunset" or "supersede" as
# readily as "remove", and rejecting one is a false RED against a contributor who did
# exactly the right thing. Widening costs nothing on the other side — the false-PASS risk
# is bounded by the tree check in find_removal(), not by this list.
REMOVAL_VERBS = (
    "remove", "removed", "removes", "removal",
    "delete", "deleted", "deletes",
    "retire", "retires", "retired",
    "fold", "folded", "folds",
    "drop", "drops", "dropped",
    "sunset", "sunsets", "sunsetting",
    "supersede", "supersedes", "superseded",
    "deprecate", "deprecates", "deprecated",
    "collapse", "collapses", "collapsed",
    "absorb", "absorbs", "absorbed",
)
VERB_RE = re.compile(r"\b(" + "|".join(REMOVAL_VERBS) + r")\b", re.IGNORECASE)

NOTES_HEADING = "### Removed in this publish"
NO_COMMIT = "no commit in this history deletes it"

Removal = collections.namedtuple("Removal", "unit sha subject message declared")


class Unmeasurable(RuntimeError):
    """The published tree could not be read at all — red, not a skip (decision-016 pt 4)."""


# --- deriving the two unit sets -----------------------------------------------------

def unit_ids(index):
    """{pid: {relpath: blob}} -> {"<pid>/<kind>/<name>"} for every shippable unit.

    One unit collapses however many files it holds: `skills/x/SKILL.md`,
    `skills/x/references/y.md` and `skills/x/scripts/z.py` are all the unit `x`. `agents/x.md`
    and `commands/x.md` lose the suffix so both sides of the comparison spell them the same
    way regardless of whether the tree stores a file or a directory.
    """
    units = set()
    for pid, blobs in index.items():
        for rel in blobs:
            parts = rel.split("/")
            if len(parts) < 2 or parts[0] not in KINDS:
                continue
            name = parts[1][:-3] if parts[1].endswith(".md") else parts[1]
            if name:
                units.add(f"{pid}/{parts[0]}/{name}")
    return units


def removed(local, published):
    """Published units with no local counterpart, as sorted unit ids.

    A plugin absent from `plugins/` entirely reports ONCE as its plugin id rather than once
    per member: the removal is the bundle, and listing its every skill would bury that.
    """
    gone = [pid for pid in published if pid not in local]
    dropped = set(gone)
    gone += [
        unit
        for unit in unit_ids(published) - unit_ids(local)
        if unit.split("/")[0] not in dropped
    ]
    return sorted(gone)


# --- finding the commit that removed it ---------------------------------------------

def pathspecs(unit):
    """The dev-side paths whose deletion IS this unit's removal.

    Both homes, because a unit leaves in one commit or two: the symlink in the assembly
    (`plugins/<id>/<kind>/<name>`) and the body it points at (`primitives-core/<kind>/<name>`).
    The `.md` variants cover agents and commands, which are files rather than directories.
    """
    parts = unit.split("/")
    if len(parts) == 1:
        return [f"plugins/{parts[0]}"]
    pid, kind, name = parts
    return [
        f"plugins/{pid}/{kind}/{name}",
        f"plugins/{pid}/{kind}/{name}.md",
        f"primitives-core/{kind}/{name}",
        f"primitives-core/{kind}/{name}.md",
    ]


def removes_outright(sha, specs, run):
    """True when `sha` deleted one of `specs` ITSELF, not a file inside it.

    A tree check, not a stronger string rule: the path resolves in the parent's tree and no
    longer resolves in this commit's. `git cat-file -e` answers for a tree object as readily
    as a blob, so a skill directory and an `agents/<name>.md` blob take the same path here.
    """
    for spec in specs:
        if run(["cat-file", "-e", f"{sha}:{spec}"])[0] == 0:
            continue  # still present in this commit, so it did not remove it
        if run(["cat-file", "-e", f"{sha}^:{spec}"])[0] == 0:
            return True  # absent here, present in the parent — a root commit fails this and is skipped
    return False


def find_removal(unit, repo=None, run=None):
    """(sha, full message) of the newest commit that deleted `unit` OUTRIGHT, or ("", "").

    The pathspec query is only the CANDIDATE list: it matches any file deleted under either
    home, so a commit that dropped one reference page inside a still-shipping skill answers
    it too. Taking the newest candidate blindly lets that commit's message declare a
    different, earlier, undeclared removal — measured against this repo's real history, that
    pre-authorized two live units. So each candidate is confirmed by tree, newest first, and
    the first one that actually deleted the unit wins.

    HEAD's history, so on `dev` this resolves to the SQUASHED merge commit — the shape a
    removal actually lands in here, and the message a reviewer actually wrote.
    """
    run = run or (lambda args: bump.run_git(args, repo=repo or REPO))
    specs = pathspecs(unit)
    try:
        rc, out, _ = run(["log", "--diff-filter=D", "--format=%H%x00%B%x00%x00", "--"] + specs)
    except OSError:
        return "", ""
    if rc != 0:
        return "", ""
    for record in out.decode("utf-8", "replace").split("\0\0"):
        sha, _, message = record.partition("\0")
        sha = sha.strip()
        if sha and removes_outright(sha, specs, run):
            return sha, message.strip()
    return "", ""


def is_declared(message, unit):
    """True when `message` names the unit AND says something left — evidence, not proof.

    Whole-message, case-insensitive, deliberately loose. See the module docstring for why
    this is a prose match rather than a trailer.
    """
    if not message:
        return False
    leaf = unit.rsplit("/", 1)[-1]
    return leaf.lower() in message.lower() and bool(VERB_RE.search(message))


def survey(local, published, lookup):
    """[Removal] for every removed unit, in stable order.

    `lookup` takes a unit id and returns (sha, message) — injected so the rule is testable
    without git.
    """
    rows = []
    for unit in removed(local, published):
        sha, message = lookup(unit)
        subject = message.splitlines()[0].strip() if message else ""
        rows.append(Removal(unit, sha, subject, message, is_declared(message, unit)))
    return rows


# --- output -------------------------------------------------------------------------

def notes(rows):
    """The release-notes section for `rows`, or "" when nothing was removed."""
    if not rows:
        return ""
    lines = [NOTES_HEADING, ""]
    for row in rows:
        lines.append(f"- `{row.unit}` — {row.subject or NO_COMMIT}")
    return "\n".join(lines) + "\n"


def _rows(plugins_dir, repo, tree):
    reason = tree.prepare()
    if reason:
        raise Unmeasurable(reason)
    try:
        published = tree.index()
    except RuntimeError as exc:
        raise Unmeasurable(str(exc)) from exc
    return survey(
        bump.local_index(plugins_dir), published, lambda unit: find_removal(unit, repo=repo)
    )


def main(plugins_dir=None, repo=None, tree=None, notes_mode=False, out=print):
    repo = repo or REPO
    tree = tree if tree is not None else bump.GitPublishedTree(repo=repo)

    if notes_mode:
        # A publish must never fail because its release notes could not be computed, so
        # every failure here degrades to an empty section. The GATE below is where an
        # unreadable published tree is red.
        try:
            text = notes(_rows(plugins_dir, repo, tree))
        except Exception:  # noqa: BLE001 - deliberate: notes are advisory, the gate is not
            return 0
        if text:
            out(text.rstrip("\n"))
        return 0

    try:
        rows = _rows(plugins_dir, repo, tree)
    except Unmeasurable as exc:
        out(
            f"✗ removal gate: {exc}. Nothing was compared, so this is NOT evidence of a "
            "removal — it is a gate that could not measure, which decision-016 point 4 makes "
            "red rather than green. Re-run once the published tree is readable."
        )
        return 1
    if getattr(tree, "note", ""):
        out(f"⚠ removal gate: {tree.note}")

    undeclared = [r for r in rows if not r.declared]
    for row in rows:
        if row.declared:
            out(f"  · {row.unit} removed by {row.sha[:7]} — {row.subject}")
    if undeclared:
        out(f"✗ removal gate: {len(undeclared)} undeclared removal(s)")
        for row in undeclared:
            where = f"{row.sha[:7]} ({row.subject})" if row.sha else NO_COMMIT
            out(f"  - {row.unit}: published on {PUBLISHED_REF}, absent here — {where}")
        out(
            "  A removal is declared in the message of the commit that removes it: name the "
            "unit and say it was removed/retired/folded, plus where its capability went. "
            "That message is what reaches consumers in the release notes "
            "(scripts/check_removals.py --notes) — see .github/CONTRIBUTING.md, "
            "\"Removing a primitive or a plugin\"."
        )
        return 1
    out(
        f"✓ removal gate clean — {len(rows)} removal(s) against {PUBLISHED_REF}, each "
        "declared by the commit that removed it"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(notes_mode="--notes" in sys.argv[1:]))

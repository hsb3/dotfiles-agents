"""Remote-tracking refs are resolved by unambiguous full refname.

`git rev-parse` resolves `refs/<name>`, `refs/tags/<name>` and `refs/heads/<name>` BEFORE
`refs/remotes/<name>`, so a local branch or tag named `origin/main` silently shadows the
tracking ref. Worse, a full refname is not self-verifying: with no such tracking ref,
`refs/remotes/origin/main` itself falls through to `refs/heads/refs/remotes/origin/main`.
The executable site (the comment-hygiene hook) is pinned behaviourally in
tests/test_comment_hygiene_gate.py; the sites here are shipped templates a consumer copies
into their own repo, reference docs whose commands get pasted into a shell, and a CI-only
workflow — nothing runs them, so they are pinned by reading the file.

The sweep is deliberately dumb: it flags EVERY `<remote>/<branch>`-shaped token in scope
and requires each surviving one to be listed in ALLOWED with a reason. Earlier it keyed off
a list of ref-consuming git subcommands and stripped `#` comments, which let a line
continuation, `git merge`, `--format='#%h'`, and a non-`main` trunk name all through. A
closed vocabulary of verbs cannot be complete; a closed list of exceptions can.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SKILL = "primitives-core/skills/private-fork"
HOOK_PY = "primitives-core/hooks/comment-hygiene-gate/hook.py"
PUBLISH_YML = ".github/workflows/publish.yml"
CHECK_YML = SKILL + "/assets/templates/upstream-check.yml"
DIGEST_SH = SKILL + "/assets/templates/upstream-digest.sh"

# `<remote>/<branch>`, with the lookbehind excluding an already-qualified
# `refs/remotes/upstream/x`. Not a closed branch vocabulary: a fork is told to match
# upstream's default branch name, so a non-`main` trunk is the documented normal case.
SHORT_FORM = re.compile(r"(?<![\w/-])(?:origin|upstream|fork)/[A-Za-z0-9_.{}<>/-]+")

# Short forms that are NOT defects. A new hit is fixed or lands here with its reason.
ALLOWED = {
    # Display, not resolution: this string is echoed to the step log and printed in the
    # issue body. The counted range beside it names the full refname.
    'range="${watermark}..upstream/{{BRANCH}}"':
        "display string; resolved_range is what rev-list resolves",
    # Prose and comments that quote the WRONG spelling on purpose, to name what not to
    # write. Rewording one drops it out of ALLOWED and sends it back through review.
    '# Full refname, not `upstream/{{BRANCH}}`: `refs/heads/<name>` resolves before':
        "quotes the rejected spelling in order to warn against it",
    "# tracking ref in full; `upstream-{{BRANCH}}` is the local mirror, `range` is display.":
        "comment explaining the split, not a command",
    "# advances origin/main to the tree being published — after it the removed unit is absent":
        "publish.yml comment describing the effect; the command below it is fully qualified",
    "# local ref named `origin/main` would otherwise become the base and diff a shorter range.":
        "hook.py comment naming the hazard it guards against",
    "local branch named `upstream/main` would resolve first and merge the wrong commits.":
        "FORK_CHANGES.md rationale for the full refname on the line above",
    "`refs/heads/<name>` resolves first: a local branch named `upstream/main` would":
        "upstream-sync.md rationale for the full refname in the blocks below",
    # `fork/` here is a LOCAL topic-branch prefix, not a remote. The regex keeps `fork` in
    # its vocabulary anyway: a remote actually named `fork` is the likelier future mistake.
    "| Branches | Single trunk `main`; optional short-lived `fork/<topic>` | Trunk + read-only `upstream-<branch>` mirror + throwaway `uat` staging per merge |":
        "SKILL.md: fork/<topic> is a local topic-branch prefix",
    "| `fork/<topic>` | Optional short-lived features | Merge to `main`, delete |":
        "setup.md: fork/<topic> is a local topic-branch prefix",
    "`fork/<topic>` are both genuine local branches.":
        "README.md sentence saying exactly that",
    # Prose naming the remote layout. These read as nouns in a sentence or a table cell,
    # never as something a reader pastes into a shell.
    "| Merge path | Merge `upstream/main` directly into trunk | `upstream/<branch>` → `uat` → trunk, promoted only after the post-merge checklist |":
        "SKILL.md comparison table; names the merge path, not a runnable command",
    '- A "pristine mirror" long-lived local branch on the light tier — `upstream/<branch>`':
        "SKILL.md prose naming the ref",
    "| `upstream/<branch>` | Pristine upstream reference | Fetch only; never push |":
        "setup.md remote-layout table cell (file not in scope for this change)",
    "| trunk (match upstream's default branch name) | `origin/<trunk>` | The fork — active work |":
        "setup.md remote-layout table cell (file not in scope for this change)",
    "| `upstream-<branch>` | `upstream/<branch>` | Read-only local mirror; advanced `--ff-only` after each merge; baseline for digests and post-merge diffs |":
        "setup.md remote-layout table cell (file not in scope for this change)",
    "`upstream/<branch>` → `uat` → trunk.":
        "setup.md prose naming the promotion path",
    "- Branch model: single trunk `main` (= upstream + our changes); `upstream/main` is the":
        "FORK_CHANGES.md prose naming the reference, not a command",
}


def in_scope():
    """Every file of the private-fork skill, plus the hook and the publish workflow.

    Deliberately not repo-wide: ordinary prose elsewhere names `origin/main` constantly.
    """
    paths = [HOOK_PY, PUBLISH_YML]
    for root, _dirs, names in os.walk(os.path.join(REPO, SKILL)):
        for name in sorted(names):
            paths.append(os.path.relpath(os.path.join(root, name), REPO))
    return sorted(paths)


def logical_lines(text):
    """(first lineno, joined text) with trailing-backslash continuations folded in."""
    out, buf, start = [], None, 0
    for n, raw in enumerate(text.splitlines(), 1):
        if buf is None:
            buf, start = raw, n
        else:
            buf = buf + " " + raw.strip()
        if buf.rstrip().endswith("\\"):
            buf = buf.rstrip()[:-1]
            continue
        out.append((start, buf))
        buf = None
    if buf is not None:
        out.append((start, buf))
    return out


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class ShortFormResolution(unittest.TestCase):
    maxDiff = None

    def hits(self):
        found = []
        for rel in in_scope():
            for n, line in logical_lines(read(rel)):
                if SHORT_FORM.search(line) and line.strip() not in ALLOWED:
                    found.append("%s:%d: %s" % (rel, n, line.strip()))
        return found

    def test_every_short_form_tracking_ref_is_fixed_or_justified(self):
        self.assertEqual(
            self.hits(), [],
            "name each refs/remotes/<remote>/<branch>, or add it to ALLOWED with why:\n"
            + "\n".join(self.hits()),
        )

    def test_allowed_entries_are_all_still_present(self):
        """A stale exemption is a hole: it stops describing anything and nobody notices."""
        blob = "\n".join(read(rel) for rel in in_scope())
        missing = [line for line in ALLOWED if line not in blob]
        self.assertEqual(missing, [], "ALLOWED entries no longer in any file in scope")

    def test_upstream_check_counts_over_the_full_refname(self):
        """The counted range is resolution; the echoed one stays short, for readers."""
        text = read(CHECK_YML)
        use = re.search(r'rev-list --count "\$\{?(\w+)\}?"', text)
        self.assertIsNotNone(use, "the count step no longer has the shape this test pins")
        var = use.group(1)
        assign = re.search(r'^\s*%s="([^"]*)"' % var, text, re.M)
        self.assertIsNotNone(assign, "no assignment found for $" + var)
        self.assertIn("refs/remotes/upstream/", assign.group(1))

    def test_upstream_digest_config_ref_is_a_full_refname(self):
        assign = re.search(r'^UPSTREAM_REF="([^"]*)"', read(DIGEST_SH), re.M)
        self.assertIsNotNone(assign, "UPSTREAM_REF is no longer a plain CONFIG assignment")
        self.assertTrue(assign.group(1).startswith("refs/remotes/"), assign.group(1))

    def test_deliberate_local_refs_say_why_in_place(self):
        yml = read(CHECK_YML)
        arm = "git rev-parse upstream-{{BRANCH}}"
        self.assertIn(arm, yml)
        self.assertIn("local", yml[max(0, yml.index(arm) - 500):yml.index(arm)].lower())

        self.assertIn("local read-only mirror", read(DIGEST_SH))

        hook = read(HOOK_PY)
        fallback = '"refs/heads/main"'
        self.assertIn(fallback, hook)
        self.assertIn("local", hook[max(0, hook.index(fallback) - 400):hook.index(fallback)].lower())

    def test_the_sweep_can_see_the_shapes_it_claims_to(self):
        """Guards the sweep itself: without this its silence proves nothing."""
        caught = [
            'git rev-list --count \\\n  "upstream/{{BRANCH}}..HEAD"',   # line continuation
            "git merge upstream/main",                                   # mutating verbs the
            "git rebase upstream/main",                                  # old verb list omitted
            "git reset --hard origin/main",
            "git switch -c work origin/main",
            "git branch mirror upstream/main",
            "git for-each-ref origin/main",
            "git cherry upstream/main",
            "git shortlog origin/main..HEAD",                            # cannot match \blog\b
            "git log --format='#%h' upstream/main",                      # `#` inside a quote
            'range="${w}..fork/<trunk>"',                                # no verb on the line
            "git merge origin/develop",                                  # open branch vocabulary
            "git merge upstream/{{UPSTREAM_BRANCH}}",
            "git merge fork/main",
        ]
        for src in caught:
            joined = [line for _n, line in logical_lines(src)]
            self.assertTrue(any(SHORT_FORM.search(line) for line in joined), src)

        # Known blind spots, asserted so they are a recorded ceiling rather than a surprise.
        # ponytail: a remote under any other name, and a ref built at runtime. Closing
        # either needs a shell/YAML evaluator; do that if a third one ever shows up.
        blind = [
            "git merge mirror/main",                     # a remote named something else
            'ref="upstream"; git merge "$ref/main"',      # ref assembled at runtime
        ]
        for src in blind:
            self.assertIsNone(SHORT_FORM.search(src), src)


if __name__ == "__main__":
    unittest.main()

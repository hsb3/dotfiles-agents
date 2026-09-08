"""Remote-tracking refs are resolved by unambiguous full refname.

`git rev-parse` resolves `refs/<name>`, `refs/tags/<name>` and `refs/heads/<name>` BEFORE
`refs/remotes/<name>`, so a local branch or tag named `origin/main` silently shadows the
tracking ref of that name.

The one site in this tree that a test can execute is the comment-hygiene hook, pinned
behaviourally in tests/test_comment_hygiene_gate.py. The sites here are shipped templates a
consumer copies into their own repo and a CI-only workflow — nothing runs them, so they are
pinned by reading the file.

A local branch (`upstream-<branch>`, `main`) is NOT a defect; it is a real local ref by
design. Those sites carry an in-place note saying so, and the last test asserts the note.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATES = "primitives-core/skills/private-fork/assets/templates"
CHECK_YML = TEMPLATES + "/upstream-check.yml"
DIGEST_SH = TEMPLATES + "/upstream-digest.sh"
PUBLISH_YML = ".github/workflows/publish.yml"
HOOK_PY = "primitives-core/hooks/comment-hygiene-gate/hook.py"

# A git subcommand that RESOLVES a ref argument. `git fetch upstream` names a remote rather
# than a ref and carries no slash, so SHORT_FORM never matches it.
REF_VERB = re.compile(
    r"\bgit\b[^|;&]*?\b(?:rev-parse|rev-list|merge-base|log|diff|cat-file|checkout|show|describe)\b"
)
SHORT_FORM = re.compile(r"(?<!refs/remotes/)\b(?:origin|upstream)/(?:main|master|\{\{BRANCH\}\})")


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


class ShortFormResolution(unittest.TestCase):
    def test_no_ref_resolving_command_names_a_short_form_tracking_ref(self):
        bad = []
        for rel in (CHECK_YML, DIGEST_SH, PUBLISH_YML):
            for n, line in enumerate(read(rel).splitlines(), 1):
                code = line.split("#", 1)[0]
                if REF_VERB.search(code) and SHORT_FORM.search(code):
                    bad.append("%s:%d: %s" % (rel, n, line.strip()))
        self.assertEqual(
            bad, [], "name these refs/remotes/<remote>/<branch>:\n" + "\n".join(bad)
        )

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
        self.assertTrue(
            assign.group(1).startswith("refs/remotes/"), assign.group(1)
        )

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


if __name__ == "__main__":
    unittest.main()

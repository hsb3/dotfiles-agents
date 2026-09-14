"""Every credential path named in evals/ must be git-ignored (wz8g).

Derives paths from the actual evals/ text files (regex over *.py/*.sh/*.md, excluding
evals/pb_data/) rather than a hardcoded list — a recorded inventory goes stale the moment
a new file names the credential path differently. Each derived path is then checked with
`git check-ignore` against the real repo .gitignore.
"""

import os
import re
import subprocess
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVALS = os.path.join(REPO, "evals")

# A path-shaped token ending in .env, anchored at a real boundary (start of string, or
# preceded by whitespace/quote/backtick/=) so shell/py identifiers like "os.environ" or
# interpolation artifacts like "$REPO/..." aren't captured as literal paths.
CREDENTIAL_PATH_RE = re.compile(r"""(?:(?<=[\s"'`=])|^)((?:[\w.-]+/)+[\w.-]+\.env)\b""")


def _derive_credential_paths():
    found = set()
    for dirpath, dirnames, filenames in os.walk(EVALS):
        dirnames[:] = [d for d in dirnames if d != "pb_data"]
        for name in filenames:
            if not name.endswith((".py", ".sh", ".md")):
                continue
            with open(os.path.join(dirpath, name), encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            for m in CREDENTIAL_PATH_RE.findall(text):
                if not m.endswith(".example"):
                    found.add(m)
    return found


class EvalsCredentialPathsIgnored(unittest.TestCase):
    def test_derives_at_least_the_known_credential_path(self):
        # Guards against the regex silently matching nothing (e.g. evals/ reorganized).
        paths = _derive_credential_paths()
        self.assertIn(".claude/operations/extender-db.env", paths)

    def test_every_derived_credential_path_is_gitignored(self):
        for path in sorted(_derive_credential_paths()):
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "check-ignore", "-q", path], cwd=REPO,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"{path!r} is referenced in evals/ but not covered by .gitignore",
                )


if __name__ == "__main__":
    unittest.main()

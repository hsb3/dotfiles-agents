"""check_readme_currency.py — the README-currency gate (decision-015).

Fixture repos are real git repos built under a tempdir (never under primitives-core/, per
the roster guard's orphan rule); the module's REPO constant is pointed at them for the
duration of each test. The gate derives everything from history, so a fixture that is not
a git repo would prove nothing.

The red/green pair decision-015 turns on — a body change committed without touching the
README is stale, the same change with the README touched is not — is the first two tests.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import check_readme_currency as C  # noqa: E402


class ReadmeCurrencyGate(unittest.TestCase):
    def setUp(self):
        self.fix = tempfile.mkdtemp(prefix="check-readme-currency-")
        self.saved = C.REPO
        C.REPO = self.fix
        self._git("init", "-q")

    def tearDown(self):
        C.REPO = self.saved
        shutil.rmtree(self.fix, ignore_errors=True)

    # --- fixture helpers -------------------------------------------------
    def _git(self, *args, repo=None):
        proc = subprocess.run(
            ["git", "-C", repo or self.fix, "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false"] + list(args),
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, f"git {args} failed: {proc.stderr}")
        return proc.stdout.strip()

    def _write(self, rel, text):
        path = os.path.join(self.fix, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _commit(self, msg):
        self._git("add", "-A")
        self._git("commit", "-qm", msg)

    def _skill(self, name, body="v1\n"):
        self._write(f"primitives-core/skills/{name}/SKILL.md", body)
        self._write(f"primitives-core/skills/{name}/README.md", f"# {name}\n\nWhat it does.\n")

    # --- the ruling ------------------------------------------------------
    def test_body_and_readme_in_one_commit_is_clean(self):
        self._skill("alpha")
        self._commit("add alpha")
        self.assertEqual(C.problems(), [])

    def test_body_change_without_readme_is_stale(self):
        self._skill("alpha")
        self._commit("add alpha")
        self._write("primitives-core/skills/alpha/SKILL.md", "v2\n")
        self._commit("rewrite alpha")
        found = C.problems()
        self.assertEqual(len(found), 1)
        self.assertIn("skill 'alpha'", found[0])
        self.assertIn("rewrite alpha", found[0])
        self.assertIn("primitives-core/skills/alpha/README.md", found[0])

    def test_same_change_with_readme_touched_is_clean(self):
        self._skill("alpha")
        self._commit("add alpha")
        self._write("primitives-core/skills/alpha/SKILL.md", "v2\n")
        self._write("primitives-core/skills/alpha/README.md", "# alpha\n\nWhat it does, v2.\n")
        self._commit("rewrite alpha + README")
        self.assertEqual(C.problems(), [])

    def test_any_file_in_the_unit_counts_not_just_skill_md(self):
        self._skill("alpha")
        self._commit("add alpha")
        self._write("primitives-core/skills/alpha/scripts/run.py", "print(1)\n")
        self._commit("add a bundled script")
        self.assertEqual(len(C.problems()), 1)

    def test_readme_touched_in_a_later_commit_is_clean(self):
        self._skill("alpha")
        self._commit("add alpha")
        self._write("primitives-core/skills/alpha/SKILL.md", "v2\n")
        self._commit("rewrite alpha")
        self._write("primitives-core/skills/alpha/README.md", "# alpha\n\nRe-reviewed.\n")
        self._commit("re-review the alpha README")
        self.assertEqual(C.problems(), [])

    def test_readme_only_change_never_makes_a_unit_stale(self):
        self._skill("alpha")
        self._commit("add alpha")
        self._write("primitives-core/skills/alpha/README.md", "# alpha\n\nTypo fixed.\n")
        self._commit("typo")
        self.assertEqual(C.problems(), [])

    # --- scope -----------------------------------------------------------
    def test_plugin_is_read_as_its_own_files_not_through_its_symlinks(self):
        self._skill("alpha")
        self._write("plugins/kit/plugin.json", '{"name": "kit"}\n')
        self._write("plugins/kit/README.md", "# kit\n\nShips `alpha`.\n")
        os.makedirs(os.path.join(self.fix, "plugins", "kit", "skills"))
        os.symlink("../../../primitives-core/skills/alpha",
                   os.path.join(self.fix, "plugins", "kit", "skills", "alpha"))
        self._commit("add alpha and the kit assembly")
        # A member skill moving, acknowledged on the skill's own README, leaves the
        # assembly current: the plugin README documents membership, not member bodies.
        self._write("primitives-core/skills/alpha/SKILL.md", "v2\n")
        self._write("primitives-core/skills/alpha/README.md", "# alpha\n\nv2.\n")
        self._commit("rewrite alpha + README")
        self.assertEqual(C.problems(), [])
        # The assembly's own tracked files are in scope.
        self._write("plugins/kit/plugin.json", '{"name": "kit", "version": "0.2.0"}\n')
        self._commit("bump kit")
        found = C.problems()
        self.assertEqual(len(found), 1)
        self.assertIn("plugin 'kit'", found[0])

    def test_untracked_unit_is_not_this_gates_business(self):
        self._skill("alpha")
        self._commit("add alpha")
        self._skill("beta")  # never committed
        self.assertEqual(C.problems(), [])

    # --- shallow, non-repo -----------------------------------------------
    def test_shallow_clone_is_a_hard_failure_not_a_vacuous_pass(self):
        self._skill("alpha")
        self._commit("add alpha")
        self._write("primitives-core/skills/alpha/SKILL.md", "v2\n")
        self._commit("rewrite alpha")
        clone = tempfile.mkdtemp(prefix="check-readme-currency-shallow-")
        try:
            subprocess.run(["git", "clone", "-q", "--depth", "1", "file://" + self.fix, clone],
                           capture_output=True, text=True, check=True)
            C.REPO = clone
            found = C.problems()
            self.assertEqual(len(found), 1)
            self.assertIn("shallow", found[0])
        finally:
            shutil.rmtree(clone, ignore_errors=True)

    def test_non_repo_is_reported(self):
        C.REPO = tempfile.mkdtemp(prefix="check-readme-currency-bare-")
        try:
            found = C.problems()
            self.assertEqual(len(found), 1)
            self.assertIn("not a git repository", found[0])
        finally:
            shutil.rmtree(C.REPO, ignore_errors=True)

    def test_symlinked_readme_is_acknowledged_through_its_target(self):
        self._skill("alpha")
        self._write("plugins/kit/plugin.json", '{"name": "kit"}\n')
        os.symlink("../../primitives-core/skills/alpha/README.md",
                   os.path.join(self.fix, "plugins", "kit", "README.md"))
        self._commit("add alpha and a kit that reuses its README")
        self._write("plugins/kit/plugin.json", '{"name": "kit", "version": "0.2.0"}\n')
        self._commit("bump kit")
        self.assertEqual(len(C.problems()), 1)
        # Editing the file a reader actually opens clears it; editing the link entry
        # alone could not, so a symlinked README would otherwise be unclearable.
        self._write("primitives-core/skills/alpha/README.md", "# alpha\n\nAnd the kit.\n")
        self._commit("re-review the shared README")
        self.assertEqual(C.problems(), [])

    def test_live_tree_is_clean(self):
        C.REPO = self.saved
        if C._git("rev-parse", "--is-shallow-repository") == "true":
            self.skipTest("shallow clone — the gate refuses one; nothing to assert here")
        self.assertEqual(C.problems(), [])


if __name__ == "__main__":
    unittest.main()

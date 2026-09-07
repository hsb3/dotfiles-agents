"""check_removals.py — the removal gate.

Three layers, cheapest first:

  * Pure-function groups (`UnitDerivation`, `DeclarationText`, `NotesSection`) need no git
    and no network — they pin how a published path becomes a unit id, what counts as a
    declaration, and what the release-notes section looks like.
  * `SyntheticRemovalRepo` builds a throwaway ORIGIN repo holding the dereferenced published
    tree and a throwaway WORK repo holding the symlink assembly, wires one to the other over
    the file transport (no network), then deletes a unit and drives `main()` end to end —
    red with a bare commit message, green once the same commit declares the removal.
  * `RealHistoryDeclarations` reads THIS repo's own git log for the two squash-merged
    removals already in history (`2c590d6` comm-kit, `84f9dd7` github-project-board). They
    are the reason the declaration is a prose match rather than a trailer, so they are
    fixtures rather than anecdotes. Each SKIPS when the commit is absent, since
    `entry-gate-floor` checks out depth-1.

Fixture trees live under a tempdir, never under primitives-core/ (the roster guard's orphan
rule).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import check_removals as R  # noqa: E402
import check_version_bump as V  # noqa: E402

# Real squash-merged removals in this repo's history: (commit, unit id it removed).
COMM_KIT = ("2c590d6", "code-desk/skills/comm-kit")
GITHUB_PROJECT_BOARD = ("84f9dd7", "solo-skills/skills/github-project-board")

GIT_IDENTITY = [
    "-c", "user.name=Removal Gate Test",
    "-c", "user.email=removal-gate@example.invalid",
    "-c", "commit.gpgsign=false",
]


def have_git():
    return shutil.which("git") is not None


def git(cwd, *args):
    """Run git in `cwd`, asserting success; returns stdout text."""
    proc = subprocess.run(
        ["git", "-C", cwd] + GIT_IDENTITY + list(args), capture_output=True, timeout=60
    )
    if proc.returncode != 0:
        raise AssertionError(
            "git " + " ".join(args) + " failed: " + proc.stderr.decode("utf-8", "replace")
        )
    return proc.stdout.decode("utf-8", "replace")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


PLUGIN_JSON = '{\n  "name": "demo",\n  "description": "A fixture plugin.",\n  "version": "0.1.0"\n}\n'


def build_fixture(root):
    """A published ORIGIN repo + a WORK repo shipping the same two skills.

    origin/ is the publish shape: `plugins/demo/skills/<name>/SKILL.md` as REAL files, the
    way `cp -RL plugins` lands them on main. work/ is the dev shape: `plugins/demo/skills/
    <name>` symlinked at `primitives-core/skills/<name>`. Returns (work, origin) paths.
    """
    origin, work = os.path.join(root, "origin"), os.path.join(root, "work")

    for name in ("alpha", "beta"):
        write(os.path.join(origin, "plugins", "demo", "skills", name, "SKILL.md"), f"# {name}\n")
    write(os.path.join(origin, "plugins", "demo", ".claude-plugin", "plugin.json"), PLUGIN_JSON)
    git(_init(origin), "add", "-A")
    git(origin, "commit", "-qm", "publish: the fixture marketplace")

    for name in ("alpha", "beta"):
        write(os.path.join(work, "primitives-core", "skills", name, "SKILL.md"), f"# {name}\n")
        os.makedirs(os.path.join(work, "plugins", "demo", "skills"), exist_ok=True)
        os.symlink(
            os.path.join("..", "..", "..", "primitives-core", "skills", name),
            os.path.join(work, "plugins", "demo", "skills", name),
        )
    write(os.path.join(work, "plugins", "demo", ".claude-plugin", "plugin.json"), PLUGIN_JSON)
    git(_init(work), "add", "-A")
    git(work, "commit", "-qm", "feat(demo): ship alpha and beta")
    git(work, "remote", "add", "origin", origin)
    return work, origin


def _init(path):
    os.makedirs(path, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    return path


def remove_beta(work, message):
    """Delete the `beta` skill from both homes and commit it under `message`."""
    os.remove(os.path.join(work, "plugins", "demo", "skills", "beta"))
    shutil.rmtree(os.path.join(work, "primitives-core", "skills", "beta"))
    git(work, "add", "-A")
    git(work, "commit", "-qm", message)


def run_gate(work, **kwargs):
    """Drive main() against the fixture; returns (exit code, [output lines])."""
    lines = []
    code = R.main(
        plugins_dir=os.path.join(work, "plugins"),
        repo=work,
        tree=V.GitPublishedTree(repo=work),
        out=lines.append,
        **kwargs,
    )
    return code, lines


class UnitDerivation(unittest.TestCase):
    """A published path becomes a unit id; anything that is not a unit is ignored."""

    INDEX = {
        "demo": {
            "skills/alpha/SKILL.md": "a",
            "skills/alpha/references/deep.md": "b",
            "agents/scout.md": "c",
            "hooks/watcher/hook.py": "d",
            "hooks/watcher/config.json": "e",
            "commands/go.md": "f",
            "README.md": "g",
            ".claude-plugin/plugin.json": "h",
            "hooks.json": "i",
        }
    }

    def test_every_kind_collapses_to_one_unit_id(self):
        self.assertEqual(
            R.unit_ids(self.INDEX),
            {
                "demo/skills/alpha",
                "demo/agents/scout",
                "demo/hooks/watcher",
                "demo/commands/go",
            },
        )

    def test_non_unit_paths_are_not_units(self):
        self.assertEqual(R.unit_ids({"demo": {"README.md": "x", "hooks.json": "y"}}), set())

    def test_a_whole_plugin_removal_collapses_to_the_plugin_id(self):
        self.assertEqual(R.removed({}, self.INDEX), ["demo"])

    def test_a_member_removal_names_the_member(self):
        local = {"demo": {"skills/alpha/SKILL.md": "a"}}
        self.assertEqual(
            R.removed(local, self.INDEX),
            ["demo/agents/scout", "demo/commands/go", "demo/hooks/watcher"],
        )

    def test_nothing_removed_is_an_empty_list(self):
        self.assertEqual(R.removed(self.INDEX, self.INDEX), [])

    def test_an_added_unit_is_not_a_removal(self):
        local = dict(self.INDEX)
        local["extra"] = {"skills/new/SKILL.md": "z"}
        self.assertEqual(R.removed(local, self.INDEX), [])

    def test_pathspecs_cover_both_homes_and_the_md_suffix(self):
        self.assertEqual(
            R.pathspecs("demo/agents/scout"),
            [
                "plugins/demo/agents/scout",
                "plugins/demo/agents/scout.md",
                "primitives-core/agents/scout",
                "primitives-core/agents/scout.md",
            ],
        )
        self.assertEqual(R.pathspecs("demo"), ["plugins/demo"])


class DeclarationText(unittest.TestCase):
    """A declaration names the unit AND says it was removed, anywhere in the message."""

    UNIT = "solo-skills/skills/github-project-board"

    def test_id_plus_verb_anywhere_in_the_message_declares(self):
        self.assertTrue(
            R.is_declared("refactor: collapse things\n\ngithub-project-board is deleted.", self.UNIT)
        )

    def test_id_without_a_removal_verb_is_not_a_declaration(self):
        self.assertFalse(R.is_declared("refactor: rework github-project-board", self.UNIT))

    def test_a_removal_verb_naming_nothing_is_not_a_declaration(self):
        self.assertFalse(R.is_declared("chore: remove a stale fixture", self.UNIT))

    def test_matching_is_case_insensitive(self):
        self.assertTrue(R.is_declared("Retired GITHUB-PROJECT-BOARD", self.UNIT))

    def test_an_empty_message_is_not_a_declaration(self):
        self.assertFalse(R.is_declared("", self.UNIT))

    def test_a_whole_plugin_id_declares_on_its_own(self):
        self.assertTrue(R.is_declared("chore: delete the kaneo plugin", "kaneo"))


class NotesSection(unittest.TestCase):
    """The release-notes section: a heading plus one bullet per removal, or nothing."""

    def test_no_removals_prints_nothing(self):
        self.assertEqual(R.notes([]), "")

    def test_each_removal_is_a_bullet_carrying_its_declaring_subject(self):
        rows = [
            R.Removal("demo/skills/beta", "abc1234", "chore(demo): remove beta", "body", True),
            R.Removal("gone", "", "", "", False),
        ]
        text = R.notes(rows)
        self.assertIn(R.NOTES_HEADING, text)
        self.assertIn("- `demo/skills/beta` — chore(demo): remove beta", text)
        self.assertIn("- `gone` —", text)


class Unmeasurable(unittest.TestCase):
    """A published tree that cannot be read is RED, never green (decision-016 point 4)."""

    class DeadTree:
        note = ""

        def prepare(self):
            return "origin/main could not be resolved (fixture)"

        def index(self):  # pragma: no cover - never reached
            raise AssertionError("index() must not be called after prepare() declined")

    def test_an_unreadable_published_tree_exits_1(self):
        lines = []
        code = R.main(tree=self.DeadTree(), out=lines.append)
        self.assertEqual(code, 1)
        blob = "\n".join(lines)
        self.assertIn("✗", blob)
        self.assertIn("could not be resolved", blob)
        self.assertIn("NOT evidence", blob)

    def test_notes_mode_stays_silent_and_exits_0(self):
        lines = []
        self.assertEqual(R.main(tree=self.DeadTree(), notes_mode=True, out=lines.append), 0)
        self.assertEqual(lines, [])


@unittest.skipUnless(have_git(), "git is not on PATH")
class SyntheticRemovalRepo(unittest.TestCase):
    """End to end over real git: undeclared removal red, declared removal green."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="check-removals-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.work, self.origin = build_fixture(self.root)

    def test_clean_tree_is_green(self):
        code, lines = run_gate(self.work)
        self.assertEqual(code, 0, "\n".join(lines))
        self.assertIn("✓", "\n".join(lines))

    def test_undeclared_removal_is_red(self):
        remove_beta(self.work, "chore(demo): tidy up the assembly")
        code, lines = run_gate(self.work)
        blob = "\n".join(lines)
        self.assertEqual(code, 1, blob)
        self.assertIn("demo/skills/beta", blob)
        self.assertIn("✗", blob)

    def test_the_same_removal_is_green_once_the_message_declares_it(self):
        remove_beta(self.work, "chore(demo): tidy up the assembly")
        self.assertEqual(run_gate(self.work)[0], 1)
        git(self.work, "commit", "-q", "--amend", "-m",
            "refactor(demo): fold beta into alpha\n\nThe beta skill is removed; alpha absorbs it.")
        code, lines = run_gate(self.work)
        blob = "\n".join(lines)
        self.assertEqual(code, 0, blob)
        self.assertIn("demo/skills/beta", blob)  # green, but not silently

    def test_a_whole_plugin_removal_reports_once(self):
        shutil.rmtree(os.path.join(self.work, "plugins", "demo"))
        git(self.work, "add", "-A")
        git(self.work, "commit", "-qm", "chore: tidy")
        code, lines = run_gate(self.work)
        blob = "\n".join(lines)
        self.assertEqual(code, 1, blob)
        self.assertEqual(blob.count("- demo"), 1, blob)
        self.assertNotIn("demo/skills/alpha", blob)

    def test_notes_mode_prints_the_removal_and_exits_0(self):
        remove_beta(self.work, "refactor(demo): fold beta into alpha\n\nbeta is removed.")
        code, lines = run_gate(self.work, notes_mode=True)
        blob = "\n".join(lines)
        self.assertEqual(code, 0)
        self.assertIn(R.NOTES_HEADING, blob)
        self.assertIn("demo/skills/beta", blob)

    def test_notes_mode_prints_nothing_when_nothing_was_removed(self):
        code, lines = run_gate(self.work, notes_mode=True)
        self.assertEqual(code, 0)
        self.assertEqual(lines, [])

    def test_the_removing_commit_is_found_from_either_home(self):
        remove_beta(self.work, "chore(demo): drop beta")
        sha, message = R.find_removal("demo/skills/beta", repo=self.work)
        self.assertTrue(sha)
        self.assertIn("drop beta", message)


@unittest.skipUnless(have_git(), "git is not on PATH")
class RealHistoryDeclarations(unittest.TestCase):
    """The two squash-merged removals already on `dev` must read as declarations.

    They are why a declaration is prose in the commit message and not a trailer: neither
    carries one, and rewriting landed history to add one is not available.
    """

    def _message(self, sha):
        proc = subprocess.run(
            ["git", "-C", REPO, "log", "-1", "--format=%B", sha], capture_output=True, timeout=60
        )
        if proc.returncode != 0:
            self.skipTest(f"{sha} is not in this clone (shallow checkout)")
        return proc.stdout.decode("utf-8", "replace")

    def test_comm_kit_removal_declares(self):
        sha, unit = COMM_KIT
        self.assertTrue(R.is_declared(self._message(sha), unit))

    def test_github_project_board_removal_declares(self):
        sha, unit = GITHUB_PROJECT_BOARD
        self.assertTrue(R.is_declared(self._message(sha), unit))

    def test_the_live_tree_finds_that_commit_for_the_live_removal(self):
        sha, unit = GITHUB_PROJECT_BOARD
        self._message(sha)  # skips the test when the clone is shallow
        found, message = R.find_removal(unit, repo=REPO)
        if not found:
            self.skipTest("no deleting commit in this clone (shallow checkout)")
        self.assertTrue(found.startswith(sha), found)
        self.assertTrue(R.is_declared(message, unit))


if __name__ == "__main__":
    unittest.main()

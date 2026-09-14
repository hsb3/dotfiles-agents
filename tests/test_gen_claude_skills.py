"""gen_claude_skills unit tests (install-time Claude Code skill laydown, ADR 0017).

Covers the ship/exclude split (every roster entry lands on one side — the no-silent-caps
contract), --only subset selection and its hard errors, build determinism against the real
roster, verbatim skill copies, and the generated installer's real behaviour under `sh`:
marker-guarded refresh, idempotent re-runs, refusal to clobber a foreign skill dir, and
rejection of unknown arguments.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import gen_claude_skills as G  # noqa: E402
from check_roster import parse_roster  # noqa: E402
from gen_opencode import _identical  # noqa: E402

TWO = ["comment-hygiene", "mermaid"]


def roster():
    return parse_roster(os.path.join(REPO, "primitives-core.yaml"))


class TestOnly(unittest.TestCase):
    def _out(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return os.path.join(d, "lane")

    def test_subset_selection(self):
        out = self._out()
        self.assertEqual(G.main(["--out", out, "--only", ",".join(TWO)]), 0)
        self.assertEqual(sorted(os.listdir(os.path.join(out, "skills"))), sorted(TWO))

    def test_unknown_id_is_an_error(self):
        self.assertEqual(G.main(["--out", self._out(), "--only", "no-such-skill"]), 1)

    def test_empty_parse_is_an_error_not_a_full_install(self):
        # `--only ,` used to fall through to "no filter": asking for a subset and getting
        # every skill is the worst possible answer, so it must fail instead.
        for value in (",", "", " , "):
            self.assertEqual(G.main(["--out", self._out(), "--only", value]), 1, value)

    def test_excluded_skill_reports_its_reason(self):
        # carbon-builder requires hosted-mcp: it is excluded, so --only must fail loudly
        # AND say why, never silently install nothing.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(G.main(["--out", self._out(), "--only", "carbon-builder"]), 1)
        text = buf.getvalue()
        self.assertIn("carbon-builder", text)
        self.assertIn("hosted-mcp", text)


class TestCarriers(unittest.TestCase):
    """An exclusion reason points somewhere that actually fixes the problem."""

    def test_only_assemblies_providing_the_capability_are_named(self):
        # carbon is the only assembly that both ships carbon-builder and registers the
        # MCP server it needs; a bundle without the server would land a dead skill.
        where = G.carriers("carbon-builder", ["hosted-mcp"])
        self.assertIn("carbon", where)
        self.assertNotIn("solo-skills", where)


class TestBuild(unittest.TestCase):
    def test_two_builds_identical(self):
        entries = roster()
        a, b = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, a, True)
        self.addCleanup(shutil.rmtree, b, True)
        self.assertEqual(G.build(a, entries), [])
        self.assertEqual(G.build(b, entries), [])
        self.assertTrue(_identical(a, b))

    def test_skill_copied_verbatim(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        self.assertEqual(G.build(d, roster(), only=["mermaid"]), [])
        with open(os.path.join(d, "skills", "mermaid", "SKILL.md"), "rb") as fh:
            got = fh.read()
        with open(os.path.join(REPO, "primitives-core/skills/mermaid/SKILL.md"), "rb") as fh:
            self.assertEqual(got, fh.read())

    def test_install_sh_is_executable(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        self.assertEqual(G.build(d, roster(), only=["mermaid"]), [])
        self.assertTrue(os.access(os.path.join(d, "install.sh"), os.X_OK))

    def test_out_refuses_non_empty_dir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "occupied.txt"), "w") as fh:
            fh.write("x")
        self.assertEqual(G.main(["--out", d]), 1)


class TestExclusionsManifest(unittest.TestCase):
    """Every roster entry is either shipped or listed with a reason — no silent skips."""

    def test_synthetic_entries_all_appear(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        entries = [
            {"id": "scout", "type": "agent",
             "source": "primitives-core/agents/scout.md", "targets": "[claude-code]"},
            {"id": "carbon-builder", "type": "skill",
             "source": "primitives-core/skills/carbon-builder",
             "targets": "[claude-code]", "requires": "[hosted-mcp]"},
            {"id": "mermaid", "type": "skill",
             "source": "primitives-core/skills/mermaid", "targets": "[opencode]"},
        ]
        self.assertEqual(G.build(d, entries), [])
        with open(os.path.join(d, "README.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertRegex(readme, r"\| `scout` \| agent \| not a skill")
        self.assertRegex(readme, r"\| `carbon-builder` \| skill \|.*hosted-mcp")
        self.assertRegex(readme, r"\| `mermaid` \| skill \| roster targets do not include claude-code")
        self.assertFalse(os.path.isdir(os.path.join(d, "skills")))


class TestInstaller(unittest.TestCase):
    """The generated install.sh, run for real under `sh`."""

    def setUp(self):
        self.lane = os.path.join(tempfile.mkdtemp(), "lane")
        self.addCleanup(shutil.rmtree, os.path.dirname(self.lane), True)
        self.assertEqual(G.main(["--out", self.lane, "--only", "mermaid"]), 0)
        self.proj = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.proj, True)
        self.dest = os.path.join(self.proj, ".claude", "skills", "mermaid")

    def _run(self, *args):
        return subprocess.run(
            ["sh", os.path.join(self.lane, "install.sh"), *args],
            capture_output=True, text=True,
        )

    def test_project_laydown_and_idempotent_rerun(self):
        r = self._run("--project", self.proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(self.dest, ".laydown")))
        again = self._run("--project", self.proj)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.dest, "SKILL.md")))

    def test_refuses_unmarked_directory(self):
        os.makedirs(self.dest)
        with open(os.path.join(self.dest, "SKILL.md"), "w") as fh:
            fh.write("hand-authored\n")
        r = self._run("--project", self.proj)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(self.dest, r.stderr)
        with open(os.path.join(self.dest, "SKILL.md")) as fh:
            self.assertEqual(fh.read(), "hand-authored\n")

    def test_rejects_unknown_argument(self):
        r = self._run("--project", self.proj, "--only", "mermaid")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(self.dest))
        self.assertNotEqual(self._run("--global", "--wat").returncode, 0)


class TestWrapper(unittest.TestCase):
    """scripts/install_claude_skills.sh — the --only rotation and its usage errors. A
    ${2:?} bail here exits 0, because the EXIT trap's rm resets $? under macOS sh."""

    WRAPPER = os.path.join(REPO, "scripts", "install_claude_skills.sh")

    def _proj(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def _run(self, *args):
        return subprocess.run([self.WRAPPER, *args], capture_output=True, text=True)

    def test_only_rotates_out_in_either_position(self):
        for argv in (["--only", "mermaid", "--project", None],
                     ["--project", None, "--only", "mermaid"]):
            proj = self._proj()
            argv = [proj if a is None else a for a in argv]
            r = self._run(*argv)
            self.assertEqual(r.returncode, 0, r.stderr)
            skills = os.path.join(proj, ".claude", "skills")
            self.assertTrue(os.path.isfile(os.path.join(skills, "mermaid", "SKILL.md")))
            self.assertEqual(os.listdir(skills), ["mermaid"])

    def test_duplicate_only_is_rejected(self):
        proj = self._proj()
        r = self._run("--only", "mermaid", "--only", "diagrams", "--project", proj)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(proj, ".claude")))

    def test_only_without_a_value_fails_nonzero(self):
        self.assertNotEqual(self._run("--only").returncode, 0)

    def test_empty_only_does_not_install_everything(self):
        proj = self._proj()
        r = self._run("--only", "", "--project", proj)
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(proj, ".claude")))


if __name__ == "__main__":
    unittest.main()

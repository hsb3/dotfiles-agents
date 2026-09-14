"""The generated opencode install.sh must leave a readable record and an honest report.

The lane builds into a tempdir that `scripts/install_opencode.sh` deletes on exit, so the
exclusions manifest (the generated README) has to be copied into $ROOT before that happens
or the user never sees what was left behind. These tests run the generated installer over a
fixture lane in a tempdir — no repo build, no network.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import gen_opencode as G  # noqa: E402

LANE_README = "# opencode lane\n\n## Not in this lane (and why)\n\n| `some-hook` | hook | unsupported |\n"


class TestLaydownRecord(unittest.TestCase):
    def _lane(self, skills=("alpha", "beta"), agents=("scout",)):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        lane = os.path.join(d, "lane")
        os.makedirs(os.path.join(lane, "skills"))
        os.makedirs(os.path.join(lane, "agents"))
        for s in skills:
            os.makedirs(os.path.join(lane, "skills", s))
            with open(os.path.join(lane, "skills", s, "SKILL.md"), "w") as fh:
                fh.write(f"---\nname: {s}\n---\nbody\n")
        for a in agents:
            with open(os.path.join(lane, "agents", f"{a}.md"), "w") as fh:
                fh.write("---\nmode: subagent\n---\nbody\n")
        with open(os.path.join(lane, "README.md"), "w") as fh:
            fh.write(LANE_README)
        with open(os.path.join(lane, "install.sh"), "w") as fh:
            fh.write(G.INSTALL_SH)
        os.chmod(os.path.join(lane, "install.sh"), 0o755)
        return d, lane

    def _install(self, lane, project):
        return subprocess.run(
            ["sh", os.path.join(lane, "install.sh"), "--project", project],
            capture_output=True, text=True, check=True,
        )

    def test_record_is_readable_in_root(self):
        d, lane = self._lane()
        project = os.path.join(d, "proj")
        self._install(lane, project)
        root = os.path.join(project, ".opencode")
        records = [f for f in os.listdir(root) if f.endswith(".md")]
        self.assertEqual(len(records), 1, f"expected one laydown record in {root}, got {records}")
        with open(os.path.join(root, records[0]), encoding="utf-8") as fh:
            self.assertIn("Not in this lane (and why)", fh.read())

    def test_closing_line_names_counts_and_hooks(self):
        d, lane = self._lane(skills=("alpha", "beta", "gamma"), agents=("scout", "builder"))
        project = os.path.join(d, "proj")
        out = self._install(lane, project).stdout
        self.assertIn("skills: 3", out)
        self.assertIn("agents: 2", out)
        self.assertIn("hooks", out.lower())
        self.assertNotIn("(skills/ + agents/)", out)

    def test_counts_are_zero_when_lane_is_empty(self):
        # An unmatched shell glob expands to its literal pattern; a counter that walks it
        # blind reports 1 skill for an empty lane (and `cp` on it fails the install).
        d, lane = self._lane(skills=(), agents=())
        project = os.path.join(d, "proj")
        out = self._install(lane, project).stdout
        self.assertIn("skills: 0", out)
        self.assertIn("agents: 0", out)


if __name__ == "__main__":
    unittest.main()

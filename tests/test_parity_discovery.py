"""Exercise the parity recipe with disposable sibling layouts and a recording bun."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ParityDiscovery(unittest.TestCase):
    def test_sibling_selection(self):
        for layout in ("nested", "direct", "both", "missing", "override", "bad-override", "gate-failure"):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp) / "home with spaces"
                nested = home / "Developer/_hsb3/dotfiles-agents-oc"
                direct = home / "Developer/dotfiles-agents-oc"
                override = home / "explicit peer"
                for directory in {
                    "nested": [nested], "direct": [direct], "both": [nested, direct],
                    "missing": [], "override": [nested, direct, override],
                    "bad-override": [nested, direct], "gate-failure": [direct],
                }[layout]:
                    directory.mkdir(parents=True)
                makefile = Path(tmp) / "Makefile"
                makefile.write_text((ROOT / "Makefile").read_text().replace("$(HOME)", str(home)))
                bun = Path(tmp) / "bun"
                bun.write_text('#!/bin/sh\nprintf "%s\\n" "$ATELIER_CC_REPO" "$@"\n'
                               '[ -d "$2" ] || exit 7\n'
                               'exit "${PARITY_TEST_EXIT:-0}"\n')
                bun.chmod(0o755)
                command = ["make", "--no-print-directory", "-f", str(makefile), "parity"]
                if layout in ("override", "bad-override"):
                    command.append(f"ATELIER_OC_REPO={override}")
                env = {**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}"}
                env.pop("ATELIER_OC_REPO", None)
                env["PARITY_TEST_EXIT"] = "9" if layout == "gate-failure" else "0"
                result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
                if layout == "missing":
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(str(nested), result.stderr)
                    self.assertIn(str(direct), result.stderr)
                elif layout in ("bad-override", "gate-failure"):
                    self.assertNotEqual(result.returncode, 0)
                    expected = override if layout == "bad-override" else direct
                    self.assertEqual(result.stdout.splitlines(), [str(ROOT), "--cwd", str(expected), "gate/parity.ts"])
                else:
                    expected = override if layout == "override" else direct if layout == "direct" else nested
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.splitlines(), [str(ROOT), "--cwd", str(expected), "gate/parity.ts"])


if __name__ == "__main__":
    unittest.main()

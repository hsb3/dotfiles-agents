"""Carbon website attribution must travel with the installed skill."""

from pathlib import Path
import hashlib
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CarbonAttributionTests(unittest.TestCase):
    def test_published_assembly_carries_website_notice(self):
        with tempfile.TemporaryDirectory() as directory:
            assembly = Path(directory) / "carbon"
            shutil.copytree(ROOT / "plugins/carbon", assembly, symlinks=False)
            skill = assembly / "skills/carbon-builder"
            readme = (skill / "README.md").read_text()
            prompting = (skill / "references/prompting.md").read_text()
            self.assertIn("Copyright 2018 IBM Corp.", readme)
            self.assertIn("996791935ba9edc7977fc12d7b16548181402c14", readme)
            self.assertIn("static/llms.txt", readme)
            self.assertIn("996791935ba9edc7977fc12d7b16548181402c14", prompting)
            self.assertEqual(
                hashlib.sha256((skill / "references/carbon-llms.txt").read_bytes()).hexdigest(),
                "c375aa34beb4eb5d0ff04e01ff90ac8f50ca2562de0276e089bcbd43564de8e9",
            )
            self.assertIn("Modified", prompting)
            self.assertIn("Copyright 2018 IBM Corp.", prompting)
            self.assertIn("../LICENSE", prompting)
            self.assertIn("TERMS AND CONDITIONS", (skill / "LICENSE").read_text())
            self.assertFalse((skill / "LICENSE").is_symlink())


if __name__ == "__main__":
    unittest.main()

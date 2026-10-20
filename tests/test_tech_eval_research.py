"""tech-eval-research ships its artifact schemas, starter and validator, and documents them.

Stdlib only: the validator's own behaviour needs jsonschema and pyyaml, so it is checked by
running it, not here. These checks catch a missing or renamed file and prose that stops
pointing at the validator.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "tech-eval-research")
SCHEMAS = ("requirements", "eval-rubric", "landscape", "findings", "runs")
STARTER = (
    "data/requirements.yaml",
    "data/eval-rubric.yaml",
    "data/findings/.gitkeep",
    "runs/.gitkeep",
    "docs/report.md",
    ".gitignore",
)


def read(*parts):
    with open(os.path.join(SKILL, *parts), encoding="utf-8") as handle:
        return handle.read()


class TechEvalResearchArtifacts(unittest.TestCase):
    def test_every_schema_ships_as_json_schema_2020_12(self):
        for name in SCHEMAS:
            with self.subTest(schema=name):
                self.assertIn("json-schema.org/draft/2020-12", read("references", "schemas", f"{name}.schema.yaml"))

    def test_starter_ships_every_file(self):
        for rel in STARTER:
            with self.subTest(file=rel):
                self.assertTrue(os.path.isfile(os.path.join(SKILL, "references", "starter", rel)))

    def test_starter_report_names_no_missing_make_target(self):
        self.assertNotIn("make ", read("references", "starter", "docs", "report.md"))

    def test_scripts_ship_and_validate_is_executable(self):
        self.assertTrue(os.access(os.path.join(SKILL, "scripts", "validate.py"), os.X_OK))
        self.assertTrue(os.path.isfile(os.path.join(SKILL, "scripts", "evalkit.py")))
        self.assertNotIn('__name__ == "__main__"', read("scripts", "evalkit.py"))

    def test_docs_describe_layout_and_validator(self):
        for doc in ("SKILL.md", "README.md"):
            text = read(doc)
            with self.subTest(doc=doc):
                for needle in ("## Artifact layout", "scripts/validate.py", "--root",
                               "data/requirements.yaml", "data/findings/", "runs.jsonl",
                               "references/starter", "references/schemas", "eval.toml"):
                    self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

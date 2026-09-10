"""Runtime reports explain filtering without exposing retired records."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPORT = Path(__file__).resolve().parents[1] / "evals" / "report.py"


class ReportCountsTest(unittest.TestCase):
    def test_generated_documents_count_suppressed_rows_once(self):
        for retired in (False, True):
            with self.subTest(retired=retired), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                collections = {
                    "frameworks": [{"id": "fw", "slug": "hsb3-jobs-to-be-done"}],
                    "framework_elements": [{"id": "job", "framework": "fw",
                                            "slug": "work", "category": "build",
                                            "sort_order": 0}],
                    "extenders": [
                        {"id": "a", "slug": "active-a", "kind": "skill"},
                        {"id": "b", "slug": "active-b", "kind": "skill", "retired": False},
                        {"id": "c", "slug": "hidden-c", "kind": "skill", "retired": retired},
                        {"id": "d", "slug": "hidden-d", "kind": "skill", "retired": retired},
                    ],
                    "assessments": [
                        {"extender": ext, "framework": "fw", "element": "job",
                         "assessor": "coverage-v1", "verdict": "present", "eval_run": "run"}
                        for ext in ("a", "c", "d", "d")
                    ],
                    "relationships": [
                        {"extender_a": a, "extender_b": b, "kind": "duplicative",
                         "evidence": evidence, "eval_run": "run"}
                        for a, b, evidence in (("a", "b", "active evidence"),
                                               ("c", "a", "hidden left evidence"),
                                               ("a", "d", "hidden right evidence"),
                                               ("c", "d", "hidden both evidence"))
                    ],
                    "sources": [], "job_coverage": [],
                    "eval_runs": [{"id": "run", "slug": "fixture-run",
                                   "kind": "coverage", "status": "complete"}],
                }
                for name, rows in collections.items():
                    (root / f"{name}.json").write_text(json.dumps(rows), encoding="utf-8")
                command = [sys.executable, str(REPORT), "--fixtures", str(root),
                           "--out", str(root / "out")]
                subprocess.run(command, check=True, capture_output=True, text=True)
                expected = (
                    "Retired units excluded: **2**. Suppressed rows: **3 assessments**, "
                    "**3 relationships**." if retired else
                    "Retired units excluded: **0**. Suppressed rows: **0 assessments**, "
                    "**0 relationships**."
                )
                outputs = {}
                for name in ("coverage-matrix.md", "analysis.md"):
                    content = (root / "out" / name).read_text(encoding="utf-8")
                    outputs[name] = content
                    self.assertIn(expected, content)
                    self.assertIn("active-a", content)
                    self.assertIn("active evidence", content)
                    if retired:
                        self.assertNotIn("hidden-", content)
                        self.assertNotIn("hidden left evidence", content)
                        self.assertNotIn("hidden right evidence", content)
                        self.assertNotIn("hidden both evidence", content)
                self.assertIn("(1 jobs, 1 families) x " + ("2" if retired else "4")
                              + " extenders.", outputs["coverage-matrix.md"])
                self.assertIn("| `fixture-run` | coverage | complete | "
                              + ("1 | 0 | 1 | 2 |" if retired else "4 | 0 | 4 | 8 |"),
                              outputs["analysis.md"])
                subprocess.run(command, check=True, capture_output=True, text=True)
                for name, content in outputs.items():
                    self.assertEqual((root / "out" / name).read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()

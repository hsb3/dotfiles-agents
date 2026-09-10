import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "evals" / "usage_digest.py"
sys.path.insert(0, str(ROOT / "evals"))
import usage_digest


def observed(observation_id, total=10, **extra):
    row = {
        "schema": "codex-usage", "schema_version": 2, "kind": "delta",
        "counter_state": "observed", "observation_id": observation_id,
        "native_id": "child", "parent_id": "root", "lifecycle_id": "child-life",
        "role": "atelier-builder", "model": "gpt-test", "host": "mac",
        "source_repo": "/repo", "tokens": {"input": total - 4, "cached_input": min(2, total - 4),
        "output": 4, "reasoning": 1, "total": total},
        "cumulative_tokens": {"input": 100, "cached_input": 20, "output": 50,
        "reasoning": 10, "total": 150}, "timing": {"lifetime_ms": 20},
    }
    row.update(extra)
    return row


class UsageDigestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "usage.jsonl"

    def write(self, *rows):
        self.path.write_text("\n".join(json.dumps(row) if not isinstance(row, str) else row for row in rows))

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(CLI), *args], text=True, capture_output=True)

    def report(self, *inputs):
        run = self.invoke("report", *(item for path in inputs for item in ("--input", str(path))))
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_root_child_totals_and_replay_use_deltas_not_cumulative(self):
        self.write(observed("one", 10), observed("two", 7, native_id="root", parent_id=None,
                                                    lifecycle_id="root-life", timing={"lifetime_ms": 30}))
        report = usage_digest.digest([self.path, self.path])
        self.assertEqual(report["tokens"]["total"], 17)
        self.assertEqual(report["observed"], 2)
        self.assertEqual(report["groups"]["root_child"]["root/child"]["total"], 10)
        self.assertEqual(report["lifetime_ms_by_lifecycle"], {"child-life": 20, "root-life": 30})

    def test_reset_resume_and_model_changes_count_each_observed_delta(self):
        self.write(observed("one", 10), {"schema": "codex-usage", "schema_version": 2, "kind": "delta",
                                           "counter_state": "reset", "observation_id": "reset"},
                   observed("two", 5, model="gpt-next"))
        report = self.report(self.path)
        self.assertEqual(report["tokens"]["total"], 15)
        self.assertEqual(report["groups"]["model"]["gpt-next"]["total"], 5)
        self.assertEqual(report["coverage"]["states"]["reset"], 1)

    def test_invalid_future_missing_and_conflicting_rows_are_visible(self):
        bad = observed("bad", 10, tokens={"input": -1})
        future = observed("future", 10, schema_version=3)
        clash = observed("one", 11)
        self.write(observed("one", 10), clash, bad, future, "not-json",
                   {"event": "delegation", "ctx_tokens": 999})
        report = self.report(self.path)
        self.assertEqual(report["tokens"]["total"], 10)
        self.assertEqual(report["coverage"]["errors"]["conflicting-observation-id"], 1)
        self.assertEqual(report["coverage"]["errors"]["malformed-json"], 1)
        self.assertEqual(report["coverage"]["errors"]["invalid-tokens"], 1)
        self.assertEqual(report["coverage"]["errors"]["unsupported-future-schema"], 1)
        self.assertEqual(report["legacy_unknown"], 1)

    def test_export_reimports_safely_and_excludes_prompts(self):
        self.write(observed("one", 10, prompt="secret", host="mac"), observed("two", 5, host="linux"))
        exported = Path(self.temp.name) / "mac.jsonl"
        run = self.invoke("export", "--input", str(self.path), "--host", "mac", "--output", str(exported))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("secret", exported.read_text())
        report = self.report(exported, exported)
        self.assertEqual(report["tokens"]["total"], 10)
        self.assertEqual(report["observed"], 1)

    def test_host_repo_and_missing_coverage_are_grouped_explicitly(self):
        self.write(observed("one", 10), observed("two", 6, host=None, source_repo=None,
                                                    model=None, timing={}))
        report = self.report(self.path)
        self.assertEqual(report["groups"]["host"]["mac"]["total"], 10)
        self.assertEqual(report["groups"]["source_repo"]["unknown"]["total"], 6)
        self.assertEqual(report["coverage"]["missing"],
                         {"host": 1, "lifetime_ms": 1, "model": 1, "source_repo": 1})


if __name__ == "__main__":
    unittest.main()

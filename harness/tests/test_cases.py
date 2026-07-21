"""Case loader — the flattened cases/<candidate>/<case-id>/ layout (DESIGN §3)."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_harness.cases import load_cases  # noqa: E402


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


class TestLoadCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)

    def _case(self, cid, payload):
        # New layout: <cases_dir>/<candidate>/<case-id>/case.json (no inner cases/).
        d = os.path.join(self.tmp, "cand", cid)
        _write(os.path.join(d, "case.json"), json.dumps(payload))

    def test_loads_and_orders(self):
        self._case("a", {"prompt": "p1", "assertions": [{"id": "x", "text": "t"}]})
        self._case("b", {"prompt": "p2"})
        cases = load_cases("cand", self.tmp)
        self.assertEqual([c["id"] for c in cases], ["a", "b"])
        self.assertTrue(cases[0]["dir"].endswith(os.path.join("cand", "a")))

    def test_only_filter(self):
        self._case("a", {"prompt": "p1"})
        self._case("b", {"prompt": "p2"})
        cases = load_cases("cand", self.tmp, only="b")
        self.assertEqual([c["id"] for c in cases], ["b"])

    def test_missing_dataset_exits(self):
        with self.assertRaises(SystemExit):
            load_cases("nope", self.tmp)

    def test_missing_prompt_exits(self):
        self._case("a", {"assertions": []})
        with self.assertRaises(SystemExit):
            load_cases("cand", self.tmp)

    def test_bad_assertion_exits(self):
        self._case("a", {"prompt": "p", "assertions": [{"id": "x"}]})
        with self.assertRaises(SystemExit):
            load_cases("cand", self.tmp)

    def test_only_filter_no_match_exits(self):
        self._case("a", {"prompt": "p1"})
        with self.assertRaises(SystemExit):
            load_cases("cand", self.tmp, only="nonexistent")


if __name__ == "__main__":
    unittest.main()

"""Tests for the owner-signoff form builder
(primitives-core/skills/owner-signoff/scripts/build_signoff.py).

Stdlib-only: JSON specs cover the render path; the YAML branch is exercised only
when PyYAML happens to be installed.
"""

import json
import os
import pathlib
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "primitives-core", "skills", "owner-signoff", "scripts"))

import build_signoff as bs  # noqa: E402


def spec(**over):
    base = {
        "title": "Sign-off — test batch",
        "items": [
            {
                "question": "Delete the branch?",
                "context": "It is merged.",
                "recommendation": "Delete it.",
            }
        ],
    }
    base.update(over)
    return base


class Validate(unittest.TestCase):
    def test_minimal_spec_is_clean(self):
        self.assertEqual(bs.validate(spec()), [])

    def test_missing_required_fields(self):
        errs = bs.validate({"items": [{}]})
        joined = "\n".join(errs)
        self.assertIn("title", joined)
        for key in ("question", "context", "recommendation"):
            self.assertIn(f"items[0].{key}", joined)

    def test_empty_items_rejected(self):
        self.assertTrue(any("items" in e for e in bs.validate(spec(items=[]))))

    def test_unknown_keys_rejected(self):
        s = spec(bogus=1)
        s["items"][0]["typo_field"] = "x"
        joined = "\n".join(bs.validate(s))
        self.assertIn("bogus", joined)
        self.assertIn("items[0].typo_field", joined)

    def test_duplicate_and_reserved_ids(self):
        item = spec()["items"][0]
        s = spec(items=[dict(item, id="A"), dict(item, id="A"), dict(item, id="Z")])
        joined = "\n".join(bs.validate(s))
        self.assertIn("duplicate", joined)
        self.assertIn("reserved", joined)

    def test_choices_need_two_entries(self):
        s = spec()
        s["items"][0]["choices"] = ["Only one"]
        self.assertTrue(any("choices" in e for e in bs.validate(s)))

    def test_summary_shape(self):
        errs = bs.validate(spec(summary={"done": ["ok"], "nope": []}))
        self.assertTrue(any("summary.nope" in e for e in errs))


class Render(unittest.TestCase):
    def test_auto_ids_skip_explicit(self):
        item = spec()["items"][0]
        ids = bs.resolve_ids([dict(item), dict(item, id="A"), dict(item)])
        self.assertEqual(ids, ["B", "A", "C"])

    def test_render_escapes_and_preselects(self):
        s = spec(
            project="proj<x>",
            date="2026-08-26",
            summary={"done": ["Roster <migrated>"], "waiting": ["Items below"]},
        )
        s["items"][0]["question"] = 'Delete "old" <branch>?'
        s["items"][0]["text_field"] = "New name…"
        page = bs.render(s)
        self.assertNotIn("<branch>", page)
        self.assertIn("Delete &quot;old&quot; &lt;branch&gt;?", page)
        self.assertIn("Roster &lt;migrated&gt;", page)
        self.assertIn('value="Approve" checked', page)
        self.assertIn('name="A_text"', page)
        self.assertIn('data-id="Z"', page)
        self.assertNotIn("{{", page)  # every placeholder replaced

    def test_summary_omitted_when_absent(self):
        self.assertNotIn("Where things stand", bs.render(spec()))


class EndToEnd(unittest.TestCase):
    def test_json_spec_builds_index_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "signoff.json"
            p.write_text(json.dumps(spec()))
            loaded = bs.load_spec(p)
            self.assertEqual(bs.validate(loaded), [])
            (p.parent / "index.html").write_text(bs.render(loaded))
            self.assertIn("Sign-off — test batch", (p.parent / "index.html").read_text())

    def test_yaml_spec_when_pyyaml_present(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed")
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "signoff.yaml"
            p.write_text("title: Yaml batch\nitems:\n  - question: Q?\n    context: C.\n    recommendation: R.\n")
            loaded = bs.load_spec(p)
            self.assertEqual(bs.validate(loaded), [])
            self.assertIn("Yaml batch", bs.render(loaded))


if __name__ == "__main__":
    unittest.main()

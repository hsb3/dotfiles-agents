"""board_health's six decay checks: each one firing, and each one silent on a clean board.

Both halves matter equally. A check that never fires is the failure this tool exists to fix
(kata-audit reported all-clear on a board where 34 of 55 items shared one priority band), and
a check that always fires trains the reader to ignore the report — so every check is pinned
against a board built to trip it AND against one built not to.

The malformed-input path is pinned too: a snapshot the tool cannot read must exit 2, never
exit 0 having measured nothing.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "primitives-core", "skills", "board-triage")

sys.path.insert(0, os.path.join(SKILL, "scripts"))

import board_health as bh  # noqa: E402


def item(key, title="a plain title", priority="P1", labels=("infra",), state="open"):
    return {
        "key": key,
        "id": key,
        "title": title,
        "state": state,
        "labels": list(labels),
        "fields": {"priority": priority},
    }


def snapshot(items, label_options=("infra", "docs")):
    return {
        "board": {"name": "demo", "backend": "kata"},
        "fields": {
            "priority": {"options": ["P0", "P1", "P2", "P3"]},
            "labels": {"options": list(label_options)},
        },
        "items": list(items),
    }


CLEAN_ITEMS = [
    item("a1", "one thing", "P0", ["infra"]),
    item("a2", "two thing", "P0", ["docs"]),
    item("a3", "three thing", "P1", ["infra"]),
    item("a4", "four thing", "P1", ["docs"]),
    item("a5", "five thing", "P2", ["infra"]),
    item("a6", "six thing", "P3", ["docs"]),
]


def clean():
    return snapshot(CLEAN_ITEMS)


def findings_by_id(snap, **kwargs):
    return {f["check"]: f for f in bh.analyze(snap, **kwargs)}


class CleanBoard(unittest.TestCase):
    def test_no_check_fires(self):
        self.assertEqual([], bh.analyze(clean()))

    def test_the_largest_band_at_exactly_half_is_not_skew(self):
        """>50%, not >=50% — a two-band board split down the middle still discriminates."""
        items = [item(f"b{n}", priority="P0") for n in range(3)]
        items += [item(f"c{n}", priority="P1") for n in range(3)]
        self.assertNotIn("priority-skew", findings_by_id(snapshot(items)))

    def test_done_items_are_invisible_to_every_check(self):
        """A closed board full of decay is not decay; the checks measure open work only."""
        rotten = [
            item(f"d{n}", f"area{n}: closed", priority=None, labels=[], state="done")
            for n in range(20)
        ]
        self.assertEqual([], bh.analyze(snapshot(CLEAN_ITEMS + rotten)))


class PrioritySkew(unittest.TestCase):
    def test_a_dominant_band_fires_and_reports_the_distribution(self):
        items = [item(f"p{n}", priority="P2") for n in range(7)]
        items += [item("q1", priority="P0"), item("q2", priority="P1")]
        found = findings_by_id(snapshot(items))["priority-skew"]
        self.assertEqual("fail", found["severity"])
        self.assertIn("P2", found["finding"])
        self.assertIn("7", found["finding"])
        self.assertEqual({"P2": 7, "P0": 1, "P1": 1}, found["distribution"])
        self.assertEqual(7, len(found["affected"]), "the dominant band's items are the subject")

    def test_unset_counts_as_a_band(self):
        """An all-blank board is skewed too; hiding nulls would make the share lie."""
        items = [item(f"p{n}", priority=None) for n in range(7)] + [item("q1", priority="P0")]
        found = findings_by_id(snapshot(items))["priority-skew"]
        self.assertIn(bh.UNSET, found["distribution"])
        self.assertEqual(7, found["distribution"][bh.UNSET])

    def test_the_threshold_is_tunable(self):
        items = [item(f"p{n}", priority="P2") for n in range(3)]
        items += [item(f"q{n}", priority="P1") for n in range(3)]
        self.assertNotIn("priority-skew", findings_by_id(snapshot(items)))
        self.assertIn("priority-skew", findings_by_id(snapshot(items), skew_threshold=0.4))


class PriorityMissing(unittest.TestCase):
    def test_null_priority_is_reported(self):
        items = CLEAN_ITEMS + [item("z1", priority=None), item("z2", priority="  ")]
        found = findings_by_id(snapshot(items))["priority-missing"]
        self.assertEqual("fail", found["severity"])
        self.assertEqual(["z1", "z2"], found["affected"])

    def test_a_missing_fields_block_is_missing_priority_not_a_crash(self):
        broken = {"key": "z9", "title": "t", "state": "open", "labels": ["infra"]}
        self.assertIn("priority-missing", findings_by_id(snapshot(CLEAN_ITEMS + [broken])))


class GroupingMissing(unittest.TestCase):
    def test_items_with_no_labels_are_reported(self):
        items = CLEAN_ITEMS + [item("z1", labels=[]), item("z2", labels=[])]
        found = findings_by_id(snapshot(items))["grouping-missing"]
        self.assertEqual("fail", found["severity"])
        self.assertEqual(["z1", "z2"], found["affected"])


class GroupingLatent(unittest.TestCase):
    def latent_items(self):
        """Half the board groups itself in title prefixes no label vocabulary knows."""
        return [
            item("l1", "kaneo: import the labels", labels=["infra"]),
            item("l2", "kaneo: document the cleanup", labels=["infra"]),
            item("l3", "sop: author the config guide", labels=["docs"]),
            item("l4", "skills: retire the aggregate", labels=["docs"]),
            item("l5", "no prefix here", labels=["infra"]),
            item("l6", "also no prefix", labels=["docs"]),
        ]

    def test_prefixes_absent_from_the_vocabulary_fire(self):
        found = findings_by_id(snapshot(self.latent_items()))["grouping-latent"]
        self.assertEqual("warn", found["severity"])
        self.assertEqual({"kaneo": 2, "sop": 1, "skills": 1}, found["prefixes"])
        self.assertEqual(["l1", "l2", "l3", "l4"], found["affected"])

    def test_prefixes_already_in_the_vocabulary_do_not_fire(self):
        """The convention is queryable — that is the fixed state, not a finding."""
        snap = snapshot(self.latent_items(), label_options=["infra", "docs", "kaneo", "sop"])
        self.assertNotIn("grouping-latent", findings_by_id(snap))

    def test_a_namespaced_label_covers_a_bare_prefix(self):
        snap = snapshot(self.latent_items(), label_options=["infra", "docs", "area:kaneo", "sop"])
        self.assertNotIn("grouping-latent", findings_by_id(snap))

    def test_too_few_prefixed_items_is_not_a_convention(self):
        items = [item(f"n{n}", "plain title") for n in range(8)]
        items.append(item("p1", "kaneo: one lonely prefix"))
        self.assertNotIn("grouping-latent", findings_by_id(snapshot(items)))

    def test_the_prefix_threshold_is_tunable(self):
        items = [item(f"n{n}", "plain title") for n in range(8)]
        items += [item("p1", "kaneo: one"), item("p2", "sop: two")]
        self.assertNotIn("grouping-latent", findings_by_id(snapshot(items)))
        self.assertIn("grouping-latent", findings_by_id(snapshot(items), prefix_threshold=0.2))

    def test_only_lowercase_slug_prefixes_count(self):
        for title in ("Kaneo: capitalised", "TODO: shouting", "note - not a colon", "http://x"):
            with self.subTest(title=title):
                self.assertIsNone(bh.title_prefix(title))
        self.assertEqual("kaneo-import", bh.title_prefix("kaneo-import: hyphens are fine"))


class VocabularyFossils(unittest.TestCase):
    def test_declared_labels_on_no_open_item_are_reported(self):
        snap = snapshot(CLEAN_ITEMS, label_options=["infra", "docs", "kaneo-status:to-do", "epic"])
        found = findings_by_id(snap)["vocabulary-fossils"]
        self.assertEqual("warn", found["severity"])
        self.assertEqual(["epic", "kaneo-status:to-do"], found["affected"])

    def test_a_label_used_only_by_a_done_item_is_still_a_fossil(self):
        snap = snapshot(
            CLEAN_ITEMS + [item("d1", labels=["epic"], state="done")],
            label_options=["infra", "docs", "epic"],
        )
        self.assertEqual(["epic"], findings_by_id(snap)["vocabulary-fossils"]["affected"])

    def test_a_board_with_no_declared_vocabulary_reports_nothing(self):
        snap = clean()
        del snap["fields"]["labels"]
        self.assertNotIn("vocabulary-fossils", findings_by_id(snap))


class VocabularyCollision(unittest.TestCase):
    def test_synonyms_and_namespace_prefixes_collapse_to_one_concept(self):
        snap = snapshot(
            CLEAN_ITEMS,
            label_options=["infra", "docs", "doc", "chore", "type:chore", "feature", "type:feat"],
        )
        found = findings_by_id(snap)["vocabulary-collision"]
        self.assertEqual("warn", found["severity"])
        self.assertEqual(
            [["doc", "docs"], ["feature", "type:feat"], ["chore", "type:chore"]],
            found["groups"],
            "groups sort by the normalized concept, members alphabetically",
        )

    def test_a_collision_between_two_in_use_labels_fires(self):
        items = [item("c1", labels=["up-next"]), item("c2", labels=["status:up-next"])]
        snap = snapshot(CLEAN_ITEMS + items, label_options=[])
        self.assertEqual(
            [["status:up-next", "up-next"]],
            findings_by_id(snap)["vocabulary-collision"]["groups"],
        )

    def test_distinct_concepts_do_not_collide(self):
        snap = snapshot(CLEAN_ITEMS, label_options=["infra", "docs", "priority:high", "spike"])
        self.assertNotIn("vocabulary-collision", findings_by_id(snap))

    def test_normalization_rules(self):
        self.assertEqual("bug", bh.normalize_label("type:fix"))
        self.assertEqual("bug", bh.normalize_label("Bug"))
        self.assertEqual("maintenance", bh.normalize_label("kind:chore"))
        self.assertEqual("docs", bh.normalize_label("area:doc"))
        self.assertEqual("upnext", bh.normalize_label("status:up-next"))
        self.assertEqual("priorityhigh", bh.normalize_label("priority:high"))


class LoadSnapshot(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            return bh.load_snapshot(path)

    def test_a_valid_snapshot_round_trips(self):
        self.assertEqual(6, len(self.load(json.dumps(clean()))["items"]))

    def test_unreadable_json_is_fatal(self):
        with self.assertRaises(bh.SnapshotError) as caught:
            self.load("{not json")
        self.assertIn("not valid JSON", str(caught.exception))

    def test_a_missing_file_is_fatal(self):
        with self.assertRaises(bh.SnapshotError) as caught:
            bh.load_snapshot(os.path.join(tempfile.gettempdir(), "no-such-snapshot-9f3.json"))
        self.assertIn("cannot read", str(caught.exception))

    def test_a_snapshot_without_items_is_fatal(self):
        for payload in ("[]", "{}", '{"items": {}}', '"a string"'):
            with self.subTest(payload=payload), self.assertRaises(bh.SnapshotError):
                self.load(payload)

    def test_stdin_is_read_when_no_path_is_given(self):
        stdin, sys.stdin = sys.stdin, io.StringIO(json.dumps(clean()))
        try:
            self.assertEqual("demo", bh.load_snapshot(None)["board"]["name"])
        finally:
            sys.stdin = stdin


class Cli(unittest.TestCase):
    def run_main(self, snap_text, argv=()):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "snap.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(snap_text)
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = bh.main([path, *argv])
            return code, out.getvalue(), err.getvalue()

    def test_a_clean_board_exits_zero(self):
        code, out, err = self.run_main(json.dumps(clean()))
        self.assertEqual(0, code, out + err)
        self.assertIn("clean", out)

    def test_any_finding_exits_one(self):
        items = [item(f"p{n}", priority="P2") for n in range(7)] + [item("q1", priority="P0")]
        code, out, _ = self.run_main(json.dumps(snapshot(items)))
        self.assertEqual(1, code)
        self.assertIn("priority-skew", out)

    def test_a_malformed_snapshot_exits_two_with_a_message(self):
        code, out, err = self.run_main("{not json")
        self.assertEqual(2, code, "measuring nothing must never look like a clean board")
        self.assertIn("not valid JSON", err)
        self.assertEqual("", out)

    def test_json_mode_emits_the_findings(self):
        items = [item(f"p{n}", priority="P2") for n in range(7)] + [item("q1", priority="P0")]
        code, out, _ = self.run_main(json.dumps(snapshot(items, ["infra"])), ["--json"])
        self.assertEqual(1, code)
        payload = json.loads(out)
        self.assertEqual(8, payload["open_items"])
        self.assertEqual(["priority-skew"], [f["check"] for f in payload["findings"]])

    def test_the_printed_item_list_is_capped(self):
        items = [item(f"p{n:02d}", priority=None, labels=[]) for n in range(14)]
        _, out, _ = self.run_main(json.dumps(snapshot(items)))
        self.assertIn("+4 more", out)
        self.assertNotIn("p13", out, "the 14th key is over the cap")
        _, raw, _ = self.run_main(json.dumps(snapshot(items)), ["--json"])
        affected = json.loads(raw)["findings"][0]["affected"]
        self.assertEqual(14, len(affected), "--json carries every key; only the report caps")

    def test_thresholds_are_flags(self):
        items = [item(f"p{n}", priority="P2") for n in range(3)]
        items += [item(f"q{n}", priority="P1") for n in range(3)]
        code, out, err = self.run_main(json.dumps(snapshot(items, ["infra"])))
        self.assertEqual(0, code, out + err)
        code, out, _ = self.run_main(
            json.dumps(snapshot(items, ["infra"])), ["--skew-threshold", "0.4"]
        )
        self.assertEqual(1, code)
        self.assertIn("priority-skew", out)


if __name__ == "__main__":
    unittest.main()

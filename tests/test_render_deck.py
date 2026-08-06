"""Tests for the comms deck renderer (primitives-core/skills/comms/scripts/render_deck.py).

Hermetic and stdlib-only: nothing here launches Chrome or touches the network. The PDF path
is covered only for its guard behavior; the render/validate path — the part that decides
whether a briefing is correct — is covered directly.
"""

import json
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "primitives-core", "skills", "comms", "scripts"))

import render_deck as rd  # noqa: E402

EXAMPLES = os.path.join(REPO, "primitives-core", "skills", "comms", "examples")


def slide(*blocks, **kw):
    d = {"blocks": list(blocks)}
    d.update(kw)
    return d


class Validate(unittest.TestCase):
    def test_minimal_deck_is_clean(self):
        deck = [slide({"type": "heading", "text": "Hello"})]
        self.assertEqual(rd.validate(deck), [])

    def test_top_level_must_be_a_list(self):
        self.assertIn("array of slides", rd.validate({"blocks": []})[0])

    def test_empty_deck_rejected(self):
        self.assertIn("zero slides", rd.validate([])[0])

    def test_slide_needs_blocks(self):
        self.assertIn("non-empty 'blocks'", rd.validate([{}])[0])

    def test_unknown_slide_key_flagged(self):
        problems = rd.validate([slide({"type": "heading", "text": "x"}, theme="midnight")])
        self.assertTrue(any("unknown slide key" in p for p in problems))

    def test_bad_layout_flagged(self):
        problems = rd.validate([slide({"type": "heading", "text": "x"}, layout="diagonal")])
        self.assertTrue(any("layout" in p for p in problems))

    def test_unsupported_block_type_is_an_error_not_a_silent_drop(self):
        problems = rd.validate([slide({"type": "timeline", "milestones": []})])
        self.assertEqual(len(problems), 1)
        self.assertIn("unsupported block type", problems[0])

    def test_heading_needs_text(self):
        self.assertTrue(any("non-empty 'text'" in p for p in rd.validate([slide({"type": "heading"})])))

    def test_heading_level_bounded(self):
        problems = rd.validate([slide({"type": "heading", "text": "x", "level": 3})])
        self.assertTrue(any("level must be 1 or 2" in p for p in problems))

    def test_bullets_need_items(self):
        problems = rd.validate([slide({"type": "bullets", "items": []})])
        self.assertTrue(any("non-empty 'items'" in p for p in problems))

    def test_stat_trend_bounded(self):
        problems = rd.validate([slide({"type": "stat", "value": "6", "trend": "sideways"})])
        self.assertTrue(any("trend" in p for p in problems))

    def test_callout_variant_bounded(self):
        problems = rd.validate([slide({"type": "callout", "text": "x", "variant": "danger"})])
        self.assertTrue(any("variant" in p for p in problems))

    def test_nested_column_blocks_are_validated(self):
        deck = [slide({"type": "columns", "columns": [[{"type": "bogus"}]]})]
        problems = rd.validate(deck)
        self.assertTrue(any("col 1 block 1" in p and "unsupported" in p for p in problems))

    def test_problems_name_their_slide(self):
        deck = [slide({"type": "heading", "text": "ok"}), slide({"type": "heading"})]
        self.assertTrue(rd.validate(deck)[0].startswith("slide 2"))


class ShippedSamplesStayValid(unittest.TestCase):
    """The samples are the skill's own worked examples — they must never drift out of schema."""

    def test_every_sample_deck_validates(self):
        samples = [
            os.path.join(root, f)
            for root, _, files in os.walk(EXAMPLES)
            for f in files
            if f == "sample.slides.json"
        ]
        self.assertTrue(samples, "no sample decks found — did the examples move?")
        for path in samples:
            with self.subTest(sample=os.path.relpath(path, REPO)):
                with open(path, encoding="utf-8") as fh:
                    self.assertEqual(rd.validate(json.load(fh)), [])


class Inline(unittest.TestCase):
    def test_html_is_escaped(self):
        self.assertEqual(rd._inline("<script>&"), "&lt;script&gt;&amp;")

    def test_bold_and_code(self):
        self.assertIn("<strong>b</strong>", rd._inline("**b**"))
        self.assertIn("<code>c</code>", rd._inline("`c`"))

    def test_tint_span(self):
        self.assertIn('<span class="tint tint-warn">late</span>', rd._inline("{warn:late}"))

    def test_chip_wins_over_tint(self):
        out = rd._inline("{chip.ok:DONE}")
        self.assertIn('class="chip chip-ok"', out)
        self.assertNotIn("tint", out)

    def test_issue_ref_linkified_when_repo_given(self):
        self.assertIn('href="https://github.com/o/r/issues/12"', rd._inline("see #12", repo="o/r"))

    def test_issue_ref_left_alone_without_repo(self):
        self.assertNotIn("<a ", rd._inline("see #12"))

    def test_placeholder_refs_are_not_linkified(self):
        self.assertNotIn("<a ", rd._inline("see #NNN", repo="o/r"))


class RenderHtml(unittest.TestCase):
    def test_document_is_self_contained(self):
        out = rd.render_html([slide({"type": "heading", "text": "Hi"})])
        self.assertIn("<style>", out)
        self.assertNotIn("<script", out)
        self.assertNotIn("http://", out)

    def test_one_section_per_slide(self):
        deck = [slide({"type": "heading", "text": f"S{i}"}) for i in range(4)]
        self.assertEqual(rd.render_html(deck).count('class="slide '), 4)

    def test_invalid_deck_raises(self):
        with self.assertRaises(rd.DeckError):
            rd.render_html([slide({"type": "nope"})])

    def test_kicker_and_footer_render(self):
        out = rd.render_html([slide({"type": "heading", "text": "x"}, kicker="K", footer="F")])
        self.assertIn('class="kicker">K<', out)
        self.assertIn('class="footer">F<', out)

    def test_notes_are_hidden_not_dropped(self):
        out = rd.render_html([slide({"type": "heading", "text": "x"}, notes="private")])
        self.assertIn("private", out)
        self.assertIn(".notes{display:none}", out.replace(" ", "").replace("\n", ""))

    def test_stat_renders_trend_arrow(self):
        out = rd.render_html([slide({"type": "stat", "value": "6", "delta": "+2", "trend": "up"})])
        self.assertIn("▲", out)
        self.assertIn("trend-up", out)

    def test_columns_nest(self):
        deck = [slide({"type": "columns", "columns": [
            [{"type": "heading", "level": 2, "text": "L"}],
            [{"type": "bullets", "items": ["r"]}],
        ]})]
        out = rd.render_html(deck)
        self.assertEqual(out.count('class="col"'), 2)
        self.assertIn("<h2>L</h2>", out)


class PdfGuards(unittest.TestCase):
    def test_missing_chrome_raises_with_guidance(self):
        real = rd.shutil.which
        rd.shutil.which = lambda _n: None
        real_isfile = rd.os.path.isfile
        rd.os.path.isfile = lambda p: False if "Google Chrome" in p else real_isfile(p)
        try:
            with self.assertRaises(rd.DeckError) as ctx:
                rd._find_chrome()
            self.assertIn("--html", str(ctx.exception))
        finally:
            rd.shutil.which = real
            rd.os.path.isfile = real_isfile


if __name__ == "__main__":
    unittest.main()

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
        problems = rd.validate([slide({"type": "sparkline", "data": []})])
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


class RichBlocks(unittest.TestCase):
    """The eight block types added after a census of the real decks in _meta/briefings/."""

    def test_table_validates_and_renders(self):
        b = {"type": "table", "head": ["A", "B"], "rows": [["1", "2"], ["3", "4"]]}
        self.assertEqual(rd.validate([slide(b)]), [])
        out = rd.render_html([slide(b)])
        self.assertEqual(out.count("<th>"), 2)
        self.assertEqual(out.count("<td>"), 4)

    def test_ragged_table_row_pads_rather_than_truncates(self):
        b = {"type": "table", "head": ["A", "B", "C"], "rows": [["1"]]}
        self.assertEqual(rd.validate([slide(b)]), [])
        self.assertEqual(rd.render_html([slide(b)]).count("<td>"), 3)

    def test_overwide_table_row_is_rejected(self):
        b = {"type": "table", "head": ["A"], "rows": [["1", "2"]]}
        problems = rd.validate([slide(b)])
        self.assertTrue(any("cells but head has" in p for p in problems))

    def test_steps_render_as_ordered_list(self):
        b = {"type": "steps", "steps": [{"title": "One", "detail": "d"}, {"title": "Two"}]}
        self.assertEqual(rd.validate([slide(b)]), [])
        out = rd.render_html([slide(b)])
        self.assertIn('<ol class="steps">', out)
        self.assertEqual(out.count("<li>"), 2)

    def test_step_without_title_rejected(self):
        problems = rd.validate([slide({"type": "steps", "steps": [{"detail": "x"}]})])
        self.assertTrue(any("needs a 'title'" in p for p in problems))

    def test_timeline_renders(self):
        b = {"type": "timeline", "milestones": [{"label": "Q1", "title": "Kickoff"}]}
        self.assertEqual(rd.validate([slide(b)]), [])
        self.assertIn('class="timeline"', rd.render_html([slide(b)]))

    def test_matrix_renders_quadrants_and_axes(self):
        b = {
            "type": "matrix",
            "xAxis": ["low", "high"],
            "yAxis": ["small", "big"],
            "quadrants": [{"title": "TL", "items": ["a"]}, {"title": "TR"}],
        }
        self.assertEqual(rd.validate([slide(b)]), [])
        out = rd.render_html([slide(b)])
        self.assertEqual(out.count('class="quad"'), 2)
        self.assertIn("axis-x", out)

    def test_matrix_rejects_more_than_four_quadrants(self):
        b = {"type": "matrix", "quadrants": [{}] * 5}
        self.assertTrue(any("at most 4" in p for p in rd.validate([slide(b)])))

    def test_matrix_axis_must_be_a_pair(self):
        b = {"type": "matrix", "quadrants": [{}], "xAxis": ["only-one"]}
        self.assertTrue(any("[start, end] pair" in p for p in rd.validate([slide(b)])))

    def test_code_block_escapes_its_body(self):
        b = {"type": "code", "lang": "py", "code": "print('<hi>')"}
        self.assertEqual(rd.validate([slide(b)]), [])
        out = rd.render_html([slide(b)])
        self.assertIn("&lt;hi&gt;", out)
        self.assertIn('data-lang="py"', out)

    def test_svg_embeds_verbatim(self):
        b = {"type": "svg", "svg": "<svg><circle r='2'/></svg>"}
        self.assertEqual(rd.validate([slide(b)]), [])
        self.assertIn("<circle r='2'/>", rd.render_html([slide(b)]))

    def test_remote_image_passes_through(self):
        b = {"type": "image", "src": "https://example.com/a.png", "alt": "x"}
        self.assertEqual(rd.validate([slide(b)]), [])
        self.assertIn("https://example.com/a.png", rd.render_html([slide(b)]))

    def test_missing_local_image_is_an_error(self):
        b = {"type": "image", "src": "nope.png"}
        with self.assertRaises(rd.DeckError):
            rd.render_html([slide(b)], base_dir="/definitely/not/here")

    def test_local_image_inlines_as_data_uri(self):
        import base64
        import tempfile

        png = base64.b64decode(
            b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        )
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "dot.png"), "wb") as fh:
                fh.write(png)
            out = rd.render_html([slide({"type": "image", "src": "dot.png"})], base_dir=tmp)
        self.assertIn("data:image/png;base64,", out)

    def test_each_chart_kind_renders_svg(self):
        for kind in ("bar", "line", "donut"):
            with self.subTest(kind=kind):
                b = {"type": "chart", "kind": kind, "data": [3, 1, 2], "labels": ["a", "b", "c"]}
                self.assertEqual(rd.validate([slide(b)]), [])
                out = rd.render_html([slide(b)])
                self.assertIn("<svg", out)
                self.assertIn('class="chart"', out)

    def test_chart_rejects_unknown_kind_and_non_numeric_data(self):
        self.assertTrue(any("chart kind" in p for p in rd.validate(
            [slide({"type": "chart", "kind": "pie", "data": [1]})])))
        self.assertTrue(any("must be all numbers" in p for p in rd.validate(
            [slide({"type": "chart", "kind": "bar", "data": ["1"]})])))

    def test_chart_data_of_all_zeros_does_not_divide_by_zero(self):
        b = {"type": "chart", "kind": "donut", "data": [0, 0]}
        self.assertIn("<svg", rd.render_html([slide(b)]))

    def test_quote_renders_with_attribution(self):
        b = {"type": "quote", "text": "Ship it", "attribution": "someone"}
        self.assertEqual(rd.validate([slide(b)]), [])
        out = rd.render_html([slide(b)])
        self.assertIn("<blockquote>", out)
        self.assertIn("someone", out)

    def test_renderer_covers_the_whole_upstream_schema(self):
        """Guards against a schema type being dropped: every documented block must render."""
        upstream = {
            "heading", "lead", "subtitle", "bullets", "code", "table", "image", "svg",
            "chart", "callout", "stat", "quote", "divider", "matrix", "timeline", "steps",
            "columns",
        }
        self.assertEqual(upstream - rd.SUPPORTED_BLOCKS, set())


class KickerPlacement(unittest.TestCase):
    def test_kicker_sits_inside_the_body_so_center_layout_groups_it(self):
        out = rd.render_html([slide({"type": "heading", "text": "T"}, kicker="K", layout="center")])
        body_start = out.index('<div class="body">')
        self.assertLess(body_start, out.index('class="kicker"'))


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

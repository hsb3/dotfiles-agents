"""Tests for the comm-kit deck engine (primitives-core/skills/comm-kit/scripts/deliver.py).

Hermetic and stdlib-only: nothing here launches Chrome or touches the network. The PDF path
is covered only for its guard behavior; the loader/validate/lint/render path — the part that
decides whether a deliverable is correct — is covered directly. Fixtures are built inline or
in ``tempfile`` tempdirs, never written under ``primitives-core/`` (the roster guard flags
orphans there).
"""

import builtins
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "primitives-core", "skills", "comm-kit", "scripts"))

import deliver as dl  # noqa: E402

EXAMPLES = os.path.join(REPO, "primitives-core", "skills", "comm-kit", "examples")
MORNING_BRIEFING_SPEC = os.path.join(EXAMPLES, "morning-briefing.spec.json")

try:
    import yaml as _probe_yaml  # noqa: F401

    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


def minimal_slide(text: str = "T") -> dict:
    return {"blocks": [{"type": "heading", "text": text}]}


def morning_slide(kicker: str = "K", extra_blocks: list | None = None) -> dict:
    blocks = [{"type": "heading", "text": "T"}]
    if extra_blocks:
        blocks += extra_blocks
    return {"kicker": kicker, "blocks": blocks}


def full_morning_sections(**overrides) -> dict:
    """Every REQUIRED section of the morning-briefing type, one clean slide each."""
    sections = {
        "title": [morning_slide()],
        "recommended-today": [morning_slide()],
        "horizon": [morning_slide()],
        "at-a-glance": [morning_slide()],
        "line-for-today": [morning_slide()],
    }
    sections.update(overrides)
    return sections


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = dl.main(argv)
    return code, out.getvalue(), err.getvalue()


class SpecLoader(unittest.TestCase):
    def test_json_dict_spec_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "spec.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"slides": [minimal_slide()]}, fh)
            spec = dl.load_spec(path)
        self.assertEqual(spec, {"slides": [minimal_slide()]})

    def test_bare_top_level_array_is_the_legacy_slides_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([minimal_slide("Legacy")], fh)
            spec = dl.load_spec(path)
        self.assertEqual(spec, {"slides": [minimal_slide("Legacy")]})

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_yaml_spec_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "spec.yaml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("slides:\n  - blocks:\n      - type: heading\n        text: Hi\n")
            spec = dl.load_spec(path)
        self.assertEqual(spec["slides"][0]["blocks"][0]["text"], "Hi")

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_missing_pyyaml_exits_with_a_clear_message(self):
        """Cheaply simulate PyYAML being absent by making `import yaml` fail."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "spec.yaml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("slides: []\n")

            real_import = builtins.__import__

            def fake_import(name, *args, **kwargs):
                if name == "yaml":
                    raise ImportError("simulated: PyYAML not installed")
                return real_import(name, *args, **kwargs)

            with mock.patch("builtins.__import__", side_effect=fake_import):
                with self.assertRaises(SystemExit) as ctx:
                    dl.load_spec(path)
            self.assertIn("PyYAML", str(ctx.exception))

    def test_unknown_top_level_key_is_a_problem_not_an_exception(self):
        spec = {"slides": [minimal_slide()], "bogus": "x"}
        problems = dl.validate_spec(spec)  # must not raise
        self.assertTrue(any("bogus" in p for p in problems))


class SectionValidation(unittest.TestCase):
    TYPE_NAME = "morning-briefing"

    def test_clean_sectioned_spec_without_optional_section_has_no_problems(self):
        spec = {"type": self.TYPE_NAME, "sections": full_morning_sections()}
        self.assertEqual(dl.validate_spec(spec), [])

    def test_unknown_section_id_names_the_types_sections(self):
        sections = full_morning_sections(**{"not-a-real-section": [morning_slide()]})
        spec = {"type": self.TYPE_NAME, "sections": sections}
        problems = dl.validate_spec(spec)
        hits = [p for p in problems if "unknown section" in p]
        self.assertTrue(hits)
        self.assertIn("title", hits[0])
        self.assertIn("recommended-today", hits[0])

    def test_missing_required_section_flagged(self):
        sections = full_morning_sections()
        del sections["horizon"]
        spec = {"type": self.TYPE_NAME, "sections": sections}
        problems = dl.validate_spec(spec)
        self.assertTrue(any("missing required section 'horizon'" in p for p in problems))

    def test_optional_section_may_be_absent(self):
        # full_morning_sections() already omits 'shipped' (required: false in the type).
        spec = {"type": self.TYPE_NAME, "sections": full_morning_sections()}
        problems = dl.validate_spec(spec)
        self.assertFalse(any("shipped" in p for p in problems))

    def test_slide_count_outside_pages_budget_flagged(self):
        sections = full_morning_sections(**{
            "at-a-glance": [morning_slide(), morning_slide()],  # budget is [1, 1]
        })
        spec = {"type": self.TYPE_NAME, "sections": sections}
        problems = dl.validate_spec(spec)
        self.assertTrue(any("budget is 1-1" in p for p in problems))

    def test_sections_and_slides_together_is_an_error(self):
        spec = {
            "type": self.TYPE_NAME,
            "sections": full_morning_sections(),
            "slides": [morning_slide()],
        }
        problems = dl.validate_spec(spec)
        self.assertTrue(any("both 'sections' and 'slides'" in p for p in problems))

    def test_sections_without_type_is_an_error(self):
        spec = {"sections": {"title": [morning_slide()]}}
        problems = dl.validate_spec(spec)
        self.assertTrue(any("no 'type'" in p for p in problems))

    def test_all_problems_arrive_in_one_analyze_spec_call(self):
        sections = full_morning_sections(**{
            "at-a-glance": [morning_slide(), morning_slide()],
            "unknown-junk": [morning_slide()],
        })
        del sections["horizon"]
        spec = {"type": self.TYPE_NAME, "sections": sections, "bogus": "x"}

        ctx, problems, findings = dl.analyze_spec(spec)

        self.assertTrue(any("unknown top-level key" in p for p in problems))
        self.assertTrue(any("unknown section" in p for p in problems))
        self.assertTrue(any("missing required section" in p for p in problems))
        self.assertTrue(any("budget is 1-1" in p for p in problems))
        self.assertGreaterEqual(len(problems), 4)


class VoiceLint(unittest.TestCase):
    def test_title_budget(self):
        voice = {"budgets": {"title_chars": 10}}
        slides = [{"blocks": [{"type": "heading", "text": "This title is way too long"}]}]
        findings = dl.voice_lint(slides, voice)
        self.assertTrue(any(rule == "voice.title-budget" for rule, _ in findings))

    def test_bullet_word_budget(self):
        voice = {"budgets": {"bullet_words": 3}}
        slides = [{"blocks": [{"type": "bullets", "items": ["one two three four five"]}]}]
        findings = dl.voice_lint(slides, voice)
        self.assertTrue(any(rule == "voice.bullet-budget" for rule, _ in findings))

    def test_bullet_count_counts_bullets_nested_in_columns(self):
        voice = {"budgets": {"bullets_per_slide": 2}}
        slides = [{"blocks": [{
            "type": "columns",
            "columns": [
                [{"type": "bullets", "items": ["a", "b"]}],
                [{"type": "bullets", "items": ["c"]}],
            ],
        }]}]
        findings = dl.voice_lint(slides, voice)
        self.assertTrue(
            any(rule == "voice.bullet-count" and "3 bullets" in msg for rule, msg in findings)
        )

    def test_register_fragments_flags_trailing_period(self):
        voice = {"register": "fragments"}
        slides = [{"blocks": [{"type": "bullets", "items": ["Ship it."]}]}]
        findings = dl.voice_lint(slides, voice)
        self.assertTrue(any(rule == "voice.register" for rule, _ in findings))

    def test_register_fragments_exempts_ellipsis(self):
        voice = {"register": "fragments"}
        slides = [{"blocks": [{"type": "bullets", "items": ["still thinking..."]}]}]
        findings = dl.voice_lint(slides, voice)
        self.assertFalse(any(rule == "voice.register" for rule, _ in findings))

    def test_bare_id_flags_a_leading_bare_ref(self):
        voice = {"id_policy": "label-first"}
        slides = [{"blocks": [{"type": "bullets", "items": ["#12 fix it"]}]}]
        findings = dl.voice_lint(slides, voice)
        self.assertTrue(any(rule == "voice.bare-id" for rule, _ in findings))

    def test_bare_id_clean_when_label_comes_first(self):
        voice = {"id_policy": "label-first"}
        slides = [{"blocks": [{"type": "bullets", "items": ["fix the loader (#12)"]}]}]
        findings = dl.voice_lint(slides, voice)
        self.assertFalse(any(rule == "voice.bare-id" for rule, _ in findings))

    def test_knob_absent_from_voice_never_fires(self):
        voice: dict = {}  # no budgets, no register, no id_policy declared
        slides = [{"blocks": [
            {"type": "heading", "text": "x" * 200},
            {"type": "bullets", "items": ["#12 " + "word " * 50 + "."]},
        ]}]
        self.assertEqual(dl.voice_lint(slides, voice), [])

    def test_waive_suppresses_a_finding_via_analyze_spec(self):
        sections = full_morning_sections(**{
            "recommended-today": [morning_slide(extra_blocks=[
                {"type": "bullets", "items": ["#99 fix the thing"]},
            ])],
        })
        spec = {
            "type": "morning-briefing",  # default_voice self-blunt: id_policy label-first
            "waive": ["voice.bare-id"],
            "sections": sections,
        }
        ctx, problems, findings = dl.analyze_spec(spec)

        self.assertEqual(problems, [])
        self.assertEqual(ctx["waive"], ["voice.bare-id"])
        self.assertTrue(any(rule == "voice.bare-id" for rule, _ in findings))
        unwaived = [(rule, msg) for rule, msg in findings if rule not in ctx["waive"]]
        self.assertFalse(any(rule == "voice.bare-id" for rule, _ in unwaived))


class ThemeCompleteness(unittest.TestCase):
    def test_required_tokens_is_28(self):
        self.assertEqual(len(dl.REQUIRED_TOKENS), 28)

    def test_every_shipped_theme_has_all_required_tokens(self):
        names = dl._names(dl.THEMES_DIR)
        self.assertEqual(len(names), 7, "theme count drifted — update this test if intended")
        for name in names:
            with self.subTest(theme=name):
                theme = dl.load_theme(name)  # raises DeckError if a token is missing/malformed
                self.assertEqual(dl.validate_theme(name, theme), [])

    def test_validate_theme_catches_a_missing_token(self):
        tokens = {t: "AABBCC" for t in dl.REQUIRED_TOKENS if t != "canvas"}
        problems = dl.validate_theme("broken", {"tokens": tokens})
        self.assertTrue(any("'canvas'" in p for p in problems))

    def test_validate_theme_catches_lowercase_hex(self):
        tokens = {t: "AABBCC" for t in dl.REQUIRED_TOKENS}
        tokens["textPrimary"] = "aabbcc"
        problems = dl.validate_theme("broken", {"tokens": tokens})
        self.assertTrue(any("'textPrimary'" in p for p in problems))


class RendererSmoke(unittest.TestCase):
    SECTION_KICKERS = (
        "ACME-PLATFORM - MORNING BRIEFING",
        "RECOMMENDED TODAY",
        "ON THE HORIZON",
        "SINCE THE LAST BRIEFING",
        "WHAT SHIPPED - 1",
        "THE LINE FOR TODAY",
    )

    def test_shipped_example_renders_all_section_slides_with_boardroom_accent(self):
        spec = dl.load_spec(MORNING_BRIEFING_SPEC)
        ctx, problems, findings = dl.analyze_spec(spec)
        self.assertEqual(problems, [])

        slides = dl.resolve_slides(spec, ctx["typedef"])
        doc = dl.render_html(slides, repo=ctx["repo"], title=ctx["title"], theme=ctx["theme"])

        for kicker in self.SECTION_KICKERS:
            self.assertIn(kicker, doc)
        self.assertIn("#1A4E8A", doc)  # boardroom accentPrimary

    def test_theme_override_to_midnight_injects_its_canvas_token(self):
        spec = dl.load_spec(MORNING_BRIEFING_SPEC)
        ctx, problems, findings = dl.analyze_spec(spec, overrides={"theme": "midnight"})
        self.assertEqual(problems, [])

        slides = dl.resolve_slides(spec, ctx["typedef"])
        doc = dl.render_html(slides, theme=ctx["theme"])
        self.assertIn("#0A0E27", doc)  # midnight canvas

    def test_legacy_bare_array_deck_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([minimal_slide("Legacy deck")], fh)
            spec = dl.load_spec(path)
        doc = dl.render_html(spec["slides"])
        self.assertIn("Legacy deck", doc)

    def test_validation_failure_raises_deckerror_from_render_html(self):
        with self.assertRaises(dl.DeckError):
            dl.render_html([{"blocks": [{"type": "bogus"}]}])


class Cli(unittest.TestCase):
    def test_check_on_shipped_example_returns_0(self):
        code, _out, _err = run_cli(["check", MORNING_BRIEFING_SPEC])
        self.assertEqual(code, 0)

    def test_check_on_bad_spec_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"type": "morning-briefing"}, fh)  # neither sections nor slides
            code, _out, _err = run_cli(["check", path])
        self.assertEqual(code, 1)

    def test_types_returns_0(self):
        code, _out, _err = run_cli(["types"])
        self.assertEqual(code, 0)

    def test_new_then_check_round_trips_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "scaffold.json")
            new_code, _out, _err = run_cli(["new", "morning-briefing", "-o", out_path])
            self.assertEqual(new_code, 0)
            self.assertTrue(os.path.isfile(out_path))
            check_code, _out, err = run_cli(["check", out_path])
        self.assertEqual(check_code, 0, err)


class PdfGuards(unittest.TestCase):
    def test_missing_chrome_raises_with_guidance(self):
        real_which = dl.shutil.which
        real_isfile = dl.os.path.isfile
        dl.shutil.which = lambda _name: None
        dl.os.path.isfile = lambda p: False if "Google Chrome" in p else real_isfile(p)
        try:
            with self.assertRaises(dl.DeckError) as ctx:
                dl._find_chrome()
            self.assertIn("--html", str(ctx.exception))
        finally:
            dl.shutil.which = real_which
            dl.os.path.isfile = real_isfile


if __name__ == "__main__":
    unittest.main()

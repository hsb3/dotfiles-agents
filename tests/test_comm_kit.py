"""Tests for the comms deck engine (primitives-core/skills/comms/scripts/deliver.py).

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
sys.path.insert(0, os.path.join(REPO, "primitives-core", "skills", "comms", "scripts"))

import deliver as dl  # noqa: E402

EXAMPLES = os.path.join(REPO, "primitives-core", "skills", "comms", "examples")
MORNING_BRIEFING_SPEC = os.path.join(EXAMPLES, "morning-briefing", "sample.spec.json")

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


def capture(fn, *args, **kwargs):
    """Call *fn*, returning ``(value, stdout, stderr)`` — for the functions that warn."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        value = fn(*args, **kwargs)
    return value, out.getvalue(), err.getvalue()


def write_local(tmp: str, text: str) -> str:
    """Write a project-local preferences file at ``<tmp>/.claude/comms.local.md``."""
    d = os.path.join(tmp, ".claude")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "comms.local.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def write_spec(directory: str, spec, name: str = "spec.json") -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh)
    return path


def helper_script(tmp: str, body: str, name: str = "fake_provider.py") -> str:
    """A tiny python file standing in for an audio provider — never a real TTS engine."""
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


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


class LocalPreferences(unittest.TestCase):
    """`.claude/comms.local.md` — house defaults, ranked below the spec."""

    def spec(self, **top) -> dict:
        spec = {"type": "morning-briefing", "sections": full_morning_sections()}
        spec.update(top)
        return spec

    def test_missing_file_is_silent_and_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            value, out, err = capture(dl.load_local_config, tmp)
        self.assertEqual(value, {})
        self.assertEqual(err, "")
        self.assertEqual(out, "")

    def test_no_spec_context_means_no_local_file(self):
        self.assertEqual(dl.load_local_config(None), {})

    def test_found_by_walking_up_from_the_spec_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\ntheme: midnight\n---\n")
            deep = os.path.join(tmp, "a", "b", "c")
            os.makedirs(deep)
            value, _out, err = capture(dl.load_local_config, deep)
        self.assertEqual(value, {"theme": "midnight"})
        self.assertEqual(err, "")

    def test_quotes_and_trailing_comments_are_stripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, '---\ntheme: "midnight"  # house dark palette\n---\n')
            value, _out, err = capture(dl.load_local_config, tmp)
        self.assertEqual(value, {"theme": "midnight"})
        self.assertEqual(err, "")

    def test_malformed_frontmatter_warns_once_and_degrades(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "theme: midnight\n")  # no fences at all
            value, _out, err = capture(dl.load_local_config, tmp)
        self.assertEqual(value, {})
        self.assertEqual(len(err.strip().splitlines()), 1, err)
        self.assertTrue(err.startswith("✗"), err)

    def test_unclosed_frontmatter_warns_and_degrades(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\ntheme: midnight\n")
            value, _out, err = capture(dl.load_local_config, tmp)
        self.assertEqual(value, {})
        self.assertEqual(len(err.strip().splitlines()), 1, err)

    def test_unknown_key_warns_but_recognized_keys_still_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\ntheme: midnight\npalette: neon\n---\n")
            value, _out, err = capture(dl.load_local_config, tmp)
        self.assertEqual(value, {"theme": "midnight"})
        self.assertIn("palette", err)
        self.assertTrue(err.startswith("✗"), err)

    def test_nested_and_list_structures_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\ntheme: midnight\nnested:\n  a: b\n- item\n---\n")
            value, _out, err = capture(dl.load_local_config, tmp)
        self.assertEqual(value, {"theme": "midnight"})
        self.assertEqual(err, "")

    # -- precedence: CLI flag > spec field > project local > type default ----

    def test_local_theme_beats_the_type_default(self):
        ctx, problems = dl.resolve_context(self.spec(), local={"theme": "midnight"})
        self.assertEqual(problems, [])
        self.assertEqual(ctx["theme_name"], "midnight")

    def test_spec_theme_beats_the_local_file(self):
        ctx, problems = dl.resolve_context(
            self.spec(theme="carbon-white"), local={"theme": "midnight"}
        )
        self.assertEqual(problems, [])
        self.assertEqual(ctx["theme_name"], "carbon-white")

    def test_cli_override_beats_both_spec_and_local(self):
        ctx, problems = dl.resolve_context(
            self.spec(theme="carbon-white"),
            overrides={"theme": "ivory"},
            local={"theme": "midnight"},
        )
        self.assertEqual(problems, [])
        self.assertEqual(ctx["theme_name"], "ivory")

    def test_local_voice_and_repo_rank_below_the_spec(self):
        local = {"voice": "self-blunt", "repo": "house/default"}
        ctx, _p = dl.resolve_context(self.spec(repo="spec/repo"), local=local)
        self.assertEqual(ctx["repo"], "spec/repo")
        ctx, _p = dl.resolve_context(self.spec(), local=local)
        self.assertEqual(ctx["repo"], "house/default")
        self.assertEqual(ctx["voice_name"], "self-blunt")

    def test_absent_local_leaves_resolution_exactly_as_before(self):
        spec = self.spec()
        self.assertEqual(dl.resolve_context(spec), dl.resolve_context(spec, local={}))

    def test_unknown_local_value_fails_in_the_normal_resolution_path(self):
        _ctx, problems = dl.resolve_context(self.spec(), local={"theme": "nosuch"})
        self.assertTrue(any("available" in p and "nosuch" in p for p in problems), problems)

    # -- precedence, end to end through the CLI ------------------------------

    def _build(self, tmp: str, spec: dict, *flags: str) -> str:
        spec_path = write_spec(tmp, spec)
        out = os.path.join(tmp, "deck.html")
        code, _o, err = run_cli(["build", spec_path, "--html", out, *flags])
        self.assertEqual(code, 0, err)
        with open(out, encoding="utf-8") as fh:
            return fh.read()

    def test_cli_build_applies_the_full_precedence_ladder(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\ntheme: midnight\n---\n")
            self.assertIn("#0A0E27", self._build(tmp, self.spec()))          # local: midnight canvas
            self.assertIn("#1A4E8A", self._build(tmp, self.spec(theme="boardroom")))  # spec accent
            doc = self._build(tmp, self.spec(theme="boardroom"), "--theme", "carbon-white")
            self.assertIn("#0F62FE", doc)                                    # CLI flag: carbon accent

    def test_cli_build_proceeds_after_an_unknown_local_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\ntheme: midnight\nbogus: x\n---\n")
            spec_path = write_spec(tmp, self.spec())
            out = os.path.join(tmp, "deck.html")
            code, _o, err = run_cli(["build", spec_path, "--html", out])
            self.assertEqual(code, 0, err)
            self.assertTrue(os.path.isfile(out))
        self.assertIn("bogus", err)


class BriefingsDir(unittest.TestCase):
    """`<briefings-dir>` resolution: CLI flag > spec field > project local > type default."""

    def test_recognized_as_a_local_key_with_no_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\nbriefings_dir: comms-out\n---\n")
            value, _out, err = capture(dl.load_local_config, tmp)
        self.assertEqual(value, {"briefings_dir": "comms-out"})
        self.assertEqual(err, "")

    def test_default_with_no_meta_tree_is_briefings_at_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = dl.resolve_briefings_dir(tmp)
        self.assertEqual(resolved, os.path.join(tmp, "briefings"))

    def test_meta_tree_present_routes_under_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "_meta"))
            resolved = dl.resolve_briefings_dir(tmp)
        self.assertEqual(resolved, os.path.join(tmp, "_meta", "briefings"))

    def test_local_override_beats_the_auto_detect_with_no_meta_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\nbriefings_dir: comms-out\n---\n")
            resolved = dl.resolve_briefings_dir(tmp)
        self.assertEqual(resolved, os.path.join(tmp, "comms-out"))
        self.assertNotEqual(resolved, os.path.join(tmp, "briefings"))

    def test_spec_field_beats_project_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\nbriefings_dir: comms-out\n---\n")
            resolved = dl.resolve_briefings_dir(tmp, spec={"briefings_dir": "spec-out"})
        self.assertEqual(resolved, os.path.join(tmp, "spec-out"))

    def test_cli_flag_beats_spec_and_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\nbriefings_dir: comms-out\n---\n")
            resolved = dl.resolve_briefings_dir(
                tmp, override="/explicit/out", spec={"briefings_dir": "spec-out"}
            )
        self.assertEqual(resolved, "/explicit/out")

    def test_cli_subcommand_prints_the_resolved_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\nbriefings_dir: comms-out\n---\n")
            code, out, err = run_cli(["briefings-dir", tmp])
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), os.path.join(tmp, "comms-out"))


class NarrationScript(unittest.TestCase):
    SLIDES = [
        {
            "kicker": "THE LINE FOR TODAY",
            "notes": "Read this one slowly.",
            "blocks": [
                {"type": "heading", "text": "Ship the **loader**"},
                {"type": "subtitle", "text": "2026-06-13 - decision first"},
                {"type": "lead", "text": "The `loader` is the gate"},
                {"type": "bullets", "items": [
                    "{accent:BUILD} the loader",
                    "{chip.ok:DONE} scoring graduated",
                ]},
            ],
        },
        {"kicker": "SECOND", "blocks": [{"type": "callout", "text": "One sentence ask"}]},
    ]

    def test_content_arrives_in_deck_order(self):
        text = dl.narration_script(self.SLIDES)
        order = [
            "THE LINE FOR TODAY", "Ship the loader", "decision first", "the gate",
            "BUILD the loader", "scoring graduated", "Read this one slowly.",
            "SECOND", "One sentence ask",
        ]
        positions = [text.find(needle) for needle in order]
        self.assertNotIn(-1, positions, f"missing from script:\n{text}")
        self.assertEqual(positions, sorted(positions), text)

    def test_inline_markup_is_stripped(self):
        text = dl.narration_script(self.SLIDES)
        for marker in ("**", "`", "{accent:", "{chip.ok:", "}"):
            self.assertNotIn(marker, text, f"{marker!r} survived into the script")

    def test_stats_are_spoken_label_then_value(self):
        """A stat-only slide must not narrate to a bare kicker — the numbers ARE the slide."""
        slides = [{"kicker": "AT A GLANCE", "blocks": [
            {"type": "stat", "value": "11", "label": "PRs merged", "delta": "up 4",
             "trend": "up", "sub": "since the last one"},
        ]}]
        text = dl.narration_script(slides)
        self.assertIn("PRs merged: 11.", text)
        self.assertIn("up 4", text)
        self.assertIn("since the last one", text)

    def test_bullets_nested_in_columns_are_reached(self):
        slides = [{"blocks": [{"type": "columns", "columns": [
            [{"type": "bullets", "items": ["nested point"]}],
        ]}]}]
        self.assertIn("nested point", dl.narration_script(slides))

    def test_guidance_becomes_a_commented_header(self):
        text = dl.narration_script(self.SLIDES, guidance="spell out acronyms")
        head = text.splitlines()[:2]
        self.assertTrue(all(line.startswith("#") for line in head), head)
        self.assertIn("spell out acronyms", "\n".join(head))

    def test_header_says_it_is_a_draft(self):
        self.assertIn("DRAFT", dl.narration_script(self.SLIDES).splitlines()[0])

    def test_cli_emits_a_script_for_the_shipped_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "script.txt")
            code, stdout, err = run_cli(["narrate", MORNING_BRIEFING_SPEC, "--script", out])
            self.assertEqual(code, 0, err)
            with open(out, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("✓", stdout)
        self.assertIn("spell out acronyms", text)  # morning-briefing type's audio guidance
        self.assertIn("RECOMMENDED TODAY", text)
        self.assertIn("THE LINE FOR TODAY", text)

    def test_cli_rejects_both_modes_at_once(self):
        code, _o, err = run_cli(["narrate", MORNING_BRIEFING_SPEC, "--script", "a", "--audio", "b"])
        self.assertEqual(code, 1)
        self.assertIn("--script", err)


class AudioProviderSeam(unittest.TestCase):
    """Never invokes a real engine: the seam is exercised with a command template."""

    COPY = (
        "import sys\n"
        "open(sys.argv[2], 'w').write('MARKER ' + open(sys.argv[1]).read())\n"
    )
    FAIL = "import sys\nsys.stderr.write('provider blew up\\n')\nsys.exit(3)\n"

    def setup_script(self, tmp: str) -> str:
        path = os.path.join(tmp, "script.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# DRAFT header, not spoken\nHello there.\n")
        return path

    def template(self, helper: str) -> str:
        return f"{sys.executable} {helper} {{script}} {{out}}"

    def test_command_template_runs_and_writes_the_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = self.setup_script(tmp)
            helper = helper_script(tmp, self.COPY)
            out = os.path.join(tmp, "audio.m4a")
            code, stdout, err = run_cli(
                ["narrate", script, "--audio", out, "--provider", self.template(helper)]
            )
            self.assertEqual(code, 0, err)
            self.assertTrue(os.path.isfile(out))
            with open(out, encoding="utf-8") as fh:
                body = fh.read()
        self.assertIn("MARKER", body)
        self.assertIn("Hello there.", body)
        self.assertIn("✓", stdout)

    def test_comment_lines_never_reach_the_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = self.setup_script(tmp)
            helper = helper_script(tmp, self.COPY)
            out = os.path.join(tmp, "audio.m4a")
            run_cli(["narrate", script, "--audio", out, "--provider", self.template(helper)])
            with open(out, encoding="utf-8") as fh:
                body = fh.read()
        self.assertNotIn("DRAFT header", body)

    def test_provider_comes_from_the_local_file_when_no_flag_is_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            helper = helper_script(tmp, self.COPY)
            write_local(tmp, f"---\naudio: {self.template(helper)}\n---\n")
            script = self.setup_script(tmp)
            out = os.path.join(tmp, "audio.m4a")
            code, _o, err = run_cli(["narrate", script, "--audio", out])
            self.assertEqual(code, 0, err)
            self.assertTrue(os.path.isfile(out))

    def test_flag_beats_the_local_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\naudio: none\n---\n")
            script = self.setup_script(tmp)
            helper = helper_script(tmp, self.COPY)
            out = os.path.join(tmp, "audio.m4a")
            code, _o, err = run_cli(
                ["narrate", script, "--audio", out, "--provider", self.template(helper)]
            )
            self.assertEqual(code, 0, err)
            self.assertTrue(os.path.isfile(out))

    def test_none_provider_succeeds_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_local(tmp, "---\naudio: none\n---\n")
            script = self.setup_script(tmp)
            out = os.path.join(tmp, "audio.m4a")
            code, stdout, err = run_cli(["narrate", script, "--audio", out])
        self.assertEqual(code, 0, err)
        self.assertIn("✓", stdout)
        self.assertFalse(os.path.exists(out))

    def test_failing_provider_names_the_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = self.setup_script(tmp)
            helper = helper_script(tmp, self.FAIL, name="broken_provider.py")
            out = os.path.join(tmp, "audio.m4a")
            code, _o, err = run_cli(
                ["narrate", script, "--audio", out, "--provider", self.template(helper)]
            )
        self.assertEqual(code, 1)
        self.assertIn("broken_provider.py", err)
        self.assertIn("3", err)

    def test_missing_say_errors_with_the_fallback_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = self.setup_script(tmp)
            out = os.path.join(tmp, "audio.m4a")
            with mock.patch.object(dl.shutil, "which", return_value=None):
                code, _o, err = run_cli(["narrate", script, "--audio", out])
        self.assertEqual(code, 1)
        self.assertIn("none", err)
        self.assertIn("comms.local.md", err)

    def test_missing_script_file_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "audio.m4a")
            code, _o, err = run_cli(
                ["narrate", os.path.join(tmp, "nope.txt"), "--audio", out, "--provider", "none"]
            )
        # `none` short-circuits before any read, so exercise a real provider instead.
        self.assertEqual(code, 0, err)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "audio.m4a")
            code, _o, err = run_cli(
                ["narrate", os.path.join(tmp, "nope.txt"), "--audio", out,
                 "--provider", "true {script} {out}"]
            )
        self.assertEqual(code, 1)
        self.assertIn("nope.txt", err)


if __name__ == "__main__":
    unittest.main()

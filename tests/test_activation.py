"""Tests for primitives-core/skills/activation/scripts/activation.py.

Runs the checker in-process (main() with an explicit argv and output stream) against
activation files built into tempdirs. Stdlib-only; CLAUDE_PROJECT_DIR and
ATELIER_ACTIVATION_FILE are scrubbed per test so a host session's environment cannot
change a result.

`AgreementTests` calls the hook loaders directly and asserts the checker's report matches
them. That catches a checker that *disagrees* with the hooks on these fixtures — it cannot
catch a private parser that happens to agree, so it is a drift alarm, not a proof of
construction. The no-second-parser property is held by the code and its comments.
"""

import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO_ROOT, "primitives-core", "skills", "activation")
SCRIPT_PATH = os.path.join(SKILL_DIR, "scripts", "activation.py")
EXAMPLE_PATH = os.path.join(SKILL_DIR, "examples", "atelier.local.md")
HOOKS_DIR = os.path.join(REPO_ROOT, "primitives-core", "hooks")
BUNDLE_README = os.path.join(REPO_ROOT, "plugins", "atelier", "README.md")
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")

SCRUBBED_ENV = ("CLAUDE_PROJECT_DIR", "ATELIER_ACTIVATION_FILE", "ATELIER_HARNESS", "CODEX_THREAD_ID")

COMMENT = "# "


def _uncomment_scalar_handoff(text):
    """The shipped example with its commented `handoff: <path>` line live.

    Deliberately surgical: the example carries TWO commented `handoff:`
    blocks (the scalar form and the external mapping form), and a blanket
    `text.replace("# handoff:", "handoff:")` uncomments both. Two top-level
    `handoff:` keys means last-wins picks the childless header, and the row
    reads inert -- a false failure that says nothing about the value under
    test. Only the line with a value after the colon is uncommented here.
    """
    out = []
    for line in text.splitlines():
        body = line[len(COMMENT):]
        if line.startswith(COMMENT + "handoff:") and body[len("handoff:"):].strip():
            line = body
        out.append(line)
    return "\n".join(out) + "\n"


def _uncomment_mapping_handoff(text):
    """The shipped example with its commented `handoff:` MAPPING block live —
    the bare `# handoff:` header plus the indented sub-keys under it."""
    lines = text.splitlines()
    out = []
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if line.strip() != (COMMENT + "handoff:").strip():
            out.append(line)
            continue
        out.append(line[len(COMMENT):])
        while index < len(lines) and lines[index].startswith(COMMENT + "  "):
            out.append(lines[index][len(COMMENT):])
            index += 1
    return "\n".join(out) + "\n"

# The documented invocation: sibling skills all run through $CLAUDE_PLUGIN_ROOT, because
# Bash runs from the project dir, not the skill dir.
INVOCATION = '"${CLAUDE_PLUGIN_ROOT}/skills/activation/scripts/activation.py"'


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Bytecode caching off for this import only: it would otherwise drop a __pycache__
    # directory inside the shipped skill and hook trees on every test run.
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


activation = _load(SCRIPT_PATH, "activation_cli_under_test")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from worktree_fixture import make_worktree, require_git  # noqa: E402


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = os.path.join(self.tmp.name, "project")
        os.makedirs(os.path.join(self.project, ".claude"))

        saved = {name: os.environ.pop(name, None) for name in SCRUBBED_ENV}

        def restore():
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.addCleanup(restore)

    def write(self, text, project=None):
        path = os.path.join(project or self.project, ".claude", "atelier.local.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def check(self, project=None):
        buf = io.StringIO()
        code = activation.main(
            ["check", "--project-dir", project or self.project], out=buf)
        return code, buf.getvalue()

    def row(self, output, key):
        """The reported line for `key`, so assertions do not depend on column widths."""
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.split(" ")[0] == key:
                return stripped
        self.fail("no row for {0!r} in:\n{1}".format(key, output))


class CheckTests(_Base):
    def test_absent_file_is_not_configured(self):
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("not configured", output)

    def test_shipped_example_checks_clean(self):
        shutil.copyfile(EXAMPLE_PATH, os.path.join(self.project, ".claude",
                                                   "atelier.local.md"))
        code, output = self.check()
        self.assertEqual(code, 0, output)
        for key in ("enforce", "protected", "isolate"):
            self.assertIn("armed", self.row(output, key), output)
        self.assertIn("prose-only", self.row(output, "effort"), output)
        # `handoff` ships commented out: an override naming a file a fresh project does
        # not have would switch handoff surfacing off. See the drift test below.
        self.assertIn("not configured", self.row(output, "handoff"), output)
        self.assertNotIn("inert", output)
        self.assertNotIn("WARN", output)

    def test_shipped_examples_handoff_line_arms_when_uncommented(self):
        """The commented value still has to be a working one."""
        with open(EXAMPLE_PATH, encoding="utf-8") as fh:
            text = fh.read()
        armed = _uncomment_scalar_handoff(text)
        self.assertIn("\nhandoff: ", armed)  # the transform actually fired
        self.write(armed)
        with open(os.path.join(self.project, ".claude", "HANDOFF.md"), "w") as fh:
            fh.write("# handoff\n")

        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("armed", self.row(output, "handoff"), output)
        self.assertNotIn("WARN", output)

    def test_shipped_examples_external_handoff_block_arms_when_uncommented(self):
        """Same bar for the second commented form: the external mapping the
        example documents has to be a working one too, not just prose."""
        with open(EXAMPLE_PATH, encoding="utf-8") as fh:
            text = fh.read()
        armed = _uncomment_mapping_handoff(text)
        self.assertIn("\nhandoff:\n", armed)  # the transform actually fired
        self.assertIn("\n  mode: external\n", armed)
        self.write(armed)

        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "handoff")
        self.assertIn("armed", row, output)
        self.assertIn("external", row, output)
        # The example's `location:` parsed, rather than degrading to the
        # no-location wording.
        self.assertIn("handoff lives at:", row)
        self.assertNotIn("no location set", row)
        # The example's stamp is deliberately a file a fresh project does not
        # have yet, so the row is armed AND warned about.
        self.assertIn("WARN", output)
        self.assertIn("stamp file does not exist yet", output)

    def test_unknown_key_is_flagged_with_a_suggestion(self):
        self.write("---\nenfroce: strict\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        row = self.row(output, "enfroce")
        self.assertIn("unknown key", row)
        self.assertIn("enforce", row)
        # ...and the real key reads as absent, which is the silent failure.
        self.assertIn("not configured", self.row(output, "enforce"))

    def test_protected_branches_reports_armed_when_set(self):
        self.write("---\nprotected-branches:\n  - main\n  - release\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "protected-branches")
        self.assertIn("armed", row)
        self.assertIn("main, release", row)
        self.assertIn("worker-git-scope-guard", row)

    def test_protected_branches_reports_not_configured_when_absent(self):
        self.write("---\nenforce: strict\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("not configured", self.row(output, "protected-branches"))

    def test_protected_branches_explicit_empty_list_is_off_not_inert(self):
        """`[]` is the documented off value (SKILL.md), not a mistake."""
        self.write("---\nprotected-branches: []\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "protected-branches")
        self.assertIn("off (explicit)", row)
        self.assertNotIn("inert", row)

    def test_protected_branches_scalar_is_inert(self):
        """A scalar where a sequence belongs is a genuine mistake, unlike `[]`."""
        self.write("---\nprotected-branches: main\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("inert", self.row(output, "protected-branches"))

    def test_protected_branches_is_armed_without_enforce(self):
        """Unlike `protected`, its hook never consults `enforce`."""
        self.write("---\nprotected-branches: [main]\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("armed", self.row(output, "protected-branches"))

    def test_isolate_explicit_empty_list_is_off_not_inert(self):
        """`[]` is the documented off value (SKILL.md), not a mistake."""
        self.write("---\nisolate: []\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "isolate")
        self.assertIn("off (explicit)", row)
        self.assertNotIn("inert", row)

    def test_isolate_unknown_word_is_inert(self):
        self.write("---\nisolate: bogus\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("inert", self.row(output, "isolate"))

    def test_the_two_protected_keys_do_not_bleed_into_each_other(self):
        self.write("---\nenforce: strict\nprotected:\n  - Makefile\n"
                   "protected-branches:\n  - main\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("Makefile", self.row(output, "protected"))
        self.assertNotIn("Makefile", self.row(output, "protected-branches"))
        self.assertIn("main", self.row(output, "protected-branches"))
        self.assertNotIn("main", self.row(output, "protected"))

    def test_text_before_the_fence_means_the_file_is_ignored(self):
        self.write("# my project notes\n\n---\nenforce: strict\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("IGNORED", output)
        self.assertIn("every hook", output)

    def test_no_closing_fence_means_the_file_is_ignored(self):
        self.write("---\nenforce: strict\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("IGNORED", output)

    def test_protected_without_enforce_is_inert(self):
        self.write("---\nprotected:\n  - Makefile\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        row = self.row(output, "protected")
        self.assertIn("inert", row)
        self.assertIn("enforce is off", row)
        self.assertIn("Makefile", row)

    def test_trailing_comment_on_the_bare_key_line_still_reads_protected(self):
        """A comment where the value belongs is not a value.

        This answer INVERTED when the hooks' seven private parsers were consolidated
        onto `_lib/atelier_local.py` (card ef7m). config-custody used to read
        `# patterns` as the key's value, so the block never opened and the list came
        back empty; the handoff hooks and context-watermark already read the same
        shape as an empty value. The shared parser takes the second reading, which is
        YAML's. The `protected` row's inert wording still names a trailing comment as
        a cause — that text is activation.py's and is now stale.
        """
        self.write("---\nenforce: strict\nprotected:  # patterns\n  - Makefile\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "protected")
        self.assertIn("armed", row)
        self.assertIn("Makefile", row)

    def test_handoff_outside_the_project_root_is_inert(self):
        self.write("---\nhandoff: ../../etc/passwd\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        row = self.row(output, "handoff")
        self.assertIn("inert", row)
        self.assertIn("outside the project root", row)

    def test_handoff_inside_the_root_but_missing_is_armed_with_a_warning(self):
        self.write("---\nhandoff: docs/HANDOFF.md\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("armed", self.row(output, "handoff"))
        self.assertIn("WARN", output)
        self.assertIn("do NOT fall back", output)

    # -- handoff, mapping form ---------------------------------------------

    def _write_handoff_mapping(self, **children):
        lines = ["---", "handoff:"]
        for key, value in children.items():
            if value is not None:
                lines.append("  {0}: {1}".format(key, value))
        lines.append("---")
        return self.write("\n".join(lines) + "\n")

    def test_external_handoff_with_an_existing_stamp_is_armed(self):
        stamp = os.path.join(self.project, ".claude", "handoff.stamp")
        with open(stamp, "w", encoding="utf-8") as fh:
            fh.write("touched\n")
        self._write_handoff_mapping(mode="external", stamp=".claude/handoff.stamp",
                                    location="Kaneo board task DFA-233")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "handoff")
        self.assertIn("armed", row)
        self.assertIn("external", row)
        self.assertIn(stamp, row)
        self.assertIn("Kaneo board task DFA-233", row)
        self.assertNotIn("WARN", output)

    def test_external_handoff_without_the_stamp_file_is_armed_with_a_warning(self):
        self._write_handoff_mapping(mode="external", stamp=".claude/handoff.stamp",
                                    location="Kaneo board task DFA-233")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("armed", self.row(output, "handoff"), output)
        self.assertIn("WARN", output)
        self.assertIn("stamp file does not exist yet", output)
        self.assertIn("blocks a manual /compact", output)
        self.assertIn("surfacer still points", output)

    def test_external_handoff_without_a_location_says_so(self):
        self._write_handoff_mapping(mode="external", stamp=".claude/handoff.stamp")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("no location set", self.row(output, "handoff"), output)

    def test_external_handoff_without_a_stamp_is_inert(self):
        self._write_handoff_mapping(mode="external",
                                    location="Kaneo board task DFA-233")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        row = self.row(output, "handoff")
        self.assertIn("inert", row)
        self.assertIn("stamp", row)
        self.assertIn("standard search", row)

    def test_external_handoff_with_an_out_of_root_stamp_is_inert(self):
        self._write_handoff_mapping(mode="external", stamp="../../etc/passwd",
                                    location="Kaneo board task DFA-233")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        row = self.row(output, "handoff")
        self.assertIn("inert", row)
        self.assertIn("stamp", row)

    def test_unknown_handoff_mode_is_inert_and_names_the_bad_value(self):
        self._write_handoff_mapping(mode="board", stamp=".claude/handoff.stamp")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        row = self.row(output, "handoff")
        self.assertIn("inert", row)
        self.assertIn("'board'", row)

    def test_file_mode_mapping_arms_the_same_way_the_bare_scalar_does(self):
        os.makedirs(os.path.join(self.project, "docs"))
        with open(os.path.join(self.project, "docs", "HANDOFF.md"), "w") as fh:
            fh.write("# handoff\n")
        self._write_handoff_mapping(mode="file", path="docs/HANDOFF.md")
        mapping_code, mapping_output = self.check()

        self.write("---\nhandoff: docs/HANDOFF.md\n---\n")
        scalar_code, scalar_output = self.check()

        self.assertEqual(mapping_code, 0, mapping_output)
        self.assertEqual(mapping_code, scalar_code)
        self.assertEqual(self.row(mapping_output, "handoff"),
                         self.row(scalar_output, "handoff"))

    def test_a_nested_handoff_mapping_does_not_swallow_the_keys_after_it(self):
        """Both hooks stop the mapping scan at the first unindented line. If
        one ran on, `protected:`'s list items would land in the handoff key and
        wipe it -- and the checker would report an inert handoff next to a
        protected row that still looks fine, which is the confusing shape."""
        self.write("---\nenforce: strict\nhandoff:\n  mode: external\n"
                   "  stamp: .claude/handoff.stamp\n"
                   "  location: Kaneo board task DFA-233\n"
                   "protected:\n  - Makefile\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("armed", self.row(output, "handoff"), output)
        self.assertIn("external", self.row(output, "handoff"), output)
        self.assertIn("Makefile", self.row(output, "protected"), output)

    def test_an_uppercase_handoff_mode_arms_external(self):
        """`mode` is lowercased before it is matched. Both hooks must do it:
        if only one does, the row is a DISAGREEMENT rather than armed."""
        self._write_handoff_mapping(mode="EXTERNAL", stamp=".claude/handoff.stamp",
                                    location="Kaneo board task DFA-233")
        code, output = self.check()
        row = self.row(output, "handoff")
        self.assertNotIn("DISAGREEMENT", row)
        self.assertIn("armed", row)
        self.assertIn("external", row)
        self.assertEqual(code, 0, output)

    def test_the_mapping_form_always_registers_as_a_present_top_level_key(self):
        """`not configured` for a written key is the silent failure this
        whole tool exists to catch -- the nested form must never report it,
        armed or inert."""
        shapes = (
            {"mode": "external", "stamp": ".claude/handoff.stamp"},
            {"mode": "external"},
            {"mode": "external", "stamp": "../../etc/passwd"},
            {"mode": "board", "stamp": ".claude/handoff.stamp"},
            {"mode": "file", "path": "docs/HANDOFF.md"},
            {"mode": "file"},
        )
        for shape in shapes:
            with self.subTest(**shape):
                self._write_handoff_mapping(**shape)
                _, output = self.check()
                self.assertNotIn("not configured", self.row(output, "handoff"), output)

    def test_oversized_file_is_reported_as_oversized_not_as_bad_values(self):
        """Every hook bails on size before parsing, so the report must blame the size."""
        worker = _load(os.path.join(HOOKS_DIR, "worker-context", "hook.py"),
                       "cap_probe_worker_context")
        cap = worker.ACTIVATION_MAX_BYTES
        self.write("---\nenforce: strict\n---\n" + ("x" * (cap + 1)))
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("too large", output)
        self.assertIn(str(cap), output)
        self.assertNotIn("advisory/strict", output)

    def test_a_key_written_twice_takes_the_last_value(self):
        """Matches the hooks: their parsers overwrite, they do not stop at the first."""
        self.write("---\neffort: deep\neffort: extreme\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("'extreme'", self.row(output, "effort"))

    def test_watermark_reports_per_layer_only_when_the_layers_differ(self):
        self.write("---\nwatermark:\n  soft: 90000\n  session:\n    soft: 200000\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("soft=200000", self.row(output, "watermark.session"))
        self.assertIn("soft=90000", self.row(output, "watermark.worker"))
        self.write("---\nwatermark:\n  session: {hard: 250000}\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("armed", self.row(output, "watermark.session"))
        self.assertIn("not configured", self.row(output, "watermark.worker"))
        self.write("---\nwatermark:\n  soft: 90000\n---\n")
        code, output = self.check()
        self.assertIn("soft=90000", self.row(output, "watermark"))
        self.assertNotIn("watermark.", output)

    def test_unknown_effort_value_is_inert(self):
        self.write("---\neffort: extreme\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("inert", self.row(output, "effort"))

    def test_effort_alone_is_reported_as_prose_only(self):
        self.write("---\neffort: deep  # trailing comment\n---\n")
        code, output = self.check()
        self.assertEqual(code, 0, output)
        row = self.row(output, "effort")
        self.assertIn("prose-only", row)
        self.assertIn("deep", row)
        self.assertIn("no hook", row)


class CheckoutRootTests(_Base):
    """`checkout-root` is read directly from `atelier_local.checkout_root`, not
    through a hook loader, so it needs a real git repo (the function shells out to
    `git rev-parse --git-common-dir`)."""

    def setUp(self):
        super().setUp()
        require_git()
        self.main, self.worktree = make_worktree(self.tmp.name)
        os.makedirs(os.path.join(self.main, ".claude"), exist_ok=True)

    def test_absent_is_not_configured(self):
        self.write("---\nenforce: strict\n---\n", project=self.main)
        code, output = self.check(project=self.main)
        self.assertEqual(code, 0, output)
        self.assertIn("not configured", self.row(output, "checkout-root"))

    def test_valid_relative_value_resolves_and_is_armed(self):
        self.write("---\nenforce: strict\ncheckout-root: .worktrees\n---\n", project=self.main)
        code, output = self.check(project=self.main)
        self.assertEqual(code, 0, output)
        row = self.row(output, "checkout-root")
        self.assertIn("armed", row)
        self.assertIn(os.path.join(self.main, ".worktrees"), row)

    def test_invalid_value_reports_the_error_not_unknown(self):
        with open(os.path.join(self.main, "afile"), "w") as fh:
            fh.write("x")
        self.write("---\nenforce: strict\ncheckout-root: afile\n---\n", project=self.main)
        code, output = self.check(project=self.main)
        self.assertEqual(code, 1, output)
        row = self.row(output, "checkout-root")
        self.assertIn("checkout-root", row)
        self.assertIn("afile", row)
        self.assertNotIn("unknown key", row)

    def test_unsafe_value_is_reported_as_blocking_isolated_codex_dispatch(self):
        for value in ("/", "..", ".git/worktrees"):
            with self.subTest(value=value):
                self.write("---\nenforce: strict\ncheckout-root: " + value + "\n---\n",
                           project=self.main)
                code, output = self.check(project=self.main)
                self.assertEqual(code, 1, output)
                row = self.row(output, "checkout-root")
                self.assertIn("inert", row)
                self.assertIn("blocks every isolated Codex dispatch", row)
                self.assertNotIn("armed", row)

    def test_outside_the_project_is_reported_as_blocking(self):
        for value in ("/etc", "$HOME"):
            with self.subTest(value=value):
                self.write("---\nenforce: strict\ncheckout-root: " + value + "\n---\n",
                           project=self.main)
                code, output = self.check(project=self.main)
                self.assertEqual(code, 1, output)
                row = self.row(output, "checkout-root")
                self.assertIn("blocks every isolated Codex dispatch", row)
                self.assertNotIn("armed", row)

    def test_separate_git_dir_with_the_key_is_reported_as_blocking(self):
        base = os.path.realpath(self.tmp.name)
        work = os.path.join(base, "sep")
        subprocess.run(["git", "init", "-q", "--separate-git-dir",
                        os.path.join(base, "store.git"), work], check=True, capture_output=True)
        os.makedirs(os.path.join(work, ".claude"))
        self.write("---\nenforce: strict\ncheckout-root: .worktrees\n---\n", project=work)
        code, output = self.check(project=work)
        self.assertEqual(code, 1, output)
        self.assertIn("unsupported git layout", self.row(output, "checkout-root"))
        self.write("---\nenforce: strict\n---\n", project=work)
        code, output = self.check(project=work)
        self.assertEqual(code, 0, output)
        self.assertIn("not configured", self.row(output, "checkout-root"))

    def test_tracked_directory_is_reported_as_blocking(self):
        base = os.path.join(self.tmp.name, "tracked-fixture")
        os.makedirs(base)
        main, _ = make_worktree(base, tracked={"src/a.py": "x"})
        os.makedirs(os.path.join(main, ".claude"), exist_ok=True)
        self.write("---\nenforce: strict\ncheckout-root: src\n---\n", project=main)
        code, output = self.check(project=main)
        self.assertEqual(code, 1, output)
        row = self.row(output, "checkout-root")
        self.assertIn("blocks every isolated Codex dispatch", row)
        self.assertIn("tracked files", row)
        self.assertNotIn("armed", row)

    def test_linked_worktree_reports_the_main_checkout_policy(self):
        # Dispatch reads the main checkout's policy, so check must too.
        self.write("---\nenforce: strict\ncheckout-root: .worktrees\n---\n", project=self.main)
        os.makedirs(os.path.join(self.worktree, ".claude"), exist_ok=True)
        self.write("---\nenforce: strict\ncheckout-root: .elsewhere\n---\n",
                   project=self.worktree)
        code, output = self.check(project=self.worktree)
        self.assertEqual(code, 0, output)
        row = self.row(output, "checkout-root")
        self.assertIn(os.path.join(self.main, ".worktrees"), row)
        self.assertNotIn(".elsewhere", row)


class AgreementTests(_Base):
    """The checker must report exactly what the hooks resolve, never its own reading."""

    def _hook(self, name):
        return _load(os.path.join(HOOKS_DIR, name, "hook.py"),
                     "agreement_hook_" + name.replace("-", "_"))

    def test_enforce_and_protected_match_the_hook_loaders(self):
        self.write("---\nenforce: advisory\nprotected:\n  - Makefile\n"
                   "  - .github/workflows/*\n---\n")
        code, output = self.check()

        mode = self._hook("worker-context")._load_mode(self.project)
        custody_mode, patterns = self._hook("config-custody")._load_activation(self.project)
        self.assertEqual(mode, custody_mode)

        self.assertEqual(code, 0, output)
        self.assertIn(" {0}".format(mode), self.row(output, "enforce"))
        self.assertIn(", ".join(patterns), self.row(output, "protected"))

    def test_protected_branches_matches_the_hook_loader(self):
        self.write("---\nprotected-branches:\n  - main\n  - release\n---\n")
        code, output = self.check()

        branches = self._hook("worker-git-scope-guard")._load_protected_branches(
            self.project)

        self.assertEqual(code, 0, output)
        row = self.row(output, "protected-branches")
        self.assertIn(", ".join(sorted(branches)), row)

    def test_isolate_and_handoff_match_the_hook_loaders(self):
        os.makedirs(os.path.join(self.project, "docs"))
        with open(os.path.join(self.project, "docs", "HANDOFF.md"), "w") as fh:
            fh.write("# handoff\n")
        self.write("---\nisolate: [builder, my-writer]\nhandoff: docs/HANDOFF.md\n---\n")
        code, output = self.check()

        mode, types = self._hook("worktree-isolation")._load_activation(self.project)
        surfacer = self._hook("session-handoff-surfacer")
        resolved = surfacer._resolve_override_path(
            surfacer._load_handoff_override(self.project), self.project)

        self.assertEqual(code, 0, output)
        row = self.row(output, "isolate")
        self.assertIn("{0} -> {1}".format(mode, ", ".join(types)), row)
        self.assertIn(resolved, self.row(output, "handoff"))

    def test_activation_file_env_override_is_honoured_and_reported(self):
        elsewhere = os.path.join(self.tmp.name, "elsewhere.md")
        with open(elsewhere, "w", encoding="utf-8") as fh:
            fh.write("---\nenforce: strict\n---\n")
        os.environ["ATELIER_ACTIVATION_FILE"] = elsewhere

        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn(elsewhere, output)
        self.assertIn("strict", self.row(output, "enforce"))


class CreateTests(_Base):
    def _create(self, *extra):
        buf = io.StringIO()
        code = activation.main(
            ["create", "--project-dir", self.project] + list(extra), out=buf)
        return code, buf.getvalue()

    def test_create_writes_the_example_and_the_result_checks_clean(self):
        code, output = self._create()
        self.assertEqual(code, 0, output)
        dest = os.path.join(self.project, ".claude", "atelier.local.md")
        self.assertTrue(os.path.isfile(dest))
        with open(dest, encoding="utf-8") as fh:
            written = fh.read()
        with open(EXAMPLE_PATH, encoding="utf-8") as fh:
            self.assertEqual(written, fh.read())
        self.assertEqual(self.check()[0], 0)

    def test_create_refuses_to_clobber_without_force(self):
        self.write("---\nenforce: strict\n---\n")
        code, output = self._create()
        self.assertEqual(code, 0, output)
        self.assertIn("left unchanged", output)
        self.assertIn(os.path.join(self.project, ".claude", "atelier.local.md"), output)

        code, output = self._create("--force")
        self.assertEqual(code, 0, output)

    def test_create_appends_the_gitignore_pattern_once(self):
        gitignore = os.path.join(self.project, ".gitignore")
        with open(gitignore, "w", encoding="utf-8") as fh:
            fh.write("logs/\n")
        code, output = self._create()
        self.assertEqual(code, 0, output)
        with open(gitignore, encoding="utf-8") as fh:
            self.assertIn(".claude/*.local.md", fh.read())

        code, output = self._create("--force")
        self.assertIn("already ignores", output)
        with open(gitignore, encoding="utf-8") as fh:
            self.assertEqual(fh.read().count(".claude/*.local.md"), 1)

    def test_create_says_so_when_there_is_no_gitignore(self):
        code, output = self._create()
        self.assertEqual(code, 0, output)
        self.assertIn("no .gitignore", output)


class SchemaDriftTests(unittest.TestCase):
    """Every key the checker knows about must appear in all three docs.

    The key list is imported from the script, never hand-copied: a hand-copied list
    only catches a doc losing a key, and stays green when the code gains one. Adding a
    key to `activation.KEYS` without documenting it turns these red.

    The defect this whole skill answers started as exactly this drift: the bundle README
    lost `handoff:` from its example while the reference doc still carried it.
    """

    def _assert_keys_in(self, path, template):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for key in activation.KEYS:
            token = template.format(key)
            self.assertIn(token, text,
                          "{0} does not document {1}".format(path, token))

    def test_shipped_example_documents_every_key(self):
        self._assert_keys_in(EXAMPLE_PATH, "{0}:")

    def test_bundle_readme_documents_every_key(self):
        self._assert_keys_in(BUNDLE_README, "{0}:")

    def test_skill_md_documents_every_key(self):
        self._assert_keys_in(SKILL_MD, "`{0}`")

    def test_shipped_example_ships_handoff_commented_out(self):
        """Deliberate, and asserted deliberately rather than left to the token check.

        A `handoff:` naming a file a fresh project does not have is authoritative to
        both hooks and suppresses the standard search, so `create` would silently switch
        handoff surfacing off. It ships commented, with the reason next to it.
        """
        with open(EXAMPLE_PATH, encoding="utf-8") as fh:
            lines = [line.strip() for line in fh if "handoff:" in line]
        self.assertTrue(lines, "the example no longer mentions handoff:")
        for line in lines:
            self.assertTrue(line.startswith("#"),
                            "handoff: must ship commented out, got: " + line)
        with open(EXAMPLE_PATH, encoding="utf-8") as fh:
            self.assertIn("turns handoff surfacing off", fh.read())

    def test_docs_use_the_plugin_root_invocation(self):
        """Bash runs from the project dir, so a bare `scripts/...` path cannot resolve."""
        for path in (SKILL_MD, BUNDLE_README, EXAMPLE_PATH):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn(INVOCATION, text,
                          "{0} does not show the $CLAUDE_PLUGIN_ROOT invocation".format(path))
            self.assertNotIn("python3 scripts/activation.py", text,
                             "{0} shows an invocation that cannot resolve".format(path))


if __name__ == "__main__":
    unittest.main()

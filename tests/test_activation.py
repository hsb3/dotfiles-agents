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

SCRUBBED_ENV = ("CLAUDE_PROJECT_DIR", "ATELIER_ACTIVATION_FILE")

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
        self.write(text.replace("# handoff:", "handoff:"))
        with open(os.path.join(self.project, ".claude", "HANDOFF.md"), "w") as fh:
            fh.write("# handoff\n")

        code, output = self.check()
        self.assertEqual(code, 0, output)
        self.assertIn("armed", self.row(output, "handoff"), output)
        self.assertNotIn("WARN", output)

    def test_unknown_key_is_flagged_with_a_suggestion(self):
        self.write("---\nenfroce: strict\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        row = self.row(output, "enfroce")
        self.assertIn("unknown key", row)
        self.assertIn("enforce", row)
        # ...and the real key reads as absent, which is the silent failure.
        self.assertIn("not configured", self.row(output, "enforce"))

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

    def test_trailing_comment_empties_protected(self):
        self.write("---\nenforce: strict\nprotected:  # patterns\n  - Makefile\n---\n")
        code, output = self.check()
        self.assertEqual(code, 1, output)
        self.assertIn("inert", self.row(output, "protected"))

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
        self.assertEqual(code, 1, output)
        self.assertIn("refused", output)
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

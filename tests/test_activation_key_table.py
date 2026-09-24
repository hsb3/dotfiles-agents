"""One table of frontmatter lines for `isolate` / `protected` / `protected-branches`,
driven through three independent readers: `atelier_local.parse_key` directly, each
key's own hook resolver, and `activation.py check`'s reported verdict.

The rows center on `_strip_comment` in `parse_key`, which strips an unquoted
trailing `#` comment before the inline-list test fires. The point of running one
table through three readers is that a future second parser can agree with
`parse_key` by accident on the easy rows and drift on this one -- so it fails here
instead of only in `test_atelier_local.py`'s corpus.

Stdlib-only; fixtures live in tempdirs, one per test.
"""

import importlib.util
import io
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS_DIR = os.path.join(REPO_ROOT, "primitives-core", "hooks")
ACTIVATION_SCRIPT = os.path.join(
    REPO_ROOT, "primitives-core", "skills", "activation", "scripts", "activation.py")

SCRUBBED_ENV = ("CLAUDE_PROJECT_DIR", "ATELIER_ACTIVATION_FILE")
KEYS = ("isolate", "protected", "protected-branches")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Bytecode caching off: importing these by path would otherwise drop a
    # __pycache__ directory into the shipped tree on every test run.
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


atelier_local = _load(os.path.join(HOOKS_DIR, "_lib", "atelier_local.py"),
                      "key_table_atelier_local")
worktree_isolation = _load(os.path.join(HOOKS_DIR, "worktree-isolation", "hook.py"),
                           "key_table_worktree_isolation")
config_custody = _load(os.path.join(HOOKS_DIR, "config-custody", "hook.py"),
                       "key_table_config_custody")
scope_guard = _load(os.path.join(HOOKS_DIR, "worker-git-scope-guard", "hook.py"),
                    "key_table_scope_guard")
activation = _load(ACTIVATION_SCRIPT, "key_table_activation_cli")


# ---------------------------------------------------------------------------
# The table: text after "<key>:" -> the value `parse_key` returns for it.
#
# The last two rows are malformed (an unclosed `[`, and junk trailing a closed
# `]`). `parse_key` makes no attempt to repair either -- it returns the
# stripped remainder as a plain scalar string. That is CURRENT, PINNED
# behavior, not a spec: a future change to it only needs new expectations here,
# not a rewrite of the table's shape.
# ---------------------------------------------------------------------------
ROWS = (
    ("inline_list_trailing_comment", " [a, b]  # note", ["a", "b"]),
    ("inline_list_trailing_comment_tab", " [a, b]\t# note", ["a", "b"]),
    ("empty_list", " []", []),
    ("empty_list_trailing_comment", " []  # c", []),
    ("quoted_item_containing_hash_space", ' ["a #b", c] # z', ["a #b", "c"]),
    ("unspaced_hash_in_item_stays", " [a#b]", ["a#b"]),
    ("bare_scalar_with_trailing_comment", " bogus  # note", "bogus"),
    ("comment_only_opens_block_form", "  # c", None),
    ("block_list_trailing_comment", "\n  - a  # note\n  - b", ["a", "b"]),
    ("block_list_trailing_comment_tab", "\n  - a\t# note\n  - b", ["a", "b"]),
    ("malformed_unclosed_list_pinned", " [a, b", "[a, b"),
    ("malformed_trailing_junk_pinned", " [a, b] junk", "[a, b] junk"),
)


def _text(key, suffix):
    return "---\nenforce: strict\n{0}:{1}\n---\n".format(key, suffix)


def _isolate_expected(parsed):
    if isinstance(parsed, list):
        return (worktree_isolation.WRITERS, tuple(parsed)) if parsed else (
            worktree_isolation.OFF, ())
    if isinstance(parsed, str) and parsed.lower() == worktree_isolation.WRITERS:
        return worktree_isolation.WRITERS, worktree_isolation.DEFAULT_WRITERS
    return worktree_isolation.OFF, ()


def _verdict(key, parsed):
    """The `activation.py check` state word this row's parsed shape implies.

    `protected` has no off-(explicit) carve-out the way `isolate` and
    `protected-branches` do: an explicit `[]` reads `inert` there, never
    `off (explicit)`. That asymmetry is existing activation.py behavior, not
    something this table asserts should change.
    """
    if isinstance(parsed, list):
        if parsed:
            return "armed"
        return "inert" if key == "protected" else "off (explicit)"
    return "inert"


class _ProjectCase(unittest.TestCase):
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

    def write(self, text):
        path = os.path.join(self.project, ".claude", "atelier.local.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def check_row(self, key):
        buf = io.StringIO()
        activation.main(["check", "--project-dir", self.project], out=buf)
        output = buf.getvalue()
        for line in output.splitlines():
            if line.strip().split(" ")[0] == key:
                return line.strip()
        self.fail("no row for {0!r} in:\n{1}".format(key, output))


class ParseKeyTableTests(_ProjectCase):
    """`parse_key` directly, every row against every key."""


class HookResolverTableTests(_ProjectCase):
    """Each key's own hook resolver, against the same table."""


class CheckVerdictTableTests(_ProjectCase):
    """`activation.py check`'s reported verdict, against the same table."""


def _add_table_cases():
    for row_id, suffix, expected in ROWS:
        for key in KEYS:
            text = _text(key, suffix)
            method_name = "test_{0}__{1}".format(row_id, key.replace("-", "_"))

            def parse_case(self, text=text, key=key, expected=expected):
                self.assertEqual(atelier_local.parse_key(text, key), expected)

            setattr(ParseKeyTableTests, method_name, parse_case)

            def hook_case(self, text=text, key=key, expected=expected):
                self.write(text)
                if key == "isolate":
                    got = worktree_isolation._load_activation(self.project)
                    self.assertEqual(got, _isolate_expected(expected))
                elif key == "protected":
                    got = config_custody._load_activation(self.project)[1]
                    self.assertEqual(got, expected if isinstance(expected, list) else [])
                else:
                    got = scope_guard._load_protected_branches(self.project)
                    want = frozenset(expected) if isinstance(expected, list) else frozenset()
                    self.assertEqual(got, want)

            setattr(HookResolverTableTests, method_name, hook_case)

            def check_case(self, text=text, key=key, expected=expected):
                self.write(text)
                row = self.check_row(key)
                self.assertIn(_verdict(key, expected), row, row)

            setattr(CheckVerdictTableTests, method_name, check_case)


_add_table_cases()


class PerKeyTrailingCommentTests(_ProjectCase):
    """Criterion 2: the trailing-comment inline list arms, once per key."""

    def test_isolate_trailing_comment_list_is_armed(self):
        self.write(_text("isolate", " [builder, x]  # note"))
        self.assertEqual(worktree_isolation._load_activation(self.project),
                         (worktree_isolation.WRITERS, ("builder", "x")))

    def test_protected_trailing_comment_list_is_armed(self):
        self.write(_text("protected", " [Makefile, .github/workflows/*]  # note"))
        self.assertEqual(config_custody._load_activation(self.project)[1],
                         ["Makefile", ".github/workflows/*"])

    def test_protected_branches_trailing_comment_list_is_armed(self):
        self.write(_text("protected-branches", " [main, release]  # note"))
        self.assertEqual(scope_guard._load_protected_branches(self.project),
                         frozenset({"main", "release"}))


if __name__ == "__main__":
    unittest.main()

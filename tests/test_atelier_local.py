"""Tests for primitives-core/hooks/_lib/atelier_local.py and the seven hooks that read
`.claude/atelier.local.md` through it.

Two layers, and the second is the one that matters:

  * `ParseKeyTests` exercises the shared parser directly — the shapes the activation
    file is allowed to take, and what each answers.
  * `CorpusTests` is a characterization table. One fixture corpus of malformed and
    edge-case activation files, every hook's OWN loader called against each, answers
    pinned. It was written against the seven private parsers this module replaced and
    is the proof that consolidating them moved nothing that was not deliberately
    moved; the four fixtures that DID move are marked `deviation` with the reason.

Every loader is called with a real project dir, so each hook's own path resolution,
size cap and fail-open wrapper are in the loop — only the parsing is shared.

Stdlib-only; fixtures build into a tempdir per test.
"""

import importlib.util
import os
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS_DIR = os.path.join(REPO_ROOT, "primitives-core", "hooks")

SCRUBBED_ENV = ("CLAUDE_PROJECT_DIR", "ATELIER_ACTIVATION_FILE")

HOOK_NAMES = ("worker-context", "config-custody", "worktree-isolation",
              "session-handoff-surfacer", "handoff-freshness-guard",
              "worker-git-scope-guard", "context-watermark")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Bytecode caching off: importing a hook would otherwise drop a __pycache__
    # directory into the shipped tree on every test run.
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = saved
    return module


atelier_local = _load(
    os.path.join(HOOKS_DIR, "_lib", "atelier_local.py"), "atelier_local_under_test")
HOOKS = {
    name: _load(os.path.join(HOOKS_DIR, name, "hook.py"),
                "atelier_local_hook_" + name.replace("-", "_"))
    for name in HOOK_NAMES
}


# ---------------------------------------------------------------------------
# The fixture corpus
# ---------------------------------------------------------------------------

FULL = (
    "---\n"
    "enforce: strict\n"
    "protected:\n"
    "  - Makefile\n"
    "  - .github/workflows/*\n"
    "protected-branches:\n"
    "  - main\n"
    "isolate: writers\n"
    "handoff: docs/HANDOFF.md\n"
    "watermark:\n"
    "  soft: 90000\n"
    "  hard: 130000\n"
    "---\n"
)

CORPUS = {
    "absent": None,
    "empty": "",
    "no-fences": "enforce: strict\nprotected:\n  - a\nisolate: writers\n",
    "no-closing-fence": "---\nenforce: strict\nprotected:\n  - a\nisolate: writers\n",
    "fence-not-first": "hi\n---\nenforce: strict\nisolate: writers\n---\n",
    "bom": "﻿" + FULL,
    "full": FULL,
    "dot-dot-fence": "---\nenforce: strict\nisolate: writers\n...\n",
    "blank-values": (
        "---\nenforce:\nprotected:\nisolate:\nprotected-branches:\n"
        "handoff:\nwatermark:\n---\n"
    ),
    "twice-scalar": (
        "---\nenforce: advisory\nenforce: strict\n"
        "isolate: [a]\nisolate: [b]\n"
        "handoff: one.md\nhandoff: two.md\n---\n"
    ),
    "twice-sequence": (
        "---\nprotected:\n  - a\nprotected: [b]\n"
        "protected-branches:\n  - main\nprotected-branches: [dev]\n---\n"
    ),
    "mixed-list-then-scalar": (
        "---\nisolate: [x]\nisolate: writers\n"
        "protected: [a]\nprotected: junk\n---\n"
    ),
    "mixed-scalar-then-list": (
        "---\nisolate: writers\nisolate: [x]\n"
        "protected: junk\nprotected: [a]\n---\n"
    ),
    "quoted-hash": (
        "---\nenforce: 'strict'\nprotected:\n  - \"a#b\"\n"
        "handoff: \"docs/H#1.md\"\nisolate: [\"bu#lder\"]\n---\n"
    ),
    "trailing-comment": (
        "---\nenforce: strict  # note\nisolate: writers  # note\n"
        "handoff: docs/H.md  # note\nprotected:\n  - Makefile  # note\n---\n"
    ),
    "comment-as-value": (
        "---\nenforce:  # note\nprotected:  # note\n  - a\n"
        "protected-branches:  # note\n  - main\nisolate:  # note\n  - builder\n"
        "handoff:  # note\n  mode: external\n  stamp: .claude/s\n"
        "watermark:  # note\n  soft: 90000\n---\n"
    ),
    "unknown-value": "---\nenforce: banana\nisolate: banana\n---\n",
    "seq-where-scalar": (
        "---\nenforce:\n  - strict\nhandoff:\n  - docs/H.md\n"
        "watermark:\n  - soft\n---\n"
    ),
    "scalar-where-seq": "---\nprotected: Makefile\nprotected-branches: main\n---\n",
    "non-kv-item": (
        "---\nenforce: strict\nnonsense\nprotected:\n  - a\nisolate: writers\n---\n"
    ),
    "unindented-seq": (
        "---\nprotected:\n- a\n- b\nprotected-branches:\n- main\n"
        "isolate:\n- builder\n---\n"
    ),
    "unindented-comment-in-block": (
        "---\nprotected:\n# c\n  - a\n"
        "handoff:\n# c\n  mode: external\n  stamp: .claude/s\n"
        "watermark:\n# c\n  soft: 90000\n---\n"
    ),
    "unindented-junk-in-block": (
        "---\nprotected:\nnonsense\n  - a\n"
        "handoff:\nnonsense\n  mode: external\n  stamp: .claude/s\n---\n"
    ),
    "inline-list": (
        "---\nprotected: [\"a b\", c]\nprotected-branches: [main, \"re/*\"]\n"
        "isolate: [builder, my-writer]\n---\n"
    ),
    "empty-inline-list": "---\nprotected: []\nisolate: []\nprotected-branches: []\n---\n",
    "bare-dash": (
        "---\nprotected:\n  -\n  - a\nprotected-branches:\n  -\n  - main\n---\n"
    ),
    "nested-key-under-other": (
        "---\nhandoff:\n  enforce: strict\n  mode: file\n  path: docs/H.md\n"
        "protected:\n  enforce: strict\n---\n"
    ),
    "uppercase-keys": "---\nENFORCE: STRICT\nPROTECTED:\n  - a\nISOLATE: WRITERS\n---\n",
    "oversize": "---\nenforce: strict\n---\n" + "x" * (256 * 1024 + 10),
}


def _handoff(**kwargs):
    """The shape both handoff hooks normalize to."""
    shape = {"mode": "file", "path": None, "stamp": None, "location": None}
    shape.update(kwargs)
    return shape


# Every hook's shipped default: what an absent activation file resolves to. A fixture's
# entry below lists only what differs from this, so a bare `{}` means "nothing is armed".
INERT = {
    "enforce/worker-context": "off",
    "enforce/config-custody": "off",
    "protected/config-custody": [],
    "protected-branches/scope-guard": [],
    "isolate/worktree-isolation": ("off", ()),
    "handoff/freshness": None,
    "handoff/surfacer": None,
    "watermark/context-watermark": {},
}

DEFAULT_WRITERS = ("builder", "manager", "general-purpose")

# What `FULL` resolves to: every key written in its ordinary form.
ARMED = {
    "enforce/worker-context": "strict",
    "enforce/config-custody": "strict",
    "protected/config-custody": ["Makefile", ".github/workflows/*"],
    "protected-branches/scope-guard": ["main"],
    "isolate/worktree-isolation": ("writers", DEFAULT_WRITERS),
    "handoff/freshness": _handoff(path="docs/HANDOFF.md"),
    "handoff/surfacer": _handoff(path="docs/HANDOFF.md"),
    "watermark/context-watermark": {"soft": 90000, "hard": 130000},
}

EXPECTED = {
    "absent": {},
    "empty": {},
    "no-fences": {},
    "no-closing-fence": {},
    "fence-not-first": {},
    "oversize": {},
    "blank-values": {},
    "unknown-value": {},
    "scalar-where-seq": {},
    "seq-where-scalar": {},
    "empty-inline-list": {},

    "full": ARMED,
    "bom": ARMED,  # a leading BOM must not hide the opening fence
    "dot-dot-fence": {
        "enforce/worker-context": "strict",
        "enforce/config-custody": "strict",
        "isolate/worktree-isolation": ("writers", DEFAULT_WRITERS),
    },
    "twice-scalar": {
        "enforce/worker-context": "strict",
        "enforce/config-custody": "strict",
        "isolate/worktree-isolation": ("writers", ("a", "b")),
        "handoff/freshness": _handoff(path="two.md"),
        "handoff/surfacer": _handoff(path="two.md"),
    },
    "twice-sequence": {
        "protected/config-custody": ["a", "b"],
        "protected-branches/scope-guard": ["dev", "main"],
    },
    "mixed-scalar-then-list": {
        "isolate/worktree-isolation": ("writers", ("x",)),
        "protected/config-custody": ["a"],
    },
    "quoted-hash": {
        "enforce/worker-context": "strict",
        "enforce/config-custody": "strict",
        "protected/config-custody": ["a#b"],
        "isolate/worktree-isolation": ("writers", ("bu#lder",)),
        "handoff/freshness": _handoff(path="docs/H#1.md"),
        "handoff/surfacer": _handoff(path="docs/H#1.md"),
    },
    "trailing-comment": {
        "enforce/worker-context": "strict",
        "enforce/config-custody": "strict",
        "protected/config-custody": ["Makefile"],
        "isolate/worktree-isolation": ("writers", DEFAULT_WRITERS),
        "handoff/freshness": _handoff(path="docs/H.md"),
        "handoff/surfacer": _handoff(path="docs/H.md"),
    },
    "non-kv-item": {
        "enforce/worker-context": "strict",
        "enforce/config-custody": "strict",
        "protected/config-custody": ["a"],
        "isolate/worktree-isolation": ("writers", DEFAULT_WRITERS),
    },
    "unindented-seq": {
        "protected/config-custody": ["a", "b"],
        "protected-branches/scope-guard": ["main"],
        "isolate/worktree-isolation": ("writers", ("builder",)),
    },
    "inline-list": {
        "protected/config-custody": ["a b", "c"],
        "protected-branches/scope-guard": ["main", "re/*"],
        "isolate/worktree-isolation": ("writers", ("builder", "my-writer")),
    },
    "bare-dash": {
        "protected/config-custody": ["a"],
        "protected-branches/scope-guard": ["main"],
    },
    "nested-key-under-other": {
        "handoff/freshness": _handoff(path="docs/H.md"),
        "handoff/surfacer": _handoff(path="docs/H.md"),
    },
    "uppercase-keys": {
        "enforce/worker-context": "strict",
        "enforce/config-custody": "strict",
        "protected/config-custody": ["a"],
        "isolate/worktree-isolation": ("writers", DEFAULT_WRITERS),
    },

    # -- the four fixtures the consolidation deliberately moved ------------
    # `key:  # note` used to mean two different things depending on which hook read
    # it: the two handoff hooks and context-watermark treated a comment where the
    # value belongs as no value (so the block below it opened), while the three
    # sequence readers treated `# note` as the value (so the block never opened and
    # the list came back empty). The shared parser takes the first reading — it is
    # what YAML does, and the alternative makes `handoff:  # note` resolve a path
    # literally named `# note`. Every flip below arms what the operator wrote on the
    # following lines; none turns an armed key inert.
    "comment-as-value": {
        "protected/config-custody": ["a"],                          # deviation
        "protected-branches/scope-guard": ["main"],                 # deviation
        "isolate/worktree-isolation": ("writers", ("builder",)),    # deviation
        "handoff/freshness": _handoff(mode="external", stamp=".claude/s"),
        "handoff/surfacer": _handoff(mode="external", stamp=".claude/s"),
        "watermark/context-watermark": {"soft": 90000},
    },
    # Same disagreement, second shape: an unindented comment (or unindented junk)
    # inside a key's block. config-custody skipped it and kept reading; the handoff
    # parsers treated any unindented line as the end of the block. Skipping wins.
    "unindented-comment-in-block": {
        "protected/config-custody": ["a"],
        "handoff/freshness": _handoff(mode="external", stamp=".claude/s"),   # deviation
        "handoff/surfacer": _handoff(mode="external", stamp=".claude/s"),    # deviation
        "watermark/context-watermark": {"soft": 90000},                      # deviation
    },
    "unindented-junk-in-block": {
        "protected/config-custody": ["a"],
        "handoff/freshness": _handoff(mode="external", stamp=".claude/s"),   # deviation
        "handoff/surfacer": _handoff(mode="external", stamp=".claude/s"),    # deviation
    },
    # A key written twice in two different forms. The rule is now one rule for every
    # key: the last written FORM wins, and repeated sequence forms merge so naming a
    # list twice never silently shrinks it. `isolate` already behaved this way;
    # `protected` used to keep the earlier list when a later scalar was unreadable.
    "mixed-list-then-scalar": {
        "isolate/worktree-isolation": ("writers", DEFAULT_WRITERS),
        "protected/config-custody": [],                             # deviation
    },
}


def _answers(project):
    """Every hook's own loader, against one project dir."""
    return {
        "enforce/worker-context": HOOKS["worker-context"]._load_mode(project),
        "enforce/config-custody": HOOKS["config-custody"]._load_activation(project)[0],
        "protected/config-custody": HOOKS["config-custody"]._load_activation(project)[1],
        "protected-branches/scope-guard": sorted(
            HOOKS["worker-git-scope-guard"]._load_protected_branches(project)),
        "isolate/worktree-isolation": HOOKS["worktree-isolation"]._load_activation(project),
        "handoff/freshness": HOOKS["handoff-freshness-guard"]._load_handoff_config(project),
        "handoff/surfacer": HOOKS["session-handoff-surfacer"]._load_handoff_config(project),
        "watermark/context-watermark":
            HOOKS["context-watermark"]._load_watermark_config(project),
    }


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = os.path.join(self.tmp.name, "project")
        os.makedirs(os.path.join(self.project, ".claude"), exist_ok=True)

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


# ---------------------------------------------------------------------------
# The shared parser, directly
# ---------------------------------------------------------------------------

def _fm(body):
    return "---\n" + body + "---\n"


class ParseKeyTests(unittest.TestCase):
    def parse(self, body, key):
        return atelier_local.parse_key(_fm(body), key)

    def test_scalar(self):
        self.assertEqual(self.parse("enforce: strict\n", "enforce"), "strict")

    def test_mapping(self):
        self.assertEqual(self.parse("watermark:\n  soft: 9\n  hard: 1\n", "watermark"),
                         {"soft": "9", "hard": "1"})

    def test_block_sequence(self):
        self.assertEqual(self.parse("protected:\n  - a\n  - b\n", "protected"), ["a", "b"])

    def test_nested_mapping_parses_to_a_dict(self):
        """One level of nesting: a bare `sub:` over deeper lines is its own mapping,
        not flattened into the parent (which set `soft` for every layer)."""
        self.assertEqual(
            self.parse("watermark:\n  worker:\n    soft: 160000\n    # c\n    hard: 2\n",
                       "watermark"),
            {"worker": {"soft": "160000", "hard": "2"}})

    def test_flat_key_after_a_nested_block_stays_top_level(self):
        self.assertEqual(
            self.parse("watermark:\n  session:\n    soft: 9\n  complexity: 1.5\n",
                       "watermark"),
            {"session": {"soft": "9"}, "complexity": "1.5"})

    def test_flow_mapping_under_a_sub_key_stays_a_string(self):
        self.assertEqual(
            self.parse("watermark:\n  worker: {soft: 1, hard: 2}\n", "watermark"),
            {"worker": "{soft: 1, hard: 2}"})

    def test_nesting_under_a_sequence_item_is_not_attempted(self):
        self.assertEqual(
            self.parse("protected:\n  - a:\n      b: c\n  - d\n", "protected"),
            ["a:", "d"])

    def test_block_sequence_at_column_zero(self):
        """YAML lets a block sequence sit unindented under its key, and the parsers
        this replaced all accepted it."""
        self.assertEqual(self.parse("protected:\n- a\n- b\n", "protected"), ["a", "b"])

    def test_inline_sequence(self):
        self.assertEqual(self.parse("isolate: [builder, my-writer]\n", "isolate"),
                         ["builder", "my-writer"])

    def test_inline_sequence_respects_quotes(self):
        self.assertEqual(self.parse('protected: ["a, b", c]\n', "protected"), ["a, b", "c"])

    def test_empty_inline_sequence_is_an_empty_list_not_none(self):
        """`[]` is an explicit empty intent, distinct from an absent key."""
        self.assertEqual(self.parse("protected: []\n", "protected"), [])

    def test_absent_key_is_none(self):
        self.assertIsNone(self.parse("enforce: strict\n", "protected"))

    def test_blank_key_is_none(self):
        self.assertIsNone(self.parse("protected:\nenforce: strict\n", "protected"))

    def test_bare_dash_is_skipped_without_closing_the_sequence(self):
        self.assertEqual(self.parse("protected:\n  -\n  - a\n", "protected"), ["a"])

    def test_sequence_ends_at_the_next_top_level_key(self):
        self.assertEqual(
            self.parse("protected:\n  - a\nenforce: strict\n  - b\n", "protected"), ["a"])

    def test_comment_where_the_value_belongs_opens_the_block(self):
        self.assertEqual(self.parse("protected:  # note\n  - a\n", "protected"), ["a"])
        self.assertEqual(self.parse("watermark:  # note\n  soft: 9\n", "watermark"),
                         {"soft": "9"})

    def test_comment_inside_a_block_is_skipped_at_any_indent(self):
        self.assertEqual(self.parse("protected:\n# c\n  - a\n", "protected"), ["a"])
        self.assertEqual(self.parse("watermark:\n# c\n  soft: 9\n", "watermark"),
                         {"soft": "9"})

    def test_repeated_sequence_forms_merge(self):
        self.assertEqual(self.parse("protected:\n  - a\nprotected: [b]\n", "protected"),
                         ["a", "b"])

    def test_the_last_written_form_wins(self):
        self.assertEqual(self.parse("enforce: a\nenforce: b\n", "enforce"), "b")
        self.assertEqual(self.parse("isolate: [x]\nisolate: writers\n", "isolate"),
                         "writers")

    def test_no_frontmatter_is_none(self):
        self.assertIsNone(atelier_local.parse_key("enforce: strict\n", "enforce"))

    def test_no_closing_fence_is_none(self):
        self.assertIsNone(atelier_local.parse_key("---\nenforce: strict\n", "enforce"))

    def test_key_lookup_is_case_insensitive(self):
        self.assertEqual(self.parse("ENFORCE: strict\n", "enforce"), "strict")

    def test_indented_key_is_not_top_level(self):
        self.assertIsNone(self.parse("handoff:\n  enforce: strict\n", "enforce"))

    def test_unquote_strips_a_trailing_comment_but_not_one_inside_quotes(self):
        self.assertEqual(atelier_local.unquote("strict  # armed"), "strict")
        self.assertEqual(atelier_local.unquote('"a#b"'), "a#b")


# ---------------------------------------------------------------------------
# The characterization corpus, through each hook's own loader
# ---------------------------------------------------------------------------

class CorpusTests(_Base):
    def test_every_fixture_is_expected(self):
        """A fixture with no entry in EXPECTED would silently assert nothing."""
        self.assertEqual(sorted(CORPUS), sorted(EXPECTED))

    def _run(self, name):
        text = CORPUS[name]
        if text is not None:
            self.write(text)
        expected = dict(INERT)
        expected.update(EXPECTED[name])
        self.assertEqual(_answers(self.project), expected, name)


def _add_corpus_cases():
    """One test method per fixture, so a failure names the fixture."""
    for name in CORPUS:
        method = "test_corpus_" + name.replace("-", "_")
        setattr(CorpusTests, method, lambda self, n=name: self._run(n))


_add_corpus_cases()


# ---------------------------------------------------------------------------
# Two hooks, one file, one key
# ---------------------------------------------------------------------------

class CrossHookAgreementTests(_Base):
    """Card ef7m's fourth criterion: the two keys read by more than one hook resolve
    identically through each hook's own loader."""

    def test_the_two_handoff_hooks_agree_on_the_mapping_form(self):
        self.write("---\nhandoff:\n  mode: external\n  stamp: .claude/s\n"
                   "  location: the board\n---\n")
        freshness = HOOKS["handoff-freshness-guard"]._load_handoff_config(self.project)
        surfacer = HOOKS["session-handoff-surfacer"]._load_handoff_config(self.project)
        self.assertEqual(freshness, surfacer)
        self.assertEqual(freshness["mode"], "external")

    def test_the_two_handoff_hooks_agree_on_a_malformed_key(self):
        self.write("---\nhandoff:\n  - docs/HANDOFF.md\n---\n")
        self.assertIsNone(
            HOOKS["handoff-freshness-guard"]._load_handoff_config(self.project))
        self.assertIsNone(
            HOOKS["session-handoff-surfacer"]._load_handoff_config(self.project))

    def test_the_two_enforce_hooks_agree(self):
        self.write("---\nenforce: advisory\n---\n")
        self.assertEqual(HOOKS["worker-context"]._load_mode(self.project), "advisory")
        self.assertEqual(
            HOOKS["config-custody"]._load_activation(self.project)[0], "advisory")

    def test_the_two_enforce_hooks_agree_on_an_unknown_value(self):
        self.write("---\nenforce: banana\n---\n")
        self.assertEqual(HOOKS["worker-context"]._load_mode(self.project), "off")
        self.assertEqual(
            HOOKS["config-custody"]._load_activation(self.project)[0], "off")

    def test_the_two_file_path_keys_never_bleed_into_each_other(self):
        """`protected` is file globs, `protected-branches` is branch names."""
        self.write("---\nprotected:\n  - Makefile\nprotected-branches:\n  - main\n---\n")
        self.assertEqual(
            HOOKS["config-custody"]._load_activation(self.project)[1], ["Makefile"])
        self.assertEqual(
            HOOKS["worker-git-scope-guard"]._load_protected_branches(self.project),
            frozenset({"main"}))


# ---------------------------------------------------------------------------
# Fail-open: an out-of-root value leaves the shipped default in force
# ---------------------------------------------------------------------------

class OutOfRootTests(_Base):
    """`handoff` is the only key whose value is a path the hooks resolve, so it is the
    only one with an out-of-root rule (docs/override-convention.md). Both hooks must
    reject the same value."""

    def test_both_handoff_hooks_reject_a_path_outside_the_project(self):
        for name in ("handoff-freshness-guard", "session-handoff-surfacer"):
            self.assertIsNone(
                HOOKS[name]._resolve_override_path("../../etc/passwd", self.project),
                name)

    def test_both_handoff_hooks_accept_a_path_inside_the_project(self):
        for name in ("handoff-freshness-guard", "session-handoff-surfacer"):
            self.assertEqual(
                HOOKS[name]._resolve_override_path("docs/H.md", self.project),
                os.path.join(self.project, "docs", "H.md"), name)


class PolicyPlacementTests(_Base):
    def test_multiple_native_agents_use_the_shared_policy(self):
        os.makedirs(os.path.join(self.project, ".claude"), exist_ok=True)
        os.makedirs(os.path.join(self.project, ".codex"))
        self.assertEqual(
            atelier_local.activation_path(self.project, inherit=False),
            os.path.join(self.project, ".agents", "atelier.local.md"))

    def test_multiple_agents_fall_back_to_an_existing_native_policy(self):
        os.makedirs(os.path.join(self.project, ".codex"))
        path = os.path.join(self.project, ".claude", "atelier.local.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\nenforce: strict\n---\n")
        self.assertEqual(atelier_local.activation_path(self.project, inherit=False), path)

    def test_shared_policy_outranks_one_native_policy(self):
        path = os.path.join(self.project, ".agents", "atelier.local.md")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\nenforce: strict\n---\n")
        self.assertEqual(atelier_local.activation_path(self.project, inherit=False), path)

    def test_shared_policy_is_discovered_without_a_native_directory(self):
        os.rmdir(os.path.join(self.project, ".claude"))
        path = os.path.join(self.project, ".agents", "atelier.local.md")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("---\nenforce: strict\n---\n")
        self.assertEqual(atelier_local.activation_path(self.project, inherit=False), path)


# ---------------------------------------------------------------------------
# The consolidation itself
# ---------------------------------------------------------------------------

class NoPrivateParserTests(unittest.TestCase):
    def test_no_hook_keeps_a_private_frontmatter_parser(self):
        """Card ef7m's first criterion, checked against the source rather than trusted:
        the parser lives in `_lib/atelier_local.py` and nowhere else."""
        banned = ("def _parse_frontmatter", "def _parse_handoff_config",
                  "def _split_inline_list")
        for name in HOOK_NAMES:
            path = os.path.join(HOOKS_DIR, name, "hook.py")
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            for marker in banned:
                self.assertNotIn(marker, source, "{0}: {1}".format(name, marker))

    def test_every_reader_imports_the_shared_module(self):
        for name in HOOK_NAMES:
            path = os.path.join(HOOKS_DIR, name, "hook.py")
            with open(path, encoding="utf-8") as fh:
                source = fh.read()
            self.assertIn("import atelier_local", source, name)


if __name__ == "__main__":
    unittest.main()

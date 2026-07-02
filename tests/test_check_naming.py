"""Tests for scripts/check_naming.py -- the naming-taxonomy lint (manifests/naming.md).

Per-kind pass/fail fixtures (skill/agent/mcp kebab; the hook <plugin>.<Event>.<slug>
grammar; client-token + vendor-in-name rules; hooks.json layout; plugins.yaml bundle ids),
the event-list pin against manifests/naming.md, a cross-repo drift guard against the
workbench's promote_check.py constants (skipped when the sibling repo is absent), and a
clean-tree smoke of main(). Stdlib-only.
"""

import importlib.util
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import check_naming as N  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMING_MD = os.path.join(REPO, "manifests", "naming.md")
WORKBENCH_PROMOTE_CHECK = os.path.join(
    os.path.dirname(REPO), "dotfiles-agents-workbench", "scripts", "promote_check.py"
)

CANONICAL_EVENTS = (
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "UserPromptSubmit",
    "SubagentStop",
    "Notification",
    "PreCompact",
    "SessionEnd",
)


def _entry(**over):
    """A naming-clean parsed roster entry (values as parse_roster produces: raw strings)."""
    e = {
        "id": "fixture-skill",
        "type": "skill",
        "source": "primitives-core/skills/fixture-skill",
        "shelf": "core",
        "origin": "authored",
        "disposition": "untriaged",
        "vendor": "null",
        "targets": "[claude-code]",
        "plugins": "[]",
        "summary": '"ok"',
    }
    e.update(over)
    return e


def _hook_entry(**over):
    """A naming-clean hook entry mirroring the real dev-focus hooks."""
    e = _entry(
        id="dev-focus.SessionStart.session-start",
        type="hook",
        source=(
            "primitives-core/hooks/dev-focus/hooks-handlers/"
            "dev-focus.SessionStart.session-start.sh"
        ),
        shelf="toggle",
        plugins="[dev-focus]",
    )
    e.update(over)
    return e


def _problems(e):
    problems = []
    N.check_entry_naming(e, problems)
    return problems


class Constants(unittest.TestCase):
    def test_events_tuple_is_the_canonical_harness_list(self):
        self.assertEqual(N.EVENTS, CANONICAL_EVENTS)

    def test_events_pinned_to_naming_md(self):
        """manifests/naming.md is canonical — every event must appear there verbatim."""
        text = open(NAMING_MD, encoding="utf-8").read()
        for ev in N.EVENTS:
            self.assertIn(f"`{ev}`", text, f"{ev} missing from manifests/naming.md")

    def test_client_tokens_match_the_ratified_list(self):
        self.assertEqual(
            set(N.CLIENT_TOKENS),
            {
                "functionform",
                "ra-platform",
                "ra-labs",
                "raptorxai",
                "raptorgpt",
                "headcase",
            },
        )

    @unittest.skipUnless(
        os.path.isfile(WORKBENCH_PROMOTE_CHECK),
        "sibling dotfiles-agents-workbench checkout not present",
    )
    def test_no_grammar_drift_against_workbench_promote_check(self):
        """Both repos carry their own constant table pinned to manifests/naming.md —
        when the sibling checkout is present, assert they haven't drifted apart."""
        spec = importlib.util.spec_from_file_location(
            "workbench_promote_check", WORKBENCH_PROMOTE_CHECK
        )
        wb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wb)
        self.assertEqual(tuple(wb.EVENTS), N.EVENTS)
        self.assertEqual(set(wb.CLIENT_TOKENS), set(N.CLIENT_TOKENS))
        self.assertEqual(wb.KEBAB.pattern, N.KEBAB.pattern)


class KebabIds(unittest.TestCase):
    def test_clean_ids_pass(self):
        for kind, eid in (
            ("skill", "cms-bigquery-etl"),
            ("agent", "python-test-writer"),
            ("mcp", "notion"),
        ):
            self.assertEqual(_problems(_entry(id=eid, type=kind)), [])

    def test_snake_case_skill_fails_naming_id_and_pattern(self):
        problems = _problems(_entry(id="Not_Kebab"))
        self.assertTrue(
            any("[Not_Kebab]" in p and "<domain>-<capability>" in p for p in problems),
            problems,
        )

    def test_camel_case_agent_fails(self):
        problems = _problems(_entry(id="camelCaseAgent", type="agent"))
        self.assertTrue(
            any(
                "[camelCaseAgent]" in p and "<domain>-<role>[-<verb>]" in p
                for p in problems
            ),
            problems,
        )

    def test_snake_case_mcp_fails(self):
        problems = _problems(_entry(id="claude_design", type="mcp"))
        self.assertTrue(
            any("[claude_design]" in p and "<service>" in p for p in problems),
            problems,
        )


class HookGrammar(unittest.TestCase):
    def test_clean_hook_passes(self):
        self.assertEqual(_problems(_hook_entry()), [])

    def test_wrong_case_event_fails(self):
        e = _hook_entry(
            id="dev-focus.postToolUse.session-start",
            source=(
                "primitives-core/hooks/dev-focus/hooks-handlers/"
                "dev-focus.postToolUse.session-start.sh"
            ),
        )
        problems = _problems(e)
        self.assertTrue(
            any("`postToolUse`" in p and "PascalCase" in p for p in problems), problems
        )

    def test_unknown_event_fails(self):
        e = _hook_entry(
            id="dev-focus.OnSave.session-start",
            source=(
                "primitives-core/hooks/dev-focus/hooks-handlers/"
                "dev-focus.OnSave.session-start.sh"
            ),
        )
        problems = _problems(e)
        self.assertTrue(any("`OnSave`" in p for p in problems), problems)

    def test_two_segment_id_fails_structure(self):
        problems = _problems(_hook_entry(id="dev-focus.SessionStart"))
        self.assertTrue(any("<plugin>.<Event>.<slug>" in p for p in problems), problems)

    def test_plugin_segment_must_match_directory(self):
        e = _hook_entry(
            source=(
                "primitives-core/hooks/python-standards/hooks-handlers/"
                "dev-focus.SessionStart.session-start.sh"
            )
        )
        problems = _problems(e)
        self.assertTrue(
            any("hooks/<plugin>/" in p and "python-standards" in p for p in problems),
            problems,
        )

    def test_plugin_segment_must_be_a_plugins_member(self):
        problems = _problems(_hook_entry(plugins="[python-standards]"))
        self.assertTrue(
            any("not among the entry's plugins" in p for p in problems), problems
        )

    def test_handler_filename_must_equal_id_dot_sh(self):
        e = _hook_entry(
            source="primitives-core/hooks/dev-focus/hooks-handlers/session-start.sh"
        )
        problems = _problems(e)
        self.assertTrue(
            any("dev-focus.SessionStart.session-start.sh" in p for p in problems),
            problems,
        )

    def test_non_kebab_slug_fails(self):
        e = _hook_entry(
            id="dev-focus.SessionStart.Session_Start",
            source=(
                "primitives-core/hooks/dev-focus/hooks-handlers/"
                "dev-focus.SessionStart.Session_Start.sh"
            ),
        )
        problems = _problems(e)
        self.assertTrue(
            any("slug" in p and "`Session_Start`" in p for p in problems), problems
        )


class ClientAndVendorRules(unittest.TestCase):
    def test_client_token_in_id_fails(self):
        problems = _problems(_entry(id="raptorxai-decks"))
        self.assertTrue(
            any("[raptorxai-decks]" in p and "`raptorxai`" in p for p in problems),
            problems,
        )

    def test_vendor_in_id_fails(self):
        problems = _problems(_entry(id="notion-sync", vendor="notion"))
        self.assertTrue(
            any("[notion-sync]" in p and "`notion`" in p for p in problems), problems
        )

    def test_henry_fork_suffix_with_nonnull_vendor_passes(self):
        self.assertEqual(_problems(_entry(id="pptx-henry", vendor="anthropic")), [])

    def test_vendor_matches_on_token_boundary_not_substring(self):
        # vendor `go` must NOT flag `django-helper`
        self.assertEqual(_problems(_entry(id="django-helper", vendor="go")), [])

    def test_null_vendor_never_flags(self):
        self.assertEqual(_problems(_entry(id="null-safe-skill", vendor="null")), [])


class HooksLayout(unittest.TestCase):
    def _tree(self, with_config):
        root = tempfile.mkdtemp()
        hooks = os.path.join(root, "hooks")
        handlers = os.path.join(hooks, "dev-focus", "hooks-handlers")
        os.makedirs(handlers)
        open(
            os.path.join(handlers, "dev-focus.SessionStart.session-start.sh"), "w"
        ).close()
        if with_config:
            cfg_dir = os.path.join(hooks, "dev-focus", "hooks")
            os.makedirs(cfg_dir)
            open(os.path.join(cfg_dir, "hooks.json"), "w").close()
        return hooks

    def test_present_config_is_clean(self):
        problems = []
        N.check_hooks_layout(self._tree(with_config=True), problems)
        self.assertEqual(problems, [])

    def test_missing_hooks_json_fails_naming_the_plugin(self):
        problems = []
        N.check_hooks_layout(self._tree(with_config=False), problems)
        self.assertTrue(
            any("[dev-focus]" in p and "hooks.json" in p for p in problems), problems
        )

    def test_real_tree_is_clean(self):
        problems = []
        N.check_hooks_layout(N.HOOKS_DIR, problems)
        self.assertEqual(problems, [])


class BundleIds(unittest.TestCase):
    def test_real_plugins_yaml_ids_all_kebab(self):
        ids = N.parse_bundle_ids(N.PLUGINS_YAML)
        self.assertTrue(ids)
        for pid in ids:
            problems = []
            N.check_bundle_id(pid, problems)
            self.assertEqual(problems, [], pid)

    def test_non_kebab_bundle_id_fails(self):
        problems = []
        N.check_bundle_id("Not_A_Plugin", problems)
        self.assertTrue(
            any("[Not_A_Plugin]" in p and "<domain>-<function>" in p for p in problems),
            problems,
        )

    def test_client_token_bundle_id_fails(self):
        problems = []
        N.check_bundle_id("headcase-tools", problems)
        self.assertTrue(any("`headcase`" in p for p in problems), problems)


class ProjectWorkflowConformance(unittest.TestCase):
    def test_project_workflow_members_pass_unchanged(self):
        """TC-010: the 9 project-workflow skills + agent all conform."""
        entries = [
            e
            for e in N.parse_roster(N.ROSTER)
            if "project-workflow" in N._list(e.get("plugins", "[]"))
        ]
        self.assertGreaterEqual(len(entries), 10, [e.get("id") for e in entries])
        for e in entries:
            self.assertEqual(_problems(e), [], e.get("id"))


class CleanTree(unittest.TestCase):
    def test_main_returns_zero(self):
        self.assertEqual(N.main(), 0)


if __name__ == "__main__":
    unittest.main()

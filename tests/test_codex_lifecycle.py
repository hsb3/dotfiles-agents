"""Runtime-shape regressions: cumulative billing must not become context occupancy."""
import importlib.util
import json
import io
import os
from pathlib import Path
import sys
import tempfile
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HOOKS = Path(__file__).resolve().parents[1] / 'primitives-core/hooks'
sys.path.insert(0, str(HOOKS / '_lib'))
import codex_lifecycle


def hook(name):
    spec = importlib.util.spec_from_file_location('codex_test_' + name.replace('-', '_'), HOOKS / name / 'hook.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RolloutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'rollout.jsonl'

    def write(self, *items):
        self.path.write_text('\n'.join(json.dumps(item) for item in items))

    def usage(self, tokens, window=258400):
        return {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
            'last_token_usage': {'total_tokens': tokens, 'input_tokens': 20000, 'cached_input_tokens': 19000},
            'total_token_usage': {'total_tokens': 999999}, 'model_context_window': window}}}

    def test_occupancy_uses_latest_request_and_effective_window(self):
        self.write({'type': 'turn_context', 'payload': {'model': 'gpt-5.6-luna'}}, self.usage(23000))
        result = codex_lifecycle.measure(self.path)
        self.assertEqual((result['ctx_tokens'], result['window'], result['model']), (23000, 258400, 'gpt-5.6-luna'))

    def test_compaction_estimate_replaces_prior_usage(self):
        self.write(self.usage(23000), self.usage(4630))
        self.assertEqual(codex_lifecycle.measure(self.path)['ctx_tokens'], 4630)

    def test_missing_measurement_never_reads_as_zero(self):
        for items in ([], [self.usage(20, None)], [self.usage(None)]):
            self.write(*items)
            with self.assertRaises(ValueError):
                codex_lifecycle.measure(self.path)

    def test_both_native_delegation_names_reset_retained_work(self):
        self.write(*[{'type': 'response_item', 'payload': {'type': 'function_call', 'name': name,
                    'arguments': json.dumps(args)}} for name, args in [
            ('exec_command', {'cmd': 'cat a.py'}), ('spawn_agent', {}),
            ('exec_command', {'cmd': 'cat b.py'}), ('collaboration.spawn_agent', {}),
            ('exec_command', {'cmd': 'git status'}), ('exec_command', {'cmd': 'cat c.py'})]])
        with patch.dict(os.environ, ATELIER_HARNESS='codex'):
            self.assertEqual(hook('delegation-watermark')._scan(self.path), (1, 2, 3))

    def test_manager_native_prefix_only_in_codex(self):
        module = hook('manager-package-gate')
        with patch.dict(os.environ, ATELIER_HARNESS='codex'):
            self.assertTrue(module._is_managed('atelier-manager'))
            self.assertFalse(module._is_managed('code-manager'))
        with patch.dict(os.environ, ATELIER_HARNESS='claude-code'):
            self.assertFalse(module._is_managed('atelier-manager'))
            self.assertTrue(module._is_managed('atelier:manager'))


class CompactWireTests(unittest.TestCase):
    def test_native_manual_block_contains_no_rejected_claude_fields(self):
        module = hook('handoff-freshness-guard')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.claude').mkdir()
            (root / '.claude/atelier.local.md').write_text(
                '---\nenforce: advisory\nhandoff:\n  mode: external\n'
                '  stamp: .claude/handoff.stamp\n  location: external board\n---\n')
            payload = {'cwd': directory, 'session_id': 'test', 'hook_event_name': 'PreCompact', 'trigger': 'manual'}
            out = io.StringIO()
            with patch.dict(os.environ, ATELIER_HARNESS='codex', ATELIER_ACTIVATION_FILE=str(root / '.claude/atelier.local.md')), \
                 patch.object(module.codex_lifecycle, 'prepare', side_effect=lambda value: value), \
                 patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))), patch.object(sys, 'stdout', out), \
                 patch.object(module.agentlog, 'make_logger', return_value=lambda value: None):
                with self.assertRaises(SystemExit):
                    module.main()
            result = json.loads(out.getvalue())
            self.assertEqual(set(result), {'continue', 'stopReason', 'systemMessage'})
            self.assertIs(result['continue'], False)


class SnapshotIdentityTests(unittest.TestCase):
    def test_codex_daemon_does_not_match_claude_daemon_for_same_repo(self):
        import re
        module = hook('lane-snapshot')
        with patch.dict(os.environ, ATELIER_HARNESS='codex'):
            native = module._pattern('/tmp/project')
        with patch.dict(os.environ, ATELIER_HARNESS='claude-code'):
            claude = module._pattern('/tmp/project')
        self.assertIsNone(re.search(native, 'snapshot_lanes.py /tmp/project'))
        self.assertIsNone(re.search(claude, 'snapshot_lanes.py --harness codex /tmp/project'))
        self.assertIsNotNone(re.search(native, 'snapshot_lanes.py --harness codex /tmp/project'))


class SetupTests(unittest.TestCase):
    def test_project_setup_is_additive_and_check_is_read_only(self):
        spec = importlib.util.spec_from_file_location('codex_activation_test',
            HOOKS.parent / 'skills/activation/scripts/activation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(sys.modules, codex_roles=SimpleNamespace(setup=lambda *args, **kwargs: [])):
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', directory], check=True)
            (root / '.codex').mkdir()
            config = root / '.codex/config.toml'
            config.write_text('model = "user-choice"\n')
            self.assertEqual(module.codex_setup(directory, io.StringIO(), check=True), 1)
            self.assertEqual(config.read_text(), 'model = "user-choice"\n')
            self.assertEqual(module.codex_setup(directory, io.StringIO()), 0)
            written = config.read_text()
            self.assertIn('model = "user-choice"', written)
            self.assertIn('/refs/heads/atelier', written)
            self.assertNotIn('"' + str(root / '.git/refs') + '"', written)
            self.assertEqual(module.codex_setup(directory, io.StringIO(), check=True), 0)
            self.assertEqual(config.read_text(), written)
            config.write_text('[sandbox_workspace_write]\nwritable_roots = ["/user-owned"]\n')
            self.assertEqual(module.codex_setup(directory, io.StringIO()), 1)
            self.assertEqual(config.read_text(), '[sandbox_workspace_write]\nwritable_roots = ["/user-owned"]\n')

    def test_other_bundle_role_injection_does_not_need_atelier_registry(self):
        module = hook('worker-context')
        roles = SimpleNamespace(package_id=lambda root: 'pocketbase',
            role_names=lambda root: ('pocketbase-pb-builder',),
            role_instructions=lambda role, root: 'CANONICAL_PACKAGE_ROLE')
        out = io.StringIO()
        payload = {'agent_type': 'pocketbase-pb-builder', 'hook_event_name': 'SubagentStart'}
        with patch.dict(os.environ, ATELIER_HARNESS='codex', ATELIER_ROLE_PLUGIN_ROOT='/package'), \
             patch.dict(sys.modules, codex_roles=roles), patch.object(sys, 'stdout', out), \
             patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))):
            module.main()
        self.assertEqual(json.loads(out.getvalue())['hookSpecificOutput']['additionalContext'], 'CANONICAL_PACKAGE_ROLE')


if __name__ == '__main__':
    unittest.main()

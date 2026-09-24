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
            with self.assertRaises(ValueError) as caught:
                codex_lifecycle.measure(self.path)
            self.assertNotIsInstance(caught.exception, codex_lifecycle.PendingMeasurement)

    def test_pending_requires_an_initialized_rollout(self):
        for content in ('', 'not json\n'):
            self.path.write_text(content)
            with self.assertRaises(ValueError) as caught:
                codex_lifecycle.measure(self.path)
            self.assertNotIsInstance(caught.exception, codex_lifecycle.PendingMeasurement)

    def test_null_token_count_info_keeps_the_previous_valid_measurement(self):
        self.write(self.usage(26117),
                   {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': None}})
        self.assertEqual(codex_lifecycle.measure(self.path)['ctx_tokens'], 26117)

    def test_initial_rollout_is_pending_until_the_first_usable_usage(self):
        # Sanitized from the 0.153.4 rollout: UserPromptSubmit precedes the
        # first token_count, so this is initialization rather than corruption.
        self.write(
            {'type': 'session_meta', 'payload': {'timestamp': '2026-09-09T14:25:10.507Z'}},
            {'type': 'turn_context', 'payload': {'model': 'gpt-6-astra'}},
        )
        with self.assertRaises(codex_lifecycle.PendingMeasurement):
            codex_lifecycle.measure(self.path)
        self.write(
            {'type': 'session_meta', 'payload': {'timestamp': '2026-09-09T14:25:10.507Z'}},
            {'type': 'turn_context', 'payload': {'model': 'gpt-6-astra'}},
            self.usage(26117), self.usage(4630),
        )
        result = codex_lifecycle.measure(self.path)
        self.assertEqual((result['ctx_tokens'], result['window'], result['model'], result['started_at']),
                         (4630, 258400, 'gpt-6-astra', '2026-09-09T14:25:10.507Z'))

    def test_context_watermark_records_initial_rollout_as_pending_without_diagnostic(self):
        module = hook('context-watermark')
        self.write({'type': 'session_meta', 'payload': {'timestamp': '2026-09-09T14:25:10.507Z'}})
        rows, output = [], io.StringIO()
        with patch.dict(os.environ, ATELIER_HARNESS='codex'), patch.object(sys, 'stdout', output):
            module.handle_session({'session_id': 'startup', 'cwd': self.tmp.name,
                                   'transcript_path': str(self.path)}, rows.append)
        self.assertEqual(rows, [{'scope': 'session', 'session_id': 'startup', 'ctx_tokens': None,
                                 'tier': 'none', 'fired': False, 'model': None, 'window': None,
                                 'window_fallback': False, 'complexity': None, 'soft': None,
                                 'hard': None, 'pending': True}])
        self.assertEqual(output.getvalue(), '')

    def test_malformed_runtime_usage_still_has_a_diagnostic(self):
        module = hook('context-watermark')
        self.write(self.usage(None))
        rows, output = [], io.StringIO()
        with patch.dict(os.environ, ATELIER_HARNESS='codex'), patch.object(sys, 'stdout', output):
            module.handle_session({'session_id': 'malformed', 'cwd': self.tmp.name,
                                   'transcript_path': str(self.path)}, rows.append)
        self.assertEqual(rows[-1]['ctx_tokens'], None)
        self.assertEqual(rows[-1]['error'], 'no runtime last_token_usage.total_tokens')
        self.assertIn('atelier: could not measure Codex lifecycle', output.getvalue())

    def test_corrupt_rollout_still_has_a_diagnostic(self):
        module = hook('context-watermark')
        self.path.write_text('not json\n')
        rows, output = [], io.StringIO()
        with patch.dict(os.environ, ATELIER_HARNESS='codex'), patch.object(sys, 'stdout', output):
            module.handle_session({'session_id': 'corrupt', 'cwd': self.tmp.name,
                                   'transcript_path': str(self.path)}, rows.append)
        self.assertNotIn('pending', rows[-1])
        self.assertEqual(rows[-1]['error'], 'no runtime last_token_usage.total_tokens')
        self.assertIn('atelier: could not measure Codex lifecycle', output.getvalue())

    def test_native_tool_events_preserve_floor_reset_and_duplicate_rules(self):
        with patch.dict(os.environ, ATELIER_HARNESS='codex', DELEGATION_WATERMARK_STATE_DIR=self.tmp.name):
            module = hook('delegation-watermark')
            calls = [('Bash', 'cat a.py'), ('spawn_agent', ''), ('Bash', 'cat b.py'),
                     ('collaborationspawn_agent', ''), ('Bash', 'git status'), ('Bash', 'cat c.py')]
            for index, (name, command) in enumerate(calls):
                payload = {'session_id': 'native-session', 'tool_use_id': str(index),
                           'tool_name': name, 'tool_input': {'command': command}}
                result = module._codex_counts(payload)
            self.assertEqual(result, (1, 2, 3))
            self.assertEqual(module._codex_counts(payload), result)
            with self.assertRaises(ValueError):
                module._codex_counts({'session_id': 'native-session'})

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


class SetupTests(unittest.TestCase):
    def test_project_setup_is_additive_and_check_is_read_only(self):
        spec = importlib.util.spec_from_file_location('codex_activation_test',
            HOOKS.parent / 'skills/activation/scripts/activation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(sys.modules, codex_roles=SimpleNamespace(setup=lambda *args, **kwargs: []),
                        codex_workers=SimpleNamespace(clean_git_env=lambda: {key: value for key, value in os.environ.items() if not key.startswith("GIT_")})):
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
            self.assertIn('[agents]\nmax_depth = 2', written)
            self.assertIn('/refs/heads/atelier', written)
            self.assertNotIn('"' + str(root / '.git/refs') + '"', written)
            self.assertEqual(module.codex_setup(directory, io.StringIO(), check=True), 0)
            self.assertEqual(config.read_text(), written)
            config.write_text('[sandbox_workspace_write]\nwritable_roots = ["/user-owned"]\n')
            self.assertEqual(module.codex_setup(directory, io.StringIO()), 1)
            self.assertEqual(config.read_text(), '[sandbox_workspace_write]\nwritable_roots = ["/user-owned"]\n')

    def test_manager_settings_are_checked_before_any_project_mutation(self):
        spec = importlib.util.spec_from_file_location('codex_activation_agents_test',
            HOOKS.parent / 'skills/activation/scripts/activation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for settings, valid in [('', False), ('max_depth = 1', False),
                                ('max_depth = 2\nenabled = false', False),
                                ('max_depth = 2\nmax_concurrent_threads_per_session = 1', False),
                                ('max_depth = 4', True)]:
            with self.subTest(settings=settings), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                subprocess.run(['git', 'init', '-q', directory], check=True)
                (root / '.codex').mkdir()
                config = root / '.codex/config.toml'
                original = '[agents]\n' + settings + '\n'
                config.write_text(original)
                calls = []
                roles = SimpleNamespace(setup=lambda *args, **kwargs: calls.append(kwargs['check']) or [])
                worker = SimpleNamespace(clean_git_env=lambda: {key: value for key, value in os.environ.items() if not key.startswith('GIT_')})
                with patch.dict(sys.modules, codex_roles=roles, codex_workers=worker):
                    report = io.StringIO()
                    self.assertEqual(module.codex_setup(directory, report), 0 if valid else 1)
                if valid:
                    self.assertIn('max_depth = 4', config.read_text())
                    self.assertNotIn('max_depth = 2', config.read_text())
                else:
                    self.assertEqual(config.read_text(), original)
                    self.assertEqual(calls, [])
                    self.assertIn('under [agents]', report.getvalue())
                    self.assertFalse((root / '.codex/agents').exists())

    def test_setup_refuses_symlink_files_before_any_write(self):
        spec = importlib.util.spec_from_file_location('codex_activation_symlink_test',
            HOOKS.parent / 'skills/activation/scripts/activation.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for destination in ('.codex/config.toml', '.git/info/exclude'):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                subprocess.run(['git', 'init', '-q', directory], check=True)
                (root / '.codex').mkdir()
                outside = root / 'outside'
                outside.write_text('UNCHANGED')
                target = root / destination
                target.unlink(missing_ok=True)
                target.symlink_to(outside)
                roles = SimpleNamespace(setup=lambda *args, **kwargs: self.fail('preflight must precede role writes'))
                worker = SimpleNamespace(clean_git_env=lambda: {key: value for key, value in os.environ.items() if not key.startswith('GIT_')})
                with patch.dict(sys.modules, codex_roles=roles, codex_workers=worker), \
                     patch.dict(os.environ, GIT_DIR='/unrelated', GIT_WORK_TREE='/unrelated'):
                    self.assertEqual(module.codex_setup(directory, io.StringIO()), 2)
                self.assertEqual(outside.read_text(), 'UNCHANGED')
                self.assertFalse((root / '.codex/agents').exists())
                if destination != '.codex/config.toml':
                    self.assertFalse((root / '.codex/config.toml').exists())

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


class BranchSessionTests(unittest.TestCase):
    def test_shared_server_pid_does_not_collapse_native_sessions(self):
        from datetime import datetime, timezone
        module = hook('branch-activity-surfacer')
        now = datetime.now(timezone.utc)
        row = {'owner_pid': 42, 'session_id': 'other-thread', 'ts': now.isoformat()}
        with patch.dict(os.environ, ATELIER_HARNESS='codex'), patch.object(module, '_pid_alive', return_value=True):
            self.assertEqual(len(module._live_peers([row], 'this-thread', 42, 300, now)), 1)
        with patch.dict(os.environ, ATELIER_HARNESS='claude-code'), patch.object(module, '_pid_alive', return_value=True):
            self.assertEqual(module._live_peers([row], 'this-thread', 42, 300, now), [])


class TelemetryTranscriptTests(unittest.TestCase):
    def test_worker_corrupt_rollout_still_has_a_diagnostic(self):
        module = hook('subagent-telemetry')
        with tempfile.TemporaryDirectory() as directory:
            child = Path(directory) / 'child'
            child.write_text('not json\n')
            record = {'session_id': 'parent', 'agent_id': 'child', 'agent_type': 'atelier-builder',
                      'transcript_path': str(child)}
            workers = SimpleNamespace(lookup=lambda value: record, records=lambda value: [],
                                      set_status=lambda value, status: None)
            rows = []
            with patch.dict(sys.modules, codex_workers=workers), \
                 patch.object(module.agentlog, 'append', side_effect=lambda stream, row, *args: rows.append(row)), \
                 patch.object(sys, 'stdout', io.StringIO()) as output:
                module._codex_stop(dict(record, cwd=directory))
            self.assertNotIn('pending', rows[-1])
            self.assertEqual(rows[-1]['error'], 'no runtime last_token_usage.total_tokens')
            self.assertIn('atelier: could not measure Codex lifecycle', output.getvalue())

    def test_worker_initial_rollout_is_pending_without_diagnostic(self):
        module = hook('subagent-telemetry')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / 'child'
            child.write_text(json.dumps({'type': 'session_meta', 'payload': {'timestamp': '2026-09-09T14:25:10.507Z'}}))
            record = {'session_id': 'parent', 'agent_id': 'child', 'agent_type': 'atelier-builder',
                      'transcript_path': str(child)}
            workers = SimpleNamespace(lookup=lambda value: record, records=lambda value: [],
                                      set_status=lambda value, status: None)
            rows = []
            with patch.dict(sys.modules, codex_workers=workers), \
                 patch.object(module.agentlog, 'append', side_effect=lambda stream, row, *args: rows.append(row)), \
                 patch.object(sys, 'stdout', io.StringIO()) as output:
                module._codex_stop(dict(record, cwd=directory))
            self.assertIsNone(rows[-1]['ctx_tokens'])
            self.assertTrue(rows[-1]['pending'])
            self.assertNotIn('error', rows[-1])
            self.assertEqual(output.getvalue(), '')

    def test_worker_stop_uses_registered_child_not_parent_transcript(self):
        module = hook('subagent-telemetry')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, model, tokens, started in (
                    ('parent', 'gpt-5.6-luna', 99000, '2026-09-08T00:00:00Z'),
                    ('child', 'gpt-5.6-terra', 12000, '2026-09-09T00:00:00Z')):
                (root / name).write_text('\n'.join(json.dumps(value) for value in [
                    {'type': 'session_meta', 'payload': {'timestamp': started}},
                    {'type': 'turn_context', 'payload': {'model': model}},
                    {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {
                        'last_token_usage': {'total_tokens': tokens}, 'model_context_window': 258400}}}]))
            record = {'session_id': 'parent', 'agent_id': 'child', 'agent_type': 'atelier-builder',
                      'transcript_path': str(root / 'child')}
            payload = dict(record, cwd=directory, transcript_path=str(root / 'parent'),
                           agent_transcript_path=str(root / 'child'))
            statuses = []
            workers = SimpleNamespace(lookup=lambda value: record, records=lambda value: [],
                set_status=lambda value, status: statuses.append(status))
            rows = []
            with patch.dict(sys.modules, codex_workers=workers), \
                 patch.object(module.agentlog, 'append', side_effect=lambda stream, row, *args: rows.append(row)):
                module._codex_stop(payload)
                self.assertEqual((rows[-1]['model'], rows[-1]['ctx_tokens'], rows[-1]['started_at']),
                                 ('gpt-5.6-terra', 12000, '2026-09-09T00:00:00Z'))
                self.assertEqual(statuses, ['stopped'])
                (root / 'child').unlink()
                with patch.object(sys, 'stdout', io.StringIO()) as output:
                    module._codex_stop(payload)
                self.assertIsNone(rows[-1]['ctx_tokens'])
                self.assertIsNone(rows[-1]['model'])
                self.assertIn('could not measure', output.getvalue())


if __name__ == '__main__':
    unittest.main()

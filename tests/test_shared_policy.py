"""Configured-agent placement and byte-preserving setup regression contract."""
import io
import itertools
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests.test_codex_activation_paths import activation, atelier_local, FULL, HOOKS, make_worktree


class SharedPolicyTests(unittest.TestCase):
    def test_agent_matrix_and_fixed_legacy_order(self):
        for count in range(4):
            for names in itertools.combinations(('claude', 'codex', 'opencode'), count):
                for harness in ('claude-code', 'codex', 'opencode'):
                    with self.subTest(names=names, harness=harness), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ATELIER_HARNESS=harness, ATELIER_ACTIVATION_FILE=''):
                        root = Path(tmp)
                        for name in names:
                            (root / ('.' + name)).mkdir()
                        expected = '.agents' if count > 1 else '.' + (names[0] if names else {'claude-code': 'claude'}.get(harness, harness))
                        self.assertEqual(Path(atelier_local.activation_path(tmp)).parent.name, expected)
                        if 'opencode' in names:
                            (root / 'opencode.json').write_text('{}')
                            (root / 'opencode.jsonc').write_text('{}')
                            self.assertEqual(len(atelier_local.configured_agents(tmp)), count)
                        for name in ('claude', 'codex', 'opencode'):
                            (root / ('.' + name)).mkdir(exist_ok=True)
                            (root / ('.' + name) / 'atelier.local.md').write_text(name)
                        self.assertEqual(Path(atelier_local.activation_path(tmp)).parent.name, '.claude')
                        (root / '.agents').mkdir()
                        (root / '.agents/atelier.local.md').write_text('malformed')
                        self.assertEqual(Path(atelier_local.activation_path(tmp)).parent.name, '.agents')

    def test_only_real_configuration_markers_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('AGENTS.md', 'CLAUDE.md'):
                (root / name).write_text('')
            (root / '.agents').mkdir()
            (root / 'opencode.json').mkdir()
            self.assertEqual(atelier_local.configured_agents(tmp), ())
            (root / 'native').mkdir()
            (root / '.claude').symlink_to(root / 'native', target_is_directory=True)
            self.assertEqual(atelier_local.configured_agents(tmp), ())
            (root / 'opencode.jsonc').write_text('{}')
            self.assertEqual(atelier_local.configured_agents(tmp), ('opencode',))
            (root / 'opencode.jsonc').unlink()
            (root / 'actual.json').write_text('{}')
            (root / 'opencode.jsonc').symlink_to(root / 'actual.json')
            self.assertEqual(atelier_local.configured_agents(tmp), ())

    def test_migration_bytes_mode_idempotence_and_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ATELIER_ACTIVATION_FILE=''):
            root = Path(tmp)
            (root / '.claude').mkdir()
            (root / '.codex').mkdir()
            old = root / '.claude/atelier.local.md'
            data = b'---\r\nenforce: strict\r\n---\r\n\xff'
            old.write_bytes(data)
            old.chmod(0o600)
            self.assertTrue(activation.reconcile_policy(tmp, atelier_local, check=True))
            self.assertEqual(old.read_bytes(), data)
            previous_umask = os.umask(0o077)
            try:
                old.chmod(0o644)
                self.assertTrue(activation.reconcile_policy(tmp, atelier_local))
            finally:
                os.umask(previous_umask)
            target = root / '.agents/atelier.local.md'
            self.assertEqual(target.read_bytes(), data)
            self.assertEqual(target.stat().st_mode & 0o777, 0o644)
            self.assertEqual(activation.reconcile_policy(tmp, atelier_local), [])
            old.write_bytes(data)
            activation.reconcile_policy(tmp, atelier_local)
            self.assertFalse(old.exists())
            old.write_bytes(b'divergent')
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            for force in (False, True):
                with self.assertRaises(ValueError):
                    activation.cmd_create(tmp, force, io.StringIO())
                self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})

    def test_override_missing_malformed_and_conflicts_are_authoritative(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ATELIER_ACTIVATION_FILE='custom.md'):
            root = Path(tmp)
            for name in ('claude', 'codex'):
                (root / ('.' + name)).mkdir()
                (root / ('.' + name) / 'atelier.local.md').write_text(name)
            self.assertEqual(atelier_local.activation_path(tmp), str(root / 'custom.md'))
            self.assertEqual(activation.cmd_check(tmp, io.StringIO()), 1)
            self.assertEqual(activation.cmd_create(tmp, False, io.StringIO()), 0)
            (root / 'custom.md').write_text('malformed')
            self.assertEqual(activation.cmd_create(tmp, False, io.StringIO()), 0)
            self.assertEqual((root / 'custom.md').read_text(), 'malformed')
            self.assertEqual(activation.cmd_check(tmp, io.StringIO()), 1)

    def test_codex_setup_reconciles_after_creating_native_directory(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
                os.environ, ATELIER_HARNESS='codex', ATELIER_ACTIVATION_FILE='',
                CODEX_HOME=str(Path(tmp) / 'codex-home')):
            root = Path(tmp)
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            (root / '.claude').mkdir()
            old = root / '.claude/atelier.local.md'
            old.write_text(FULL)
            self.assertNotEqual(activation.codex_setup(tmp, io.StringIO(), check=True), 0)
            self.assertFalse((root / '.codex').exists())
            self.assertEqual(activation.codex_setup(tmp, io.StringIO()), 0)
            target = root / '.agents/atelier.local.md'
            self.assertEqual(target.read_bytes(), FULL.encode())
            self.assertEqual(activation.codex_setup(tmp, io.StringIO(), check=True), 0)
            self.assertEqual(atelier_local.activation_path(tmp), str(target))
            self.assertEqual(activation.cmd_check(tmp, io.StringIO()), 0)

    def test_head_selection_ignores_live_directory_and_policy_changes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ATELIER_ACTIVATION_FILE=''):
            _, worker = make_worktree(tmp, tracked={'.codex/atelier.local.md': FULL, 'opencode.json/file': ''})
            root = Path(worker)
            self.assertEqual(atelier_local.committed_activation_candidates(worker)[0], '.codex/atelier.local.md')
            (root / '.codex/atelier.local.md').unlink()
            (root / '.codex').rmdir()
            (root / '.claude').mkdir()
            (root / '.claude/atelier.local.md').write_text('---\nenforce: off\n---\n')
            self.assertEqual(HOOKS['config-custody']._load_policy(str(root / 'Makefile'), worker)[0], 'strict')
            self.assertEqual(atelier_local.committed_activation_candidates(worker)[0], '.codex/atelier.local.md')

    def test_opencode_settings_are_named_without_accepting_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, ATELIER_ACTIVATION_FILE=''):
            root = Path(tmp)
            (root / '.claude').mkdir()
            policy = root / '.claude/atelier.local.md'
            policy.write_text('---\nenforce: strict\nmodels: {}\ncomplexity: simple\nworktreeBaseRef: dev\n---\n')
            out = io.StringIO()
            self.assertEqual(activation.cmd_check(tmp, out), 0, out.getvalue())
            self.assertIn('other harness', out.getvalue())
            policy.write_text('---\nmodles: {}\n---\n')
            self.assertEqual(activation.cmd_check(tmp, io.StringIO()), 1)

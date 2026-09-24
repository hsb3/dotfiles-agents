"""A creator/reader path mismatch must disarm these regression assertions."""
import io
import os
from pathlib import Path
import shutil
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_activation import activation
from test_atelier_local import FULL, HOOKS, atelier_local
from worktree_fixture import make_worktree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'primitives-core/hooks/_lib'))
import codex_roles


class ActivationPathsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.env = patch.dict(os.environ, ATELIER_HARNESS='codex', ATELIER_ACTIVATION_FILE='',
                              CODEX_HOME=str(self.root / 'codex-home'))
        self.env.start()
        self.addCleanup(self.env.stop)

    def write(self, path, text=FULL):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def assert_readers(self, project, expected, mode='strict'):
        for name, hook in HOOKS.items():
            if hasattr(hook, '_resolve_activation_path'):
                with self.subTest(reader=name):
                    self.assertEqual(Path(hook._resolve_activation_path(str(project))), expected)
        self.assertEqual(HOOKS['worker-context']._load_mode(str(project)), mode)
        self.assertEqual(HOOKS['config-custody']._load_activation(str(project))[0], mode)
        self.assertEqual(atelier_local.activation_path(str(project)), str(expected))
        workers = HOOKS['config-custody'].codex_workers
        self.assertEqual(workers._activation_text({'cwd': str(project)}), expected.read_text())

    def test_fresh_codex_create_arms_the_files_read_by_hooks(self):
        (self.root / '.gitignore').write_text('')
        output = io.StringIO()
        self.assertEqual(activation.main(['create', '--harness', 'codex', '--project-dir', str(self.root)], out=output), 0)
        dest = self.root / '.codex/atelier.local.md'
        self.assertTrue(dest.is_file(), output.getvalue())
        self.assertFalse((self.root / '.claude').exists())
        self.assertIn('.codex/*.local.md', (self.root / '.gitignore').read_text())
        self.assertIn('check --harness codex', dest.read_text())
        self.assertNotIn('CLAUDE_PLUGIN_ROOT', dest.read_text())
        self.assert_readers(self.root, dest)
        self.assertEqual(activation.cmd_check(str(self.root), io.StringIO()), 0)

    def test_legacy_and_both_file_precedence_without_migration(self):
        legacy = self.write(self.root / '.claude/atelier.local.md')
        self.assert_readers(self.root, legacy)
        self.assertEqual(activation.main(['create', '--harness', 'codex', '--project-dir', str(self.root)], out=io.StringIO()), 0)
        self.assertFalse((self.root / '.codex').exists())
        native = self.write(self.root / '.codex/atelier.local.md', FULL.replace('strict', 'advisory'))
        self.assert_readers(self.root, legacy)
        with patch.dict(os.environ, ATELIER_HARNESS='claude-code'):
            self.assertEqual(atelier_local.activation_path(str(self.root)), str(legacy))
            self.assertEqual(HOOKS['worker-context']._load_mode(str(self.root)), 'strict')

    def test_selected_malformed_missing_and_explicit_files_never_fall_back(self):
        self.write(self.root / '.claude/atelier.local.md')
        native = self.write(self.root / '.agents/atelier.local.md', 'not frontmatter')
        self.assert_readers(self.root, native, 'off')
        self.assertEqual(activation.cmd_check(str(self.root), io.StringIO()), 1)
        explicit = self.write(self.root / 'policy.md')
        with patch.dict(os.environ, ATELIER_ACTIVATION_FILE='policy.md'):
            self.assert_readers(self.root, explicit)
            explicit.unlink()
            self.assertEqual(atelier_local.activation_path(str(self.root)), str(explicit))
            self.assertEqual(activation.cmd_check(str(self.root), io.StringIO()), 1)
        native.unlink()
        native.symlink_to(self.root / 'missing')
        self.assertEqual(atelier_local.activation_path(str(self.root)), str(native))
        self.assertEqual(activation.cmd_check(str(self.root), io.StringIO()), 1)

    def test_worktree_inherits_selected_policy_and_local_policy_wins(self):
        main, worker = make_worktree(str(self.root), files={'.codex/atelier.local.md': FULL})
        main, worker = Path(main), Path(worker)
        self.assert_readers(worker, main / '.codex/atelier.local.md')
        local = self.write(worker / '.codex/atelier.local.md', FULL.replace('strict', 'advisory'))
        self.assert_readers(worker, local, 'advisory')
        local.write_text('malformed')
        self.assert_readers(worker, local, 'off')

    def test_committed_codex_custody_survives_worker_policy_edits(self):
        main, worker = make_worktree(str(self.root), tracked={
            '.agents/atelier.local.md': FULL,
            '.codex/atelier.local.md': FULL.replace('strict', 'off')})
        worker = Path(worker)
        (worker / '.codex/atelier.local.md').write_text('---\nenforce: off\n---\n')
        custody = HOOKS['config-custody']
        self.assertEqual(custody._load_policy(str(worker / 'Makefile'), str(worker)),
                         ('strict', ['Makefile', '.github/workflows/*']))

    def test_fresh_codex_setup_and_check_do_not_create_claude_activation(self):
        main, _ = make_worktree(str(self.root))
        for command in ['create', 'codex-setup', 'check']:
            output = io.StringIO()
            code = activation.main([command, '--harness', 'codex', '--project-dir', main], out=output)
            self.assertEqual(code, 0, output.getvalue())
        self.assertFalse((Path(main) / '.claude').exists())

    def test_codex_setup_uses_current_global_profiles_without_local_copies(self):
        main, _ = make_worktree(str(self.root))
        home = Path(os.environ['CODEX_HOME'])
        home.mkdir()
        codex_roles.setup(home, global_profiles=True)
        output = io.StringIO()
        self.assertEqual(
            activation.main(['codex-setup', '--harness', 'codex', '--project-dir', main], out=output),
            0, output.getvalue())
        self.assertFalse((Path(main) / '.codex/agents').exists())

    def test_codex_setup_rejects_partial_global_collision_before_config_write(self):
        main, _ = make_worktree(str(self.root))
        home = Path(os.environ['CODEX_HOME'])
        home.mkdir()
        codex_roles.setup(home, global_profiles=True)
        (home / 'agents/atelier-scout.toml').unlink()
        (home / 'agents/custom.toml').write_text('name = "atelier-builder"\n')
        output = io.StringIO()
        self.assertNotEqual(
            activation.main(['codex-setup', '--harness', 'codex', '--project-dir', main], out=output), 0)
        self.assertFalse((Path(main) / '.codex/config.toml').exists())

    def setup_roots(self, value=None):
        main, _ = make_worktree(str(self.root))
        self.write(Path(main) / '.codex/atelier.local.md',
                   FULL.replace('---\n', '---\ncheckout-root: ' + value + '\n', 1) if value else FULL)
        config = Path(main) / '.codex/config.toml'
        config.write_text('model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n')
        output = io.StringIO()
        code = activation.main(['codex-setup', '--harness', 'codex', '--project-dir', main], out=output)
        text = config.read_text()
        roots = __import__('tomllib').loads(text).get('sandbox_workspace_write', {}).get('writable_roots')
        return Path(main), code, output.getvalue(), text, roots

    def test_codex_setup_writable_root_defaults_to_the_common_dir(self):
        main, code, output, text, roots = self.setup_roots()
        self.assertEqual(code, 0, output)
        common = main / '.git'
        self.assertEqual(roots, [str(common / p) for p in (
            'atelier-codex/checkouts', 'worktrees', 'objects', 'refs/heads/atelier', 'logs/refs/heads/atelier')])
        self.assertIn('model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n', text)

    def test_codex_setup_writable_root_follows_checkout_root(self):
        main, code, output, text, roots = self.setup_roots('.worktrees')
        self.assertEqual(code, 0, output)
        common = main / '.git'
        self.assertEqual(roots, [str(main / '.worktrees')] + [str(common / p) for p in (
            'worktrees', 'objects', 'refs/heads/atelier', 'logs/refs/heads/atelier')])
        self.assertIn('model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n', text)

    def test_codex_setup_refuses_an_invalid_checkout_root(self):
        (self.root / 'main').mkdir()
        (self.root / 'main/afile').write_text('x')
        main, code, output, text, roots = self.setup_roots('afile')
        self.assertNotEqual(code, 0)
        self.assertIn('checkout-root', output)
        self.assertIsNone(roots)
        self.assertEqual(text, 'model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n')

    def test_codex_setup_refuses_an_unsafe_checkout_root(self):
        for value in ('/', '..', '.git/worktrees'):
            with self.subTest(value=value):
                shutil.rmtree(self.root / 'main', ignore_errors=True)
                shutil.rmtree(self.root / 'worktree', ignore_errors=True)
                main, code, output, text, roots = self.setup_roots(value)
                self.assertNotEqual(code, 0)
                self.assertIn('checkout-root', output)
                self.assertIsNone(roots)
                self.assertEqual(text, 'model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n')
                self.assertFalse(list((main / '.codex').glob('agents/*')))

    def test_codex_setup_refuses_a_tracked_directory_as_checkout_root(self):
        main, _ = make_worktree(str(self.root), tracked={'src/a.py': 'x'})
        main = Path(main)
        self.write(main / '.codex/atelier.local.md',
                   FULL.replace('---\n', '---\ncheckout-root: src\n', 1))
        config = main / '.codex/config.toml'
        config.write_text('model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n')
        output = io.StringIO()
        code = activation.main(['codex-setup', '--harness', 'codex', '--project-dir', str(main)],
                               out=output)
        self.assertNotEqual(code, 0, output.getvalue())
        self.assertIn('checkout-root', output.getvalue())
        self.assertIn('tracked files', output.getvalue())
        self.assertEqual(config.read_text(), 'model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n')
        self.assertFalse(list((main / '.codex').glob('agents/*')))

    def test_codex_setup_rewrites_a_managed_root_containing_a_bracket(self):
        main, _ = make_worktree(str(self.root))
        main = Path(main)
        elsewhere = main / 'odd]dir'
        code, output, _, roots = self.rerun_with_checkout_root(main, str(elsewhere))
        self.assertEqual(code, 0, output)
        self.assertEqual(roots[0], str(elsewhere))
        code, output, text, roots = self.rerun_with_checkout_root(main, '.worktrees')
        self.assertEqual(code, 0, output)
        self.assertEqual(roots[0], str(main / '.worktrees'))
        self.assertEqual(text.count('# atelier managed writable roots'), 1)

    def rerun_with_checkout_root(self, main, value='.worktrees'):
        self.write(main / '.codex/atelier.local.md', FULL.replace('---\n', '---\ncheckout-root: ' + value + '\n', 1))
        output = io.StringIO()
        code = activation.main(['codex-setup', '--harness', 'codex', '--project-dir', str(main)], out=output)
        text = (main / '.codex/config.toml').read_text()
        roots = __import__('tomllib').loads(text).get('sandbox_workspace_write', {}).get('writable_roots')
        return code, output.getvalue(), text, roots

    def test_codex_setup_rewrites_its_own_roots_when_checkout_root_is_enabled(self):
        main, code, output, _, _ = self.setup_roots()
        self.assertEqual(code, 0, output)
        config = main / '.codex/config.toml'
        config.write_text(config.read_text() + '\n[profiles.later]\nmodel = "later"\n')
        code, output, text, roots = self.rerun_with_checkout_root(main)
        self.assertEqual(code, 0, output)
        common = main / '.git'
        self.assertEqual(roots, [str(main / '.worktrees')] + [str(common / p) for p in (
            'worktrees', 'objects', 'refs/heads/atelier', 'logs/refs/heads/atelier')])
        self.assertNotIn(str(common / 'atelier-codex/checkouts'), roots)
        self.assertEqual(text.count('# atelier managed writable roots'), 1)
        self.assertIn('model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n', text)
        self.assertIn('[profiles.later]\nmodel = "later"\n', text)

    def test_codex_setup_still_refuses_a_user_owned_table(self):
        main, _ = make_worktree(str(self.root))
        main = Path(main)
        config = main / '.codex/config.toml'
        user = 'model = "keep-me"\n\n[sandbox_workspace_write]\nwritable_roots = ["/elsewhere"]\n'
        self.write(config, user)
        code, output, text, _ = self.rerun_with_checkout_root(main)
        self.assertNotEqual(code, 0)
        self.assertIn('user-owned', output)
        self.assertEqual(text, user)

    def test_codex_setup_excludes_an_in_tree_checkout_root(self):
        import subprocess
        main, code, output, _, _ = self.setup_roots('.worktrees')
        self.assertEqual(code, 0, output)
        activation.main(['codex-setup', '--harness', 'codex', '--project-dir', str(main)], out=io.StringIO())
        exclude = (main / '.git/info/exclude').read_text().splitlines()
        self.assertEqual(exclude.count('/.worktrees/'), 1)
        subprocess.run(['git', '-C', str(main), 'worktree', 'add', '-q', '-b', 'w',
                        str(main / '.worktrees/s/w')], check=True, capture_output=True)
        status = subprocess.run(['git', '-C', str(main), '-c', 'core.excludesFile=/dev/null',
                                 'status', '--porcelain'], check=True, capture_output=True, text=True).stdout
        self.assertNotIn('.worktrees', status)

    def test_codex_setup_refuses_a_root_outside_the_project(self):
        home = self.root / 'home/me'
        home.mkdir(parents=True)
        for value in ('/etc', '~/..', '$HOME'):
            with self.subTest(value=value), patch.dict(os.environ, HOME=str(home)):
                shutil.rmtree(self.root / 'main', ignore_errors=True)
                shutil.rmtree(self.root / 'worktree', ignore_errors=True)
                main, code, output, text, roots = self.setup_roots(value)
                self.assertNotEqual(code, 0)
                self.assertIn('checkout-root', output)
                self.assertIsNone(roots)
                self.assertEqual(text, 'model = "keep-me"\n\n[profiles.mine]\nmodel = "mine"\n')

    def separate_git_dir(self, value=None):
        import subprocess
        main = self.root / 'sep'
        subprocess.run(['git', 'init', '-q', '--separate-git-dir', str(self.root / 'store.git'), str(main)],
                       check=True, capture_output=True)
        self.write(main / '.codex/atelier.local.md',
                   FULL.replace('---\n', '---\ncheckout-root: ' + value + '\n', 1) if value else FULL)
        output = io.StringIO()
        code = activation.main(['codex-setup', '--harness', 'codex', '--project-dir', str(main)], out=output)
        return main, code, output.getvalue()

    def test_codex_setup_refuses_checkout_root_on_a_separate_git_dir(self):
        main, code, output = self.separate_git_dir('.worktrees')
        self.assertNotEqual(code, 0, output)
        self.assertIn('unsupported git layout', output)
        self.assertFalse((main / '.codex/config.toml').exists())
        self.assertFalse(list((main / '.codex').glob('agents/*')))
        self.assertFalse((self.root / 'store.git/info/exclude').read_text().count('/.codex/'))

    def test_codex_setup_separate_git_dir_without_the_key_keeps_the_default(self):
        main, code, output = self.separate_git_dir()
        self.assertEqual(code, 0, output)
        roots = __import__('tomllib').loads((main / '.codex/config.toml').read_text())[
            'sandbox_workspace_write']['writable_roots']
        self.assertEqual(roots[0], str(self.root / 'store.git/atelier-codex/checkouts'))

    def test_codex_setup_rewrites_a_multi_line_managed_block(self):
        main, code, output, _, _ = self.setup_roots()
        self.assertEqual(code, 0, output)
        config = main / '.codex/config.toml'
        text = config.read_text()
        old = __import__('tomllib').loads(text)['sandbox_workspace_write']['writable_roots']
        # The shape a TOML formatter leaves the managed block in.
        multi = 'writable_roots = [\n' + ''.join('  "' + r + '",\n' for r in old) + ']\n'
        text = text.replace('writable_roots = ' + __import__('json').dumps(old) + '\n', multi)
        self.assertIn(multi, text)
        config.write_text(text + '\n[profiles.later]\nmodel = "later"\n')
        code, output, text, roots = self.rerun_with_checkout_root(main)
        self.assertEqual(code, 0, output)
        common = main / '.git'
        self.assertEqual(roots, [str(main / '.worktrees')] + [str(common / p) for p in (
            'worktrees', 'objects', 'refs/heads/atelier', 'logs/refs/heads/atelier')])
        self.assertEqual(text.count('# atelier managed writable roots'), 1)
        self.assertIn('[profiles.later]\nmodel = "later"\n', text)
        self.assertIn('model = "keep-me"\n', text)

    def test_codex_setup_refuses_to_write_a_config_that_does_not_come_out_right(self):
        # The managed marker inside a multi-line string: a naive rewrite edits the string,
        # leaving the real table without the roots. Setup must refuse, not write.
        # A comment swallowing the string's closing quotes makes the rewrite unparsable.
        head = 'note = """\n# atelier managed writable roots\n[sandbox_workspace_write]\n'
        cases = {'wrong value': head + 'writable_roots = []\n"""\n\n[sandbox_workspace_write]\nnetwork_access = true\n',
                 'parse failure': head + 'writable_roots = [] # """\n'}
        for name, pathological in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.root / 'main', ignore_errors=True)
                shutil.rmtree(self.root / 'worktree', ignore_errors=True)
                main, _ = make_worktree(str(self.root))
                main = Path(main)
                config = main / '.codex/config.toml'
                self.write(config, pathological)
                __import__('tomllib').loads(pathological)
                code, output, text, _ = self.rerun_with_checkout_root(main)
                self.assertNotEqual(code, 0, output)
                self.assertIn('refusing to write ' + str(config), output)
                self.assertEqual(text, pathological)
                self.assertFalse(list((main / '.codex').glob('agents/*')))

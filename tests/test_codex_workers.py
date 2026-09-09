"""Real disposable Git trees exercise Codex routing and ownership failures."""

import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'primitives-core/hooks/_lib'))


class CodexWorkersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.env = {'PATH': os.environ['PATH'], 'HOME': self.tmp.name,
                    'ATELIER_HARNESS': 'codex', 'XDG_DATA_HOME': self.tmp.name}
        self.environment = patch.dict(os.environ, self.env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git('init', '-b', 'dev')
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@invalid',
                 'commit', '--allow-empty', '-m', 'Baseline')
        self.mod = importlib.import_module('codex_workers')
        self.activation()

    def git(self, *args, cwd=None):
        return subprocess.check_output(['git', '-C', str(cwd or self.repo), *args],
                                       stderr=subprocess.PIPE, text=True).strip()

    def payload(self, agent='worker-a', tool='Bash', command='pwd'):
        transcript = Path(self.tmp.name) / (agent + '.jsonl')
        transcript.write_text(json.dumps({'type': 'session_meta', 'payload': {
            'id': agent, 'parent_thread_id': 'session-a', 'agent_path': '/root/' + agent}}) + '\n')
        return dict(session_id='session-a', agent_id=agent, agent_type='atelier-builder',
                    cwd=str(self.repo), tool_name=tool, tool_input={'command': command},
                    transcript_path=str(transcript))

    def test_two_real_worktrees_stage_independently(self):
        indexes = []
        for agent, contents in [('worker-a', 'ALPHA'), ('worker-b', 'BETA')]:
            p = self.payload(agent, command='pwd; printf '+contents+' > shared.txt; git add shared.txt')
            record = self.mod.register(p, isolate=True)
            command = self.mod.route_tool(p)['command']
            output = subprocess.check_output(command, cwd=self.repo, shell=True, text=True)
            self.assertEqual(output.strip(), record['worktree'])
            self.assertEqual(self.git('show', ':shared.txt', cwd=record['worktree']), contents)
            indexes.append(self.git('rev-parse', '--git-path', 'index', cwd=record['worktree']))
            self.assertEqual(self.mod.register(p, isolate=True), record)
        self.assertNotEqual(*indexes)
        self.assertFalse((self.repo / 'shared.txt').exists())
        self.assertEqual(self.git('status', '--porcelain'), '?? .claude/')

    def test_patch_all_headers_and_idempotence(self):
        p = self.payload(tool='apply_patch', command='*** Begin Patch\n*** Add File: a\n+x\n*** Update File: b\n*** Move to: c\n@@\n-x\n+y\n*** Delete File: d\n*** End Patch')
        record = self.mod.register(p, isolate=True)
        paths = self.mod.patch_paths(p)
        self.assertEqual(paths, [str(Path(record['worktree']) / x) for x in 'abcd'])
        routed = self.mod.route_tool(p)
        p['tool_input'] = routed
        self.assertEqual(self.mod.route_tool(p), routed)

    def test_parent_absolute_maps_owned_absolute_remains(self):
        p = self.payload(tool='apply_patch')
        r = self.mod.register(p, isolate=True)
        for name in [str(self.repo / 'x'), str(Path(r['worktree']) / 'x')]:
            p['tool_input']['command'] = '*** Begin Patch\n*** Add File: '+name+'\n+x\n*** End Patch'
            self.assertEqual(self.mod.patch_paths(p), [str(Path(r['worktree']) / 'x')])

    def test_escape_symlink_other_worker_and_unknown_tool_deny(self):
        p = self.payload(tool='apply_patch')
        r = self.mod.register(p, isolate=True)
        other = self.mod.register(self.payload('worker-b'), isolate=True)
        (Path(r['worktree']) / 'escape').symlink_to(self.repo, target_is_directory=True)
        for path in ['../x', 'escape/x', str(Path(r['worktree']) / 'escape/x'),
                     str(Path(other['worktree']) / 'x')]:
            p['tool_input']['command'] = '*** Begin Patch\n*** Add File: '+path+'\n+x\n*** End Patch'
            with self.subTest(path=path), self.assertRaises(self.mod.WorkerError):
                self.mod.route_tool(p)
        p['tool_name'] = 'unknown_file_writer'
        with self.assertRaises(self.mod.WorkerError):
            self.mod.route_tool(p)

    def test_missing_mapping_denies_and_git_env_cleared(self):
        p = self.payload(command='pwd; git rev-parse --show-toplevel')
        with self.assertRaises(self.mod.WorkerError):
            self.mod.route_tool(p)
        r = self.mod.register(p, isolate=True)
        os.environ['GIT_WORK_TREE'] = str(self.repo)
        os.environ['GIT_INDEX_FILE'] = str(self.repo / 'wrong-index')
        command = self.mod.route_tool(p)['command']
        output = subprocess.check_output(command, cwd=self.repo, shell=True, text=True)
        self.assertEqual(output.splitlines(), [r['worktree'], r['worktree']])

    def test_role_control_boundary_native_and_collaboration(self):
        for role in ['atelier-builder', 'atelier-scout', 'atelier-reviewer', 'atelier-code-reviewer']:
            p = self.payload(agent=role); p['agent_type'] = role
            self.mod.register(p, isolate=False)
            for tool in ['spawn_agent', 'multi_agent_v1send_input', 'collaborationspawn_agent', 'collaborationfollowup_task']:
                p['tool_name'] = tool
                with self.subTest(role=role, tool=tool), self.assertRaises(self.mod.WorkerError):
                    self.mod.route_tool(p)
            if role != 'atelier-builder':
                p['tool_name'] = 'apply_patch'
                with self.assertRaises(self.mod.WorkerError):
                    self.mod.route_tool(p)
        p = self.payload('manager', tool='collaborationspawn_agent'); p['agent_type'] = 'atelier-manager'
        self.mod.register(p, isolate=True)
        self.assertEqual(self.mod.route_tool(p), p['tool_input'])

    def test_lifecycle_status_and_session_scope(self):
        p = self.payload()
        self.mod.register(p)
        self.assertEqual(len(self.mod.records(p)), 1)
        self.mod.set_status(p, 'stopped')
        self.assertEqual(self.mod.lookup(p)['status'], 'stopped')
        p['session_id'] = 'other-session'
        self.assertIsNone(self.mod.lookup(p))
        self.assertEqual(self.mod.records(p), [])

    def hook(self, name, payload):
        run = subprocess.run([sys.executable, str(ROOT / 'primitives-core/hooks' / name / 'hook.py')],
                             input=json.dumps(payload), text=True, capture_output=True,
                             env=dict(os.environ), check=True)
        return json.loads(run.stdout) if run.stdout.strip() else {}

    def activation(self, mode='strict'):
        folder = self.repo / '.claude'; folder.mkdir(exist_ok=True)
        (folder / 'atelier.local.md').write_text('---\nenforce: '+mode+'\nisolate: writers\nprotected:\n  - config.toml\nprotected-branches:\n  - dev\n---\n')

    def decision(self, output):
        return output.get('hookSpecificOutput', {}).get('permissionDecision')

    def test_subagent_start_and_unregistered_tool_failure(self):
        self.activation()
        p = self.payload(); p['hook_event_name'] = 'PreToolUse'
        self.assertEqual(self.decision(self.hook('worktree-isolation', p)), 'deny')
        p['hook_event_name'] = 'SubagentStart'
        self.hook('worktree-isolation', p)
        self.assertTrue(self.mod.lookup(p)['worktree'])
        p['hook_event_name'] = 'PreToolUse'
        output = self.hook('worktree-isolation', p)['hookSpecificOutput']
        self.assertEqual(output['permissionDecision'], 'allow')
        routed = output['updatedInput']['command']
        self.assertIn(self.mod.lookup(p)['worktree'], routed)

    def test_custody_all_patch_paths_and_modes(self):
        self.activation()
        p = self.payload(tool='apply_patch')
        self.mod.register(p, isolate=True)
        for header in ['*** Add File: config.toml', '*** Delete File: config.toml',
                       '*** Update File: config.toml', '*** Update File: safe\n*** Move to: config.toml']:
            p['tool_input']['command'] = '*** Begin Patch\n*** Add File: safe-first\n+x\n'+header+'\n*** End Patch'
            self.assertEqual(self.decision(self.hook('config-custody', p)), 'deny')
        self.activation('advisory')
        result = self.hook('config-custody', p)
        self.assertIsNone(self.decision(result))
        self.assertIn('additionalContext', result['hookSpecificOutput'])
        self.activation('off')
        self.assertEqual(self.hook('config-custody', p), {})
        p['tool_input']['command'] = '*** Begin Patch\n*** Add File: okay.py\n+x\n*** End Patch'
        self.activation()
        self.assertEqual(self.hook('config-custody', p), {})

    def test_git_guard_uses_owned_branch(self):
        self.activation()
        p = self.payload(command='git commit -m test')
        self.mod.register(p, isolate=True)
        self.assertEqual(self.hook('worker-git-scope-guard', p), {})

    def test_git_guard_refuses_other_worker_checkout(self):
        p = self.payload(command='git add shared.txt')
        self.mod.register(p, isolate=True)
        other = self.mod.register(self.payload('worker-b'), isolate=True)
        p['tool_input']['command'] = 'git -C '+shlex.quote(other['worktree'])+' add shared.txt'
        self.assertEqual(self.decision(self.hook('worker-git-scope-guard', p)), 'deny')
        p['tool_input']['command'] = 'git -C '+shlex.quote(str(self.repo))+' commit -m test'
        self.assertEqual(self.decision(self.hook('worker-git-scope-guard', p)), 'deny')
        p['tool_input']['command'] = 'git status'
        self.assertEqual(self.hook('worker-git-scope-guard', p), {})

    def test_live_guard_tracks_unisolated_and_stopped_workers(self):
        p = self.payload(); self.mod.register(p)
        parent = dict(p); parent.pop('agent_id'); parent.pop('agent_type')
        parent['tool_input'] = {'command': 'git commit -m test'}
        self.assertEqual(self.decision(self.hook('live-worker-git-guard', parent)), 'deny')
        self.mod.set_status(p, 'stopped')
        self.assertEqual(self.hook('live-worker-git-guard', parent), {})

    def test_comment_gate_scans_worker_index(self):
        p = self.payload(command='git commit -m test')
        r = self.mod.register(p, isolate=True)
        tree = Path(r['worktree'])
        (tree / 'example.py').write_text('# Fixed in PR #123\nanswer = 42\n')
        self.git('add', 'example.py', cwd=tree)
        result = self.hook('comment-hygiene-gate', p)
        self.assertIn('additionalContext', result['hookSpecificOutput'])
        self.assertIsNone(self.decision(result))

    def test_unarmed_non_git_is_inert_and_missing_cwd_denies(self):
        p = self.payload(); p['cwd'] = self.tmp.name; p['hook_event_name'] = 'SubagentStart'
        self.assertEqual(self.hook('worktree-isolation', p), {})
        p['hook_event_name'] = 'PreToolUse'
        for name in ['worktree-isolation', 'config-custody', 'worker-git-scope-guard', 'live-worker-git-guard']:
            self.assertEqual(self.hook(name, p), {})
        p['cwd'] = ''
        self.assertEqual(self.decision(self.hook('worktree-isolation', p)), 'deny')

    def test_nested_worker_bases_on_immediate_parent_head(self):
        parent = self.payload('manager'); parent['agent_type'] = 'atelier-manager'
        r = self.mod.register(parent, isolate=True)
        tree = Path(r['worktree']); (tree / 'manager.txt').write_text('parent commit')
        self.git('add', 'manager.txt', cwd=tree)
        self.git('-c', 'user.name=Test', '-c', 'user.email=test@invalid', 'commit', '-m', 'Manager baseline', cwd=tree)
        child = self.payload('leaf')
        Path(child['transcript_path']).write_text(json.dumps({'type': 'session_meta', 'payload': {
            'id': 'leaf', 'parent_thread_id': 'manager', 'agent_path': '/root/manager/leaf'}})+'\n')
        leaf = self.mod.register(child, isolate=True)
        self.assertEqual(leaf['source'], r['worktree'])
        self.assertEqual((Path(leaf['worktree'])/'manager.txt').read_text(), 'parent commit')
        self.assertFalse((self.repo/'manager.txt').exists())

    def test_missing_and_mismatched_ancestry_denies_registration(self):
        p = self.payload()
        Path(p['transcript_path']).write_text('{}\n')
        with self.assertRaises(self.mod.WorkerError):
            self.mod.register(p, isolate=True)
        p = self.payload(); p['agent_id'] = 'other-worker'
        with self.assertRaises(self.mod.WorkerError):
            self.mod.register(p, isolate=True)

    def test_removed_policy_cannot_disable_corrupt_worker_boundary(self):
        p = self.payload(); p['hook_event_name'] = 'PreToolUse'
        self.mod.register(p, isolate=True)
        (self.repo / '.claude/atelier.local.md').unlink()
        record_path = self.repo / '.git/atelier-codex/workers/session-a/worker-a.json'
        record_path.write_text('not json')
        self.assertEqual(self.decision(self.hook('worktree-isolation', p)), 'deny')

    def test_removed_policy_cannot_disable_missing_checkout_boundary(self):
        p = self.payload(); p['hook_event_name'] = 'PreToolUse'
        r = self.mod.register(p, isolate=True)
        (self.repo / '.claude/atelier.local.md').unlink()
        shutil.rmtree(r['worktree'])
        self.assertEqual(self.decision(self.hook('worktree-isolation', p)), 'deny')

    def test_arming_isolation_denies_existing_unisolated_writer_without_migration(self):
        p = self.payload(); p['hook_event_name'] = 'PreToolUse'
        policy = self.repo / '.claude/atelier.local.md'
        policy.write_text('---\nenforce: strict\nisolate: []\n---\n')
        self.mod.ensure_worker(p)
        before = self.mod.lookup(p)
        for selection in ('writers', '[atelier-builder]'):
            policy.write_text('---\nenforce: strict\nisolate: '+selection+'\n---\n')
            p['agent_type'] = 'atelier-scout'  # runtime tool metadata cannot replace registered authority
            for tool, command in [('Bash', 'pwd'), ('apply_patch',
                    '*** Begin Patch\n*** Add File: x\n+x\n*** End Patch')]:
                p.update(tool_name=tool, tool_input={'command': command})
                with self.subTest(selection=selection, tool=tool):
                    output = self.hook('worktree-isolation', p)
                    self.assertEqual(self.decision(output), 'deny')
                    self.assertIn('redispatch', output['hookSpecificOutput']['permissionDecisionReason'])
            self.assertEqual(self.mod.lookup(p), before)
        self.assertFalse((self.repo / '.git/atelier-codex/checkouts').exists())

    def test_replacement_repository_at_owned_path_denies(self):
        p = self.payload(); p['hook_event_name'] = 'PreToolUse'
        record = self.mod.register(p, isolate=True)
        tree = Path(record['worktree'])
        shutil.rmtree(tree)
        tree.mkdir()
        self.git('init', '-b', 'unrelated', cwd=tree)
        self.assertEqual(self.decision(self.hook('worktree-isolation', p)), 'deny')

    def test_missing_recorded_git_identity_denies_without_backfill(self):
        p = self.payload(); p['hook_event_name'] = 'PreToolUse'
        record = self.mod.register(p, isolate=True)
        del record['git_index']
        path = self.repo / '.git/atelier-codex/workers/session-a/worker-a.json'
        path.write_text(json.dumps(record))
        before = path.read_bytes()
        self.assertEqual(self.decision(self.hook('worktree-isolation', p)), 'deny')
        self.assertEqual(path.read_bytes(), before)

    def test_redirected_worker_admin_or_index_denies(self):
        for redirect in ('admin', 'index'):
            with self.subTest(redirect=redirect):
                p = self.payload('worker-'+redirect); p['hook_event_name'] = 'PreToolUse'
                record = self.mod.register(p, isolate=True)
                other = self.mod.register(self.payload('other-'+redirect), isolate=True)
                tree, sibling = Path(record['worktree']), Path(other['worktree'])
                if redirect == 'admin':
                    (tree / '.git').write_bytes((sibling / '.git').read_bytes())
                else:
                    index = Path(self.git('rev-parse', '--git-path', 'index', cwd=tree))
                    other_index = Path(self.git('rev-parse', '--git-path', 'index', cwd=sibling))
                    index.unlink(missing_ok=True)
                    index.symlink_to(other_index)
                self.assertEqual(self.decision(self.hook('worktree-isolation', p)), 'deny')

    def test_routed_followup_revives_stopped_worker(self):
        p = self.payload()
        self.mod.register(p, isolate=True)
        self.mod.set_status(p, 'stopped')
        self.mod.route_tool(p)
        self.assertEqual(self.mod.lookup(p)['status'], 'running')


if __name__ == '__main__':
    unittest.main()

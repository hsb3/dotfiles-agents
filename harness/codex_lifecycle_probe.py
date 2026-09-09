#!/usr/bin/env python3
"""Opt-in trusted Codex lifecycle proof against actual installed hook scripts.

Requires authenticated Codex; keeps credentials only in a disposable private home.
No production configuration or trust is changed. Run outside CI.
"""
import argparse
import json
import os
from pathlib import Path
import queue
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time


def hook(root, package):
    payload = json.load(sys.stdin)
    names = {'SessionStart': 'session-handoff-surfacer', 'PreCompact': 'handoff-freshness-guard',
             'SubagentStop': 'manager-package-gate'}
    output = {}
    name = names.get(payload['hook_event_name'])
    if name:
        result = subprocess.run([sys.executable, str(package / 'hooks' / name / 'hook.py')],
                                input=json.dumps(payload), capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise RuntimeError(result.stderr)
        if result.stdout.strip():
            output = json.loads(result.stdout)
    with (root / 'hooks.jsonl').open('a') as stream:
        stream.write(json.dumps({'input': payload, 'output': output}) + '\n')
    print(json.dumps(output))


class Server:
    def __init__(self, root, env):
        self.root = root
        self.stderr = (root / 'server.stderr').open('a')
        self.process = subprocess.Popen(['codex', 'app-server', '--stdio'], env=env, cwd=root / 'repo',
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True)
        self.queue = queue.Queue()
        self.serial = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.call('initialize', {'clientInfo': {'name': 'atelier-lifecycle-probe', 'version': '0.0.1'},
                                 'capabilities': {'experimentalApi': True}})
        self.send({'method': 'initialized'})

    def _read(self):
        with (self.root / 'events.jsonl').open('a') as stream:
            for line in self.process.stdout:
                stream.write(line)
                stream.flush()
                self.queue.put(json.loads(line))

    def send(self, value):
        self.process.stdin.write(json.dumps(value) + '\n')
        self.process.stdin.flush()

    def until(self, predicate):
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            value = self.queue.get(timeout=max(.1, deadline - time.monotonic()))
            if predicate(value):
                return value
        raise TimeoutError('Codex did not finish within 120 seconds')

    def call(self, method, params):
        self.serial += 1
        serial = self.serial
        self.send({'id': serial, 'method': method, 'params': params})
        value = self.until(lambda value: value.get('id') == serial)
        if 'error' in value:
            raise RuntimeError(value['error'])
        return value['result']

    def close(self):
        self.process.terminate()
        self.process.wait(timeout=10)
        self.reader.join(timeout=5)
        self.stderr.close()


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='atelier-lifecycle-') as directory:
        root = Path(directory).resolve()
        home, repo = root / 'home', root / 'repo'
        home.mkdir(mode=0o700)
        (repo / '.claude').mkdir(parents=True)
        shutil.copyfile(args.auth_source, home / 'auth.json')
        (home / 'auth.json').chmod(0o600)
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env.update(CODEX_HOME=str(home), ATELIER_HARNESS='codex',
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
        subprocess.run(['git', 'init', '-b', 'probe-parent', str(repo)], check=True, capture_output=True)
        (repo / '.claude/atelier.local.md').write_text('---\nenforce: advisory\nhandoff:\n  mode: external\n'
            '  stamp: .claude/handoff.stamp\n  location: kata card COLD_EXTERNAL_TOKEN\n---\n')
        config = home / 'config.toml'
        config.write_text('model="gpt-5.6-luna"\nmodel_reasoning_effort="low"\napproval_policy="never"\n')
        command = shlex.join([sys.executable, str(Path(__file__).resolve()), '--hook', str(root),
                              '--package-root', str(args.package_root)])
        (home / 'hooks.json').write_text(json.dumps({'hooks': {event: [{'hooks': [
            {'type': 'command', 'command': command, 'timeout': 10}]}]
            for event in ('SessionStart', 'PreCompact', 'PostCompact', 'SubagentStop')}}))
        server = None
        try:
            server = Server(root, env)
            listed = server.call('hooks/list', {'cwds': [str(repo)]})
            server.close()
            server = None
            # Approve only the reviewed commands in this disposable home.
            with config.open('a') as stream:
                for handler in listed['data'][0]['hooks']:
                    stream.write('\n[hooks.state.' + json.dumps(handler['key']) + ']\ntrusted_hash='
                                 + json.dumps(handler['currentHash']) + '\n')
            server = Server(root, env)
            trusted = server.call('hooks/list', {'cwds': [str(repo)]})
            checks = {'trusted': all(handler['trustStatus'] == 'trusted'
                                     for handler in trusted['data'][0]['hooks'])}
            thread = server.call('thread/start', {'cwd': str(repo), 'model': 'gpt-5.6-luna',
                'sandbox': 'read-only', 'approvalPolicy': 'never'})['thread']['id']
            server.call('turn/start', {'threadId': thread, 'input': [{'type': 'text',
                'text': 'Return the handoff location token from session context. Do not use tools.'}]})
            server.until(lambda value: value.get('method') == 'turn/completed')
            for case in ('missing', 'stale', 'fresh'):
                stamp = repo / '.claude/handoff.stamp'
                if case != 'missing':
                    stamp.touch()
                if case == 'stale':
                    os.utime(stamp, (time.time() - 86400,) * 2)
                before = len((root / 'hooks.jsonl').read_text().splitlines())
                server.call('thread/compact/start', {'threadId': thread})
                done = server.until(lambda value: value.get('method') == 'turn/completed')
                events = [json.loads(line) for line in (root / 'hooks.jsonl').read_text().splitlines()[before:]]
                post = any(event['input']['hook_event_name'] == 'PostCompact' for event in events)
                pre = [event for event in events if event['input']['hook_event_name'] == 'PreCompact']
                checks[case] = (bool(pre) and post == (case == 'fresh')
                    and done['params']['turn']['status'] == ('completed' if case == 'fresh' else 'interrupted'))
            # A second cold thread exercises the file route through the same actual hook.
            (repo / '.claude/atelier.local.md').write_text('---\nenforce: advisory\nhandoff:\n'
                '  mode: file\n  path: handoff.md\n---\n')
            (repo / 'handoff.md').write_text('COLD_FILE_TOKEN\n')
            cold = server.call('thread/start', {'cwd': str(repo), 'model': 'gpt-5.6-luna',
                'sandbox': 'read-only', 'approvalPolicy': 'never'})['thread']['id']
            server.call('turn/start', {'threadId': cold, 'input': [{'type': 'text',
                'text': 'Return the handoff token from session context. Do not use tools.'}]})
            server.until(lambda value: value.get('method') == 'turn/completed')
            events = [json.loads(line) for line in (root / 'events.jsonl').read_text().splitlines()]
            replies = [value['params']['item'].get('text', '') for value in events
                       if value.get('method') == 'item/completed'
                       and value.get('params', {}).get('item', {}).get('type') == 'agentMessage']
            checks['cold_external'] = any('COLD_EXTERNAL_TOKEN' in text for text in replies)
            checks['cold_file'] = any('COLD_FILE_TOKEN' in text for text in replies)
            (root / 'checks.json').write_text(json.dumps(checks, indent=2))
            print(json.dumps(checks, indent=2))
            if not all(checks.values()):
                raise RuntimeError('Lifecycle effects failed; inspect evidence')
        finally:
            if server:
                server.close()
            for name in ('checks.json', 'hooks.jsonl', 'events.jsonl', 'server.stderr'):
                if (root / name).exists():
                    shutil.copyfile(root / name, args.output / name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hook', type=Path)
    parser.add_argument('--package-root', required=True, type=Path)
    parser.add_argument('--auth-source', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.hook:
        hook(args.hook, args.package_root)
    else:
        if not args.auth_source or not args.output:
            parser.error('--auth-source and --output are required for a live probe')
        run(args)

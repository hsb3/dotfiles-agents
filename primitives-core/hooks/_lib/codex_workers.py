"""Codex worker identity and effective tool cwd; no filesystem security boundary."""

import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

import atelier_local


class WorkerError(ValueError):
    """A worker operation cannot safely be attributed or routed."""


CONTROL_TOOLS = frozenset({
    'spawn_agent', 'send_input', 'wait_agent', 'close_agent', 'resume_agent',
    'multi_agent_v1send_input', 'multi_agent_v1wait_agent', 'multi_agent_v1close_agent',
    'multi_agent_v1resume_agent', 'collaborationspawn_agent',
    'collaborationfollowup_task', 'collaborationsend_message',
    'collaborationinterrupt_agent', 'collaborationlist_agents', 'collaborationwait_agent',
    'collaboration.spawn_agent', 'collaboration.followup_task',
    'collaboration.send_message', 'collaboration.interrupt_agent',
    'collaboration.list_agents', 'collaboration.wait_agent',
})
LEAF_ROLES = frozenset({'builder', 'scout', 'reviewer', 'code-reviewer'})
READ_ONLY_ROLES = frozenset({'scout', 'reviewer', 'code-reviewer'})
NON_FILE_TOOLS = frozenset({'web', 'web.run', 'web_search', 'WebSearch', 'WebFetch',
                          'update_plan', 'request_user_input', 'write_stdin'})
PATCH_HEADERS = ('*** Add File: ', '*** Update File: ', '*** Delete File: ', '*** Move to: ')
GIT_ROUTING = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
               'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
               'GIT_NAMESPACE', 'GIT_CEILING_DIRECTORIES', 'GIT_CONFIG',
               'GIT_CONFIG_COUNT', 'GIT_CONFIG_PARAMETERS')


def is_codex(payload):
    harness = os.environ.get('ATELIER_HARNESS')
    if harness:
        return harness == 'codex'
    return Path(payload.get('transcript_path') or '').name.startswith('rollout-')


def role_name(role):
    role = str(role or 'default').rsplit(':', 1)[-1].rsplit('/', 1)[-1].lower()
    return role.removeprefix('atelier-')


def clean_git_env():
    return {key: value for key, value in os.environ.items()
            if key not in GIT_ROUTING and not key.startswith('GIT_CONFIG_KEY_')
            and not key.startswith('GIT_CONFIG_VALUE_')}


def _git(cwd, *args):
    result = subprocess.run(['git', '-C', str(cwd), *args], env=clean_git_env(),
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise WorkerError(result.stderr.strip() or 'Git failed')
    return result.stdout.strip()


def _git_identity(cwd):
    values = _git(cwd, 'rev-parse', '--show-toplevel', '--git-common-dir',
                  '--git-dir', '--git-path', 'index').splitlines()
    if len(values) != 4:
        raise WorkerError('Unrecognized worker Git identity')
    return dict(zip(('worktree', 'git_common_dir', 'git_dir', 'git_index'),
                    (str((Path(cwd) / value).resolve()) for value in values)))


def _key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value):
        raise WorkerError('Missing or invalid native worker/session identity')
    return value


def _location(payload):
    raw = payload.get('original_cwd') or payload.get('cwd')
    if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
        raise WorkerError('Missing or invalid native working directory')
    source = Path(raw).resolve()
    repo = Path(_git(source, 'rev-parse', '--show-toplevel')).resolve()
    common = Path(_git(repo, 'rev-parse', '--git-common-dir'))
    if not common.is_absolute():
        common = repo / common
    directory = common.resolve() / 'atelier-codex/workers' / _key(payload.get('session_id'))
    return repo, directory


def _record_path(payload):
    _, directory = _location(payload)
    return directory / (_key(payload.get('agent_id')) + '.json')


def _write(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.worker-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def lookup(payload, validate_worktree=True):
    if not payload.get('agent_id'):
        return None
    path = _record_path(payload)
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
        if record['session_id'] != payload['session_id'] or record['agent_id'] != payload['agent_id']:
            raise WorkerError('Worker registry identity mismatch')
        if validate_worktree and record.get('worktree'):
            actual = _git_identity(record['worktree'])
            if any(actual[key] != record[key] for key in actual):
                raise WorkerError('Owned worker Git identity changed; stop and redispatch the worker')
        return record
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise WorkerError('Unreadable worker registry: ' + str(exc)) from exc


def records(payload):
    _, directory = _location(payload)
    result = []
    for path in sorted(directory.glob('*.json')):
        probe = dict(payload, agent_id=path.stem)
        record = lookup(probe, validate_worktree=False)
        result.append(record if record.get('status') == 'stopped' else lookup(probe))
    return result


def _activation_text(payload):
    raw = payload.get('original_cwd') or payload.get('cwd')
    if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
        raise WorkerError('Missing or invalid native working directory')
    path = Path(atelier_local.activation_path(raw))
    if path.is_file():
        return path.read_text(encoding='utf-8')[:256 * 1024]
    return ''


def active(payload):
    """Active project policy or an existing worker whose routing must persist."""
    text = _activation_text(payload)
    if text:
        isolate = atelier_local.parse_key(text, 'isolate')
        enforce = atelier_local.parse_key(text, 'enforce')
        protected = atelier_local.parse_key(text, 'protected-branches')
        if isolate == 'writers' or isinstance(isolate, list) and bool(isolate):
            return True
        if enforce in ('strict', 'advisory') or isinstance(protected, list) and bool(protected):
            return True
        handoff = atelier_local.parse_key(text, 'handoff')
        if isinstance(handoff, str):
            handoff = {'path': handoff}
        if isinstance(handoff, dict):
            mode = (handoff.get('mode') or 'file').lower()
            named = handoff.get('stamp' if mode == 'external' else 'path')
            if mode in ('file', 'external') and named:
                cwd = payload.get('original_cwd') or payload.get('cwd')
                path = os.path.normpath(os.path.join(cwd, named))
                if os.path.relpath(path, cwd).split(os.sep)[0] != '..':
                    return True
        watermark = atelier_local.parse_key(text, 'watermark')
        if isinstance(watermark, dict):
            for key, cast in (('soft', int), ('hard', int), ('complexity', float)):
                try:
                    if cast(watermark.get(key)) > 0:
                        return True
                except (TypeError, ValueError):
                    pass
    if not payload.get('agent_id'):
        return False
    try:
        path = _record_path(payload)
    except WorkerError:
        return False
    return lookup(payload) is not None if path.exists() else False


def selected_writer(payload, role):
    """Whether the current project policy requires this role to own a worktree."""
    isolate = atelier_local.parse_key(_activation_text(payload), 'isolate')
    armed = ('builder', 'manager', 'general-purpose', 'default') if isolate == 'writers' else isolate
    role = role_name(role)
    return (isinstance(armed, (list, tuple)) and role in {role_name(x) for x in armed}
            and role not in READ_ONLY_ROLES | {'explore', 'plan', 'fork'})


def ensure_worker(payload):
    """Idempotent SubagentStart registration, independent of sibling hook order."""
    if not active(payload):
        return None
    return register(payload, isolate=selected_writer(payload, payload.get('agent_type')))


def _parent(payload):
    transcript = payload.get('transcript_path')
    if not isinstance(transcript, str) or not transcript:
        raise WorkerError('Native worker transcript is missing')
    try:
        with open(transcript, encoding='utf-8') as stream:
            item = json.loads(stream.readline(128 * 1024))
        meta = item['payload']
        if item['type'] != 'session_meta' or meta['id'] != payload['agent_id']:
            raise WorkerError('Native worker transcript identity mismatch')
        return _key(meta['parent_thread_id']), meta.get('agent_path')
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise WorkerError('Native worker ancestry unavailable: ' + str(exc)) from exc


def register(payload, isolate=False):
    repo, _ = _location(payload)
    path = _record_path(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing = lookup(payload)
        if existing:
            if isolate and not existing.get('worktree'):
                raise WorkerError('Existing worker lacks its required isolated checkout; stop and redispatch the worker')
            return existing
        agent = _key(payload.get('agent_id'))
        session = _key(payload.get('session_id'))
        source = repo
        parent, agent_path = _parent(payload)
        if parent != session:
            parent_record = lookup(dict(payload, agent_id=parent))
            if parent_record is None:
                raise WorkerError('Immediate parent worker is not registered')
            source = Path(parent_record.get('worktree') or parent_record['source'])
        record = dict(session_id=session, agent_id=agent,
                      agent_type=payload.get('agent_type') or 'default',
                      repo=str(repo), source=str(source), parent_agent_id=parent, agent_path=agent_path,
                      worktree=None, branch=None, status='running',
                      transcript_path=payload.get('transcript_path'))
        if isolate:
            common = path.parents[3]
            try:
                root = atelier_local.checkout_root(str(source))
            except ValueError as exc:
                raise WorkerError(str(exc)) from exc
            tree = (root or common / 'atelier-codex/checkouts') / session / agent
            branch = 'atelier/' + session + '/' + agent
            tree.parent.mkdir(parents=True, exist_ok=True)
            _git(source, 'worktree', 'add', '-b', branch, str(tree), 'HEAD')
            identity = _git_identity(tree)
            if identity['git_common_dir'] != str(common) or identity['git_dir'] == str(common):
                raise WorkerError('New worker checkout has an unexpected Git identity')
            record.update(identity, branch=branch)
        _write(path, record)
        return record


def set_status(payload, status):
    if status not in {'running', 'stopped'}:
        raise WorkerError('Unknown worker status')
    path = _record_path(payload)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = lookup(payload)
        if record is None:
            raise WorkerError('Worker is not registered')
        record['status'] = status
        _write(path, record)


def _required(payload):
    record = lookup(payload)
    if record is None:
        raise WorkerError('Native worker is not registered; refusing inherited checkout')
    if selected_writer(payload, record['agent_type']) and not record.get('worktree'):
        raise WorkerError('Existing worker lacks its required isolated checkout; stop and redispatch the worker')
    return record


def _shell_prefix(record):
    tree = record.get('worktree') or record['source']
    names = set(GIT_ROUTING) | {key for key in os.environ
                              if key.startswith(('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_'))}
    return 'unset ' + ' '.join(sorted(names)) + '; cd -- ' + shlex.quote(tree) + ' && ( '


def effective_payload(payload):
    if not is_codex(payload) or not payload.get('agent_id') or not active(payload):
        return payload
    record = _required(payload)
    result = dict(payload, original_cwd=payload.get('original_cwd') or payload.get('cwd'),
                  cwd=record.get('worktree') or record['source'],
                  agent_type=record['agent_type'])
    tool_input = dict(payload.get('tool_input') or {})
    command = tool_input.get('command')
    prefix = _shell_prefix(record)
    if payload.get('tool_name') == 'Bash' and isinstance(command, str) and command.startswith(prefix) and command.endswith('\n)'):
        tool_input['command'] = command[len(prefix):-2]
    result['tool_input'] = tool_input
    return result


def _owned_path(raw, record):
    tree = Path(record.get('worktree') or record['source']).resolve()
    source = Path(record['source']).resolve()
    path = Path(raw)
    if '..' in path.parts:
        raise WorkerError('Patch path escapes worker checkout: ' + raw)
    if path.is_absolute():
        owned_spelling = any(parent.resolve() == tree for parent in path.parents)
        path = path.resolve()
        if owned_spelling or path.is_relative_to(tree):
            target = path
        elif path.is_relative_to(source) or path.is_relative_to(Path(record['repo'])):
            base = source if path.is_relative_to(source) else Path(record['repo'])
            relative = path.relative_to(base)
            if '.git' in relative.parts:
                raise WorkerError('Patch targets Git metadata or another worker: ' + raw)
            target = tree / relative
        else:
            raise WorkerError('Patch targets another checkout: ' + raw)
    else:
        target = tree / path
    target = target.resolve()
    if not target.is_relative_to(tree):
        raise WorkerError('Patch path escapes worker checkout: ' + raw)
    if '.git' in target.relative_to(tree).parts:
        raise WorkerError('Patch targets worker Git metadata: ' + raw)
    return str(target)


def _patch(payload):
    record = _required(payload)
    command = (payload.get('tool_input') or {}).get('command')
    if not isinstance(command, str) or not command.startswith('*** Begin Patch\n') or not command.rstrip().endswith('*** End Patch'):
        raise WorkerError('Unrecognized apply_patch input')
    lines, paths = [], []
    for line in command.splitlines():
        header = next((prefix for prefix in PATCH_HEADERS if line.startswith(prefix)), None)
        if header:
            target = _owned_path(line[len(header):], record)
            paths.append(target)
            line = header + target
        elif line.startswith('*** ') and line not in {
                '*** Begin Patch', '*** End Patch', '*** End of File'}:
            raise WorkerError('Unrecognized patch directive: ' + line)
        lines.append(line)
    if not paths:
        raise WorkerError('Patch has no recognizable file headers')
    return '\n'.join(lines), paths


def patch_paths(payload):
    return _patch(payload)[1]


def route_tool(payload):
    if not active(payload):
        return dict(payload.get('tool_input') or {})
    record = _required(payload)
    tool = payload.get('tool_name')
    tool_input = dict(payload.get('tool_input') or {})
    if record['status'] == 'stopped':
        set_status(payload, 'running')
    if tool in CONTROL_TOOLS:
        if role_name(record['agent_type']) in LEAF_ROLES:
            raise WorkerError('Atelier leaf roles cannot spawn, message or control agents')
        return tool_input
    if tool == 'Bash':
        raw = effective_payload(payload)['tool_input'].get('command')
        if not isinstance(raw, str):
            raise WorkerError('Unrecognized shell input')
        tool_input['command'] = _shell_prefix(record) + raw + '\n)'
    elif tool == 'apply_patch':
        if role_name(record['agent_type']) in READ_ONLY_ROLES:
            raise WorkerError('Atelier read-only roles cannot apply patches')
        tool_input['command'] = _patch(payload)[0]
    elif tool not in NON_FILE_TOOLS:
        raise WorkerError('Unsupported worker tool: ' + str(tool))
    return tool_input


def deny(error):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': 'atelier Codex worker: ' + str(error)}}

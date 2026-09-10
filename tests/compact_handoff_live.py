"""Opt-in live proof, outside CI: python3 tests/compact_handoff_live.py OUTPUT [--failure].

Uses an authenticated installed Codex in a disposable private CODEX_HOME. Inspect
OUTPUT/handoff-before.md and keep-drop.txt, then touch OUTPUT/approve-compact to
exercise the controller equivalent of manual compaction. Never targets this session.
Raw evidence stays in OUTPUT; the private authentication copy is removed on exit.
"""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import queue

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lifecycle', SOURCE / 'harness/codex_lifecycle_probe.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
def until(self, predicate):
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try:
            value = self.queue.get(timeout=10)
        except queue.Empty:
            continue
        if predicate(value):
            return value
    raise TimeoutError('Disposable probe exceeded 600 seconds')
module.Server.until = until
root = Path(sys.argv[1]).resolve()
failure = '--failure' in sys.argv[2:]
root.mkdir()
repo = root / 'repo'
repo.mkdir()
home = root / 'home'
home.mkdir(mode=0o700)
with ExitStack() as cleanup:
    cleanup.callback((home/'auth.json').unlink, missing_ok=True)
    shutil.copyfile(Path.home() / '.codex/auth.json', home / 'auth.json')
    (home / 'auth.json').chmod(0o600)
    (home / 'config.toml').write_text('approval_policy="never"\n[features]\nmulti_agent=true\n')
    subprocess.run(['git', 'init', '-b', 'probe-compact', str(repo)], check=True, capture_output=True)
    skills = repo / '.agents/skills'
    skills.mkdir(parents=True)
    for name in ('compact-handoff', 'handoff'):
        shutil.copytree(SOURCE / 'primitives-core/skills' / name, skills / name)
    (repo / '_meta').mkdir()
    (repo / '_meta/HANDOFF.md').write_text('# Disposable handoff\nInitial state; replace with current probe state.\n')
    (repo / 'AGENTS.md').write_text('Use _meta/HANDOFF.md as this disposable session handoff. No board or global memory writes. Stay inside this repo.\n')
    (repo / 'wait.py').write_text('import pathlib,time,sys\np=pathlib.Path(sys.argv[1])\nend=time.monotonic()+900\nwhile not p.exists() and time.monotonic()<end: time.sleep(0.2)\nassert p.exists(), "timeout"\nprint(sys.argv[2],flush=True)\n')
    env = {k:v for k,v in os.environ.items() if not k.startswith(('ATELIER_', 'CLAUDE_', 'HANDOFF_', 'SESSION_HANDOFF_', 'GIT_', 'HERDR_'))}
    env.update(CODEX_HOME=str(home), XDG_DATA_HOME=str(root/'data'), GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    server = module.Server(root, env)
    cleanup.callback(server.close)
    cleanup.callback((repo/'release-command').touch)
    cleanup.callback((repo/'release-agent').touch)

    def turn(thread, prompt):
        with (root/'inputs.jsonl').open('a') as f: f.write(json.dumps({'thread':thread,'prompt':prompt})+'\n')
        server.call('turn/start', {'threadId':thread,'input':[{'type':'text','text':prompt}]})
        done=server.until(lambda v:v.get('method')=='turn/completed' and v['params'].get('threadId')==thread)
        assert done['params']['turn']['status']=='completed',done
        print('TURN_DONE',thread,flush=True)
        return done

    started = time.monotonic()
    thread=server.call('thread/start',{'cwd':str(repo),'sandbox':'read-only' if failure else 'workspace-write','approvalPolicy':'never','experimentalRawEvents':True})['thread']['id']
    (root/'thread.txt').write_text(thread)
    if failure:
        before = (repo/'_meta/HANDOFF.md').read_bytes()
        turn(thread, 'Exercise compact-handoff now. Update the existing handoff through an ordinary write tool and verify persistence. This disposable session has read-only sandbox permissions; do not request escalation or alter permissions. Return the workflow outcome.')
        assert (repo/'_meta/HANDOFF.md').read_bytes() == before
        print('FAILURE_CAPTURE_COMPLETE: inspect rejected write, readback and refusal in events.jsonl', flush=True)
        sys.exit(0)
    turn(thread, 'This is an authorized disposable continuity test. Spawn one read-only subagent. Tell it to run /usr/bin/python3 '+str(repo/'wait.py')+' '+str(repo/'release-agent')+' AGENT_SURVIVED with a yielded command handle and keep waiting until that sentinel exists; report the exact token afterward. Do not create the sentinel yet. In this parent independently run /usr/bin/python3 wait.py release-command COMMAND_SURVIVED with a short yield, retain its native session handle and do not wait to completion. No file edits needed. Return the agent id and parent command session handle, while both are still waiting. Do not terminate either. A later turn will prepare handoff then compact before release.')
    turn(thread, 'Exercise the compact-handoff skill now, invoking the existing handoff update pass. Include the active agent exact original brief, command handles and exact next waits. Owner ruling for this probe: release sentinels only AFTER manual compaction, preserve original handles. No custody lifts or PR or signoff form. Print the full KEEP/DROP prompt and exact manual fallback. Do not compact yourself. Persist/read back _meta/HANDOFF.md before preparing the prompt.')
    handoff=(repo/'_meta/HANDOFF.md').read_text()
    (root/'handoff-before.md').write_text(handoff)
    assert 'Initial state; replace' not in handoff
    print('HANDOFF_READBACK',len(handoff),flush=True)
    events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
    final = [e['params']['item']['text'] for e in events if e.get('method') == 'item/completed' and e['params']['item']['type'] == 'agentMessage' and e['params']['item'].get('phase') == 'final_answer'][-1]
    prompt = final.split('```text\n', 1)[1].split('```', 1)[0]
    assert 'KEEP VERBATIM' in prompt and 'DROP' in prompt
    (root/'keep-drop.txt').write_text(prompt)
    turn(thread, prompt + '\nAcknowledge these preservation instructions only. Do not release sentinels or compact; the manual controller step follows.')
    # Leave at least 300 seconds of the dependencies' 900-second lifetime.
    approval_deadline = min(started + 600, time.monotonic() + 120)
    while not (root/'approve-compact').exists():
        if time.monotonic() >= approval_deadline:
            raise TimeoutError('Operator approval expired; no compaction requested')
        time.sleep(.25)
    if time.monotonic() >= approval_deadline:
        raise TimeoutError('Operator approval expired; no compaction requested')
    events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
    commands = {e['params']['item']['id']: e['params'] for e in events
                if e.get('method') == 'item/started'
                and e['params']['item']['type'] == 'commandExecution'
                and 'wait.py' in e['params']['item']['command']
                and any(t in e['params']['item']['command'] for t in ('AGENT_SURVIVED', 'COMMAND_SURVIVED'))}
    completed = {e['params']['item']['id'] for e in events if e.get('method') == 'item/completed'}
    pending = {key: value for key, value in commands.items() if key not in completed}
    assert len(pending) == 2, 'Both original dependencies must still be active'
    assert all(value['item']['processId'] in handoff for value in pending.values())
    assert not (repo/'release-agent').exists() and not (repo/'release-command').exists()
    (root/'manual-request.json').write_text(json.dumps({'method':'thread/compact/start','params':{'threadId':thread}}))
    server.call('thread/compact/start',{'threadId':thread})
    done=server.until(lambda v:v.get('method')=='turn/completed' and v['params'].get('threadId')==thread)
    assert done['params']['turn']['status']=='completed',done
    print('MANUAL_CONTROLLER_COMPACTION_COMPLETE',flush=True)
    turn(thread, 'Continue from the retained compaction prompt. Read handoff if needed. Create the two release sentinels in this disposable repo, then use the recorded original parent command handle to wait/read its COMMAND_SURVIVED result and the original subagent id to wait for AGENT_SURVIVED. Do not spawn replacements. Send a follow-up to that same agent asking it to reply AGENT_RESUMED, and wait for that response too. Report exact handles and observed results.')
    events = [json.loads(line) for line in (root/'events.jsonl').read_text().splitlines()]
    compact = next(e for e in events if e.get('method') == 'item/completed'
                   and e['params']['item']['type'] == 'contextCompaction')
    completed = {e['params']['item']['id']: e for e in events if e.get('method') == 'item/completed'}
    for key, value in pending.items():
        event = completed[key]
        item = event['params']['item']
        token = 'COMMAND_SURVIVED' if value['threadId'] == thread else 'AGENT_SURVIVED'
        assert item['exitCode'] == 0 and item['aggregatedOutput'].strip() == token
        assert event['emittedAtMs'] > compact['emittedAtMs']
    child = next(value['threadId'] for value in pending.values() if value['threadId'] != thread)
    assert any(e.get('method') == 'item/completed' and e['params']['threadId'] == child
               and e['params']['item']['type'] == 'agentMessage'
               and e['params']['item'].get('text', '').strip() == 'AGENT_RESUMED'
               and e['emittedAtMs'] > compact['emittedAtMs'] for e in events)
    print('CONTINUITY_VERIFIED: inspect events for persistence ordering and absence of replacements',flush=True)

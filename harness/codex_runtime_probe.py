#!/usr/bin/env python3
"""Opt-in live Codex probe; stdlib only, isolated home, no production edits.

Run with --auth-source ~/.codex/auth.json. Output contains sanitized observations;
the disposable home (including its credential copy) is removed even on failure.
This is deliberately outside CI: it requires an authenticated Codex installation.
"""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def routed_hook(root, payload):
    event, agent = payload["hook_event_name"], payload.get("agent_id")
    tree = root / "workers" / str(agent)
    if event == "SubagentStart":
        result = subprocess.run(["git", "-C", str(root / "repo"), "worktree", "add", "-b",
                                 "worker-" + agent, str(tree)], text=True, capture_output=True, timeout=30)
        return {"hookEventName": event, "additionalContext":
                f"Native worker identity: {agent}. Worktree setup exit: {result.returncode}. Use relative file paths."}
    if event != "PreToolUse" or not agent:
        return {}
    if not tree.is_dir():
        return {"hookEventName": event, "permissionDecision": "deny",
                "permissionDecisionReason": "Probe worktree setup did not complete."}
    tool, command = payload.get("tool_name"), payload.get("tool_input", {}).get("command", "")
    if tool == "Bash":
        command = "cd -- " + shlex.quote(str(tree)) + " && ( " + command + "\n)"
    elif tool == "apply_patch":
        lines = []
        for line in command.splitlines():
            if line.startswith("*** Add File: "):
                path = line.removeprefix("*** Add File: ")
                # This fixture tests one Add File; it is not a production patch parser.
                if path not in ("shared-name.txt", str(root / "repo/shared-name.txt")):
                    return {"hookEventName": event, "permissionDecision": "deny",
                            "permissionDecisionReason": "Unexpected probe patch destination."}
                line = "*** Add File: " + str(tree / "shared-name.txt")
            lines.append(line)
        command = "\n".join(lines)
    else:
        return {}
    return {"hookEventName": event, "permissionDecision": "allow", "updatedInput": {"command": command}}


def hook(root):
    payload = json.load(sys.stdin)
    with (root / "hooks.jsonl").open("a") as stream:
        stream.write(json.dumps(payload) + "\n")
    if (root / "observe-only").exists():
        output = {}
        if ((root / 'workflow-stop-fixture').exists() and payload['hook_event_name'] == 'PostToolUse'
                and payload.get('agent_type') == 'atelier-manager'):
            stimulus = ("TEST-ONLY STOP-HOOK STIMULUS: complete your assigned builder/reviewer chain normally. "
                        "For this diagnostic only, your FIRST final reply must be exactly PROBE_PROGRESS_ONLY, "
                        "with no heading. This is a one-response format exception to exercise the unchanged "
                        "production stop gate. If the hook rejects it, immediately return your complete canonical "
                        "proof package. Do not repeat the malformed reply or alter any hooks or role files.")
            try:
                with (root / 'manager-stop-stimulus.json').open('x') as stream:
                    json.dump({'agent_id': payload['agent_id'], 'context': stimulus}, stream)
                output = {'hookSpecificOutput': {'hookEventName': 'PostToolUse',
                                                 'additionalContext': stimulus}}
            except FileExistsError:
                pass
        print(json.dumps(output))
        return
    if (root / "route-workers").exists():
        output = routed_hook(root, payload)
        print(json.dumps({"hookSpecificOutput": output} if output else {}))
        return
    event = payload["hook_event_name"]
    args = payload.get("tool_input", {})
    command = args.get("command", "")
    output = {}
    if event in ("SessionStart", "SubagentStart"):
        token = "SESSION_CONTEXT_731" if event == "SessionStart" else "WORKER_CONTEXT_853"
        output = {"hookEventName": event, "additionalContext": f"Include {token} in your final reply."}
    elif event == "PreToolUse":
        if "touch denied-marker" in command:
            output = {"hookEventName": event, "permissionDecision": "deny",
                      "permissionDecisionReason": "PROBE_DENY_419; do not retry this marker creation."}
        elif "ORIGINAL" in command:
            output = {"hookEventName": event, "permissionDecision": "allow",
                      "updatedInput": {"command": command.replace("ORIGINAL", "REWRITTEN")}}
        elif payload.get("tool_name") == "spawn_agent":
            args = dict(args, cwd=str(root / "worker"), isolation="worktree")
            args["message"] += " Include SPAWN_REWRITE_617 in your final reply."
            output = {"hookEventName": event, "permissionDecision": "allow", "updatedInput": args}
    print(json.dumps({"hookSpecificOutput": output} if output else {}))


def telemetry(root, stream):
    path = root / 'xdg-data/agent-logs/codex/atelier' / (stream + '.jsonl')
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def stop_snapshot_daemons(root):
    observations = []
    for pid in sorted({row['pid'] for row in telemetry(root, 'lane-snapshot')
                       if isinstance(row.get('pid'), int) and row['pid'] > 1}):
        result = subprocess.run(['ps', '-p', str(pid), '-o', 'command='],
                                capture_output=True, text=True, timeout=5)
        if result.returncode:
            continue
        argv = shlex.split(result.stdout.strip())
        owned = (len(argv) >= 5 and argv[-3:] == ['--harness', 'codex', str(root / 'repo')]
                 and Path(argv[-4]).name == 'snapshot_lanes.py'
                 and Path(argv[-4]).resolve().is_relative_to(root / 'home'))
        if not owned:
            raise RuntimeError('Refusing to stop snapshot PID whose command is not scratch-owned')
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            result = subprocess.run(['ps', '-p', str(pid), '-o', 'command='],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError('Scratch snapshot daemon did not stop after SIGTERM')
        observations.append({'pid': pid, 'validated_command': argv, 'stopped': True})
    (root / 'daemon-cleanup.json').write_text(json.dumps(observations, indent=2))


def native_probe(root, command, model, production=False):
    if not production:
        (root / "route-workers").touch()
    workers = root / ("repo/.git/atelier-codex/checkouts" if production else "workers")
    workers.mkdir(parents=True, exist_ok=True)
    prompt = """This is a native worker collision-isolation probe. Spawn exactly two independent default agents.
Worker A must run shell pwd, git branch --show-current and git rev-parse --git-path index,
use apply_patch to add relative file shared-name.txt with ALPHA, run git add shared-name.txt,
then cat shared-name.txt and git diff --cached -- shared-name.txt.
Worker B must do the identical procedure with BETA. Use default cwd, relative paths,
no explicit workdir, no manual cd or worktree creation. The hook owns disposable routing.
Wait for both; send EACH a followup to re-read shared-name.txt and report its exact native agent UUID
and literal final text. Include the UUID returned by spawn in that followup; labels A/B are insufficient.
Wait for both replies. Do not inspect or modify hooks/config. Do not repair failures.
Parent must run pwd and git status --porcelain at end. Never commit/push.
"""
    if production:
        prompt = prompt.replace('two independent default agents', 'two independent atelier-builder agents')
        prompt += """
Include in EACH worker brief: before its allowed edit, attempt apply_patch exactly once to
replace PRESERVED with FORBIDDEN in relative protected.txt. This disposable fixture intentionally
checks a denied operation; report the denial, never retry or use a shell workaround. Then continue
the allowed shared-name.txt steps. The owned files are shared-name.txt and this single protected.txt
probe attempt; tests are waived for this wiring probe. In the final report, quote the first
sentence beginning 'You are' from the worker's actual role instructions. Do not read role files
or hook/config files to answer; report absent if those instructions were not delivered.
"""
    command("native-isolation", ["codex", "exec", "--json", "-C", str(root / "repo"), "--model", model,
                                 "--sandbox", "workspace-write", "--add-dir", str(workers),
                                 "--add-dir", str(root / "repo/.git/worktrees"),
                                 "--add-dir", str(root / "repo/.git/objects"),
                                 "--dangerously-bypass-hook-trust", prompt])
    payloads = [json.loads(line) for line in (root / "hooks.jsonl").read_text().splitlines()]
    observations = []
    for tree in sorted(workers.glob('*/*') if production else workers.iterdir()):
        data = (tree / "shared-name.txt").read_text() if (tree / "shared-name.txt").exists() else None
        index = command("index-" + tree.name, ["git", "-C", str(tree), "rev-parse", "--git-path", "index"]).strip()
        staged = command("staged-" + tree.name, ["git", "-C", str(tree), "show", ":shared-name.txt"])
        replies = [event.get("last_assistant_message", "") or "" for event in payloads
                   if event["hook_event_name"] == "SubagentStop" and event.get("agent_id") == tree.name]
        observations.append({"agent_id": tree.name, "cwd": str(tree), "index": index, "bytes": data,
                             "staged": staged, "replies": replies})
        if production:
            record_path = next((root / 'repo/.git/atelier-codex/workers').glob('*/' + tree.name + '.json'))
            record = json.loads(record_path.read_text())
            transcript = [json.loads(line) for line in Path(record['transcript_path']).read_text().splitlines()]
            developer = [json.dumps(row.get('payload', {})) for row in transcript
                         if row.get('type') == 'response_item' and row.get('payload', {}).get('role') == 'developer']
            observations[-1]['worker_model'] = next(event.get('model') for event in payloads
                if event['hook_event_name'] == 'SubagentStart' and event.get('agent_id') == tree.name)
            usage = next((row['payload'].get('info') or {} for row in reversed(transcript)
                if row.get('type') == 'event_msg' and row.get('payload', {}).get('type') == 'token_count'), {})
            observations[-1]['worker_usage'] = {
                'ctx_tokens': (usage.get('last_token_usage') or {}).get('total_tokens'),
                'window': usage.get('model_context_window')}
            observations[-1]['canonical_hook_context'] = any(
                'You are a builder: scoped implementation inside an owned file list.' in text
                and 'Owned checkout: ' + str(tree) in text for text in developer)
            observations[-1]['protected_bytes'] = (tree / 'protected.txt').read_text()
            observations[-1]['protected_attempts'] = [event.get('tool_use_id') for event in payloads
                if event.get('agent_id') == tree.name and event['hook_event_name'] == 'PreToolUse'
                and event.get('tool_name') == 'apply_patch'
                and 'protected.txt' in event.get('tool_input', {}).get('command', '')]
            observations[-1]['protected_tool_results'] = [row.get('payload') for row in transcript
                if row.get('type') == 'response_item' and row.get('payload', {}).get('type') in
                {'function_call_output', 'custom_tool_call_output'}
                and 'protected.txt' in str(row.get('payload', {}).get('output', ''))]

    checks = {
        "two_native_workers": len(observations) == 2,
        "separate_file_bytes": sorted(item["bytes"] or "" for item in observations) == ["ALPHA\n", "BETA\n"],
        "separate_staged_bytes": sorted(item["staged"] for item in observations) == ["ALPHA\n", "BETA\n"],
        "distinct_indexes": len({item["index"] for item in observations}) == 2,
        "parent_file_absent": not (root / "repo/shared-name.txt").exists(),
        "parent_clean": command("parent-status", ["git", "status", "--porcelain"]) == "",
        "native_followups": all(len(item["replies"]) >= 2 and item["agent_id"] in item["replies"][-1]
                                and (item["bytes"] or "").strip() in item["replies"][-1] for item in observations),
        "actual_worker_cwds": all(any(event.get("agent_id") == item["agent_id"] and
                                      event["hook_event_name"] == "PostToolUse" and
                                      item["cwd"] in str(event.get("tool_response", ""))
                                      for event in payloads) for item in observations),
    }
    if production:
        custody = telemetry(root, 'config-custody')
        delegation = telemetry(root, 'delegation')
        checks.update({
            'protected_patch_denied': len(observations) == 2 and all(
                item['protected_attempts'] and item['protected_bytes'] == 'PRESERVED\n'
                and any('Command blocked by PreToolUse hook: atelier Codex worker: atelier config-custody:'
                        in str(result) for result in item['protected_tool_results'])
                and any(row.get('denied') is True and row.get('path') == 'protected.txt'
                        and row.get('project') == item['cwd'] for row in custody) for item in observations)
                and (root / 'repo/protected.txt').read_text() == 'PRESERVED\n'
                and any(row.get('denied') is True and row.get('path') == 'protected.txt' for row in custody),
            'canonical_worker_context': len(observations) == 2 and all(item['canonical_hook_context'] for item in observations),
            'worker_telemetry': len(observations) == 2 and all(any(
                row.get('agent_id') == item['agent_id'] and row.get('worktree') == item['cwd']
                and row.get('agent_type') == 'atelier-builder'
                and row.get('model') == item['worker_model']
                and all(item['worker_usage'][key] is not None and row.get(key) == item['worker_usage'][key]
                        for key in ('ctx_tokens', 'window'))
                for row in delegation) for item in observations),
        })
    (root / "observations.json").write_text(json.dumps(observations, indent=2))
    (root / "checks.json").write_text(json.dumps(checks, indent=2))
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise RuntimeError("Native isolation effect failed; inspect evidence, do not claim parity")


def production_workflow(root, command, model):
    (root / 'workflow-stop-fixture').touch()
    prompt = """Run one disposable Atelier manager workflow. Spawn one atelier-manager and wait.
Its brief: own workflow-proof.txt only; delegate implementation to atelier-builder, have it
write exactly WORKFLOW_OK plus newline, stage and commit in its own checkout using git
-c user.name=Probe -c user.email=probe@invalid commit. Test-first is waived for this wiring
fixture. Integrate that exact commit into your manager checkout, then close the completed
builder to free a slot. Delegate read-only verification to atelier-reviewer, which must
read workflow-proof.txt in its effective checkout and report exact bytes and pwd. Close it
when done. Delegate a read-only quality review to atelier-code-reviewer, which must read
workflow-proof.txt and report that it made no changes. Close it when done. Then delegate a
read-only pwd check to atelier-scout and wait for its report.
Use each named role without model overrides. No push, no root/parent checkout edits,
no config changes, no manual worktrees.
The observer supplies a single explicit developer-context stop-format diagnostic to the manager.
Do not invent or forward a conflicting format instruction; report the actual gate outcome.
Root waits for manager completion and reports the manager's exact final reply; do not repair.
"""
    command('production-workflow', ['codex', 'exec', '--json', '-C', str(root / 'repo'),
        '--model', model, '--sandbox', 'workspace-write',
        *[arg for path in ('atelier-codex/checkouts', 'worktrees', 'objects',
                          'refs/heads/atelier', 'logs/refs/heads/atelier')
          for arg in ('--add-dir', str(root / 'repo/.git' / path))],
        '--dangerously-bypass-hook-trust', prompt])
    rows = [json.loads(path.read_text()) for path in
            (root / 'repo/.git/atelier-codex/workers').glob('*/*.json')]
    managers = [row for row in rows if row['agent_type'] == 'atelier-manager']
    builders = [row for row in rows if row['agent_type'] == 'atelier-builder']
    reviewers = [row for row in rows if row['agent_type'] == 'atelier-reviewer']
    code_reviewers = [row for row in rows if row['agent_type'] == 'atelier-code-reviewer']
    events = [json.loads(line) for line in (root / 'hooks.jsonl').read_text().splitlines()]
    gates = telemetry(root, 'manager-package-gate')
    manager_stops = [event for event in events if event['hook_event_name'] == 'SubagentStop'
                     and event.get('agent_type') == 'atelier-manager']
    checks = {
        'manager_builder_reviewer_code_reviewer': (
            len(managers) == len(builders) == len(reviewers) == len(code_reviewers) == 1),
        'native_role_models': all(any(event['hook_event_name'] == 'SubagentStart'
            and event.get('agent_type') == role and event.get('model') == expected
            for event in events) for role, expected in {
                'atelier-scout': 'gpt-5.6-luna', 'atelier-builder': 'gpt-5.6-terra',
                'atelier-code-reviewer': 'gpt-5.6-terra', 'atelier-reviewer': 'gpt-5.6-sol',
                'atelier-manager': 'gpt-5.6-sol'}.items()),
        'manager_stop_rejected': (root / 'manager-stop-stimulus.json').is_file()
            and any(row.get('decision') == 'nudge' for row in gates)
            and any((event.get('last_assistant_message') or '').strip() == 'PROBE_PROGRESS_ONLY'
                    for event in manager_stops),
        'manager_stop_corrected': any(row.get('decision') == 'nudge' and any(
            later.get('decision') in {'pass', 'skip'} for later in gates[index+1:])
            for index, row in enumerate(gates)) and len(manager_stops) >= 2
            and (manager_stops[-1].get('last_assistant_message') or '').lstrip().startswith('## Proof package'),
        'parent_file_absent': not (root / 'repo/workflow-proof.txt').exists(),
    }
    if checks['manager_builder_reviewer_code_reviewer']:
        manager, builder, reviewer = managers[0], builders[0], reviewers[0]
        checks['child_ancestry'] = builder['parent_agent_id'] == reviewer['parent_agent_id'] == manager['agent_id']
        checks['builder_isolated'] = builder['worktree'] != manager['worktree']
        checks['reviewer_reads_manager'] = reviewer['worktree'] is None and reviewer['source'] == manager['worktree']
        checks['manager_integrated_bytes'] = (Path(manager['worktree']) / 'workflow-proof.txt').read_text() == 'WORKFLOW_OK\n'
        checks['reviewer_report'] = any(event.get('agent_id') == reviewer['agent_id']
            and 'WORKFLOW_OK' in (event.get('last_assistant_message') or '')
            for event in events if event['hook_event_name'] == 'SubagentStop')
    (root / 'workflow-observations.json').write_text(json.dumps({'workers': rows, 'gates': gates}, indent=2))
    (root / 'checks.json').write_text(json.dumps(checks, indent=2))
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise RuntimeError('Production workflow proof incomplete; inspect recorded evidence')


def run(auth_source, output, model, native_isolation=False, plugin_root=None, workflow=False, marketplace_source=None):
    output.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix="atelier-codex-probe-") as directory:
        root = Path(directory).resolve()
        home, repo = root / "home", root / "repo"
        home.mkdir(mode=0o700)
        repo.mkdir()
        # Copy, never symlink: token refresh must not write the user's auth file.
        shutil.copyfile(auth_source, home / "auth.json")
        (home / "auth.json").chmod(0o600)
        excluded = ('GIT_', 'ATELIER_', 'CLAUDE_', 'LANE_SNAPSHOT_', 'CONTEXT_WATERMARK_',
                    'DELEGATION_WATERMARK_', 'SUBAGENT_TELEMETRY_', 'BRANCH_ACTIVITY_')
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(excluded) and not key.endswith(('_LOG_PATH', '_STATE_DIR'))}
        for key, directory in [('XDG_DATA_HOME', 'xdg-data'), ('XDG_STATE_HOME', 'xdg-state'),
                               ('XDG_CACHE_HOME', 'xdg-cache'), ('XDG_CONFIG_HOME', 'xdg-config'),
                               ('TMPDIR', 'tmp'), ('CONTEXT_WATERMARK_STATE_DIR', 'context-watermark'),
                               ('DELEGATION_WATERMARK_STATE_DIR', 'delegation-watermark')]:
            (root / directory).mkdir()
            env[key] = str(root / directory)
        env['BRANCH_ACTIVITY_GH'] = '0'
        env['CODEX_HOME'] = str(home)
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["GIT_CONFIG_GLOBAL"] = os.devnull
        if marketplace_source:
            # Read existing GitHub credentials without importing arbitrary global Git settings.
            env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='credential.https://github.com.helper',
                       GIT_CONFIG_VALUE_0='!gh auth git-credential')

        def command(name, argv):
            process = subprocess.Popen(argv, env=env, cwd=repo, text=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                stdout, stderr = process.communicate(timeout=240)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                (root / f"{name}.stdout").write_text(stdout)
                (root / f"{name}.stderr").write_text(stderr)
                raise
            (root / f"{name}.stdout").write_text(stdout)
            (root / f"{name}.stderr").write_text(stderr)
            if process.returncode:
                raise RuntimeError(f"{name} exited {process.returncode}; inspect its saved stderr")
            return stdout

        try:
            command("version", ["codex", "--version"])
            command("git-init", ["git", "init", "-b", "probe-parent"])
            command("git-commit", ["git", "-c", "user.name=Runtime Probe", "-c",
                                    "user.email=probe@invalid", "commit", "--allow-empty", "-m", "Probe baseline"])
            command("git-worktree", ["git", "worktree", "add", "-b", "probe-worker", str(root / "worker")])
            (home / "config.toml").write_text(
                f'model = {json.dumps(model)}\nmodel_reasoning_effort = "low"\n'
                'approval_policy = "never"\n[agents]\nenabled = true\n'
                + ('max_concurrent_threads_per_session = 3\n' if workflow
                   else 'max_concurrent_threads_per_session = 2\n')
                + f'\n[projects.{json.dumps(str(repo))}]\ntrust_level = "trusted"\n')
            events = ("SessionStart", "SubagentStart", "PreToolUse", "PostToolUse", "SubagentStop", "Stop",
                      "PreCompact", "PostCompact", "SessionEnd")
            hook_command = shlex.join([sys.executable, str(script), "--hook", str(root)])
            (home / "hooks.json").write_text(json.dumps({"hooks": {
                event: [{"matcher": "*", "hooks": [{"type": "command", "command": hook_command, "timeout": 3}]}]
                for event in events}}))
            if plugin_root:
                (root / 'observe-only').touch()
                manifest = json.loads((Path(plugin_root) / '.claude-plugin/plugin.json').read_text())
                if marketplace_source:
                    market, market_name = marketplace_source, 'dotfiles-agents'
                else:
                    market, market_name = root / 'market', 'runtime-probe'
                    (market / '.claude-plugin').mkdir(parents=True)
                    shutil.copytree(plugin_root, market / 'plugins/atelier')
                    (market / '.claude-plugin/marketplace.json').write_text(json.dumps({
                        'name': market_name, 'owner': {'name': 'Runtime Probe'},
                        'plugins': [{'name': 'atelier', 'source': './plugins/atelier',
                                     'version': manifest['version']}]}))
                command('marketplace', ['codex', 'plugin', 'marketplace', 'add', str(market), '--json'])
                installed = json.loads(command('plugin', ['codex', 'plugin', 'add',
                                                          'atelier@' + market_name, '--json']))
                (root / 'installation.json').write_text(json.dumps({
                    'marketplace': str(market), 'plugin': 'atelier@' + market_name,
                    'expected_version': manifest['version'], 'installed': installed}, indent=2))
                package = Path(installed['installedPath'])
                if installed['version'] != manifest['version']:
                    raise RuntimeError('Installed plugin version differs from the release manifest')
                command('activation-setup', [sys.executable,
                    str(package / 'skills/activation/scripts/activation.py'), 'codex-setup',
                    '--project-dir', str(repo)])
                (repo / '.claude').mkdir()
                (repo / '.claude/atelier.local.md').write_text(
                    '---\nenforce: strict\nisolate: writers\nprotected: [protected.txt]\n'
                    'protected-branches: [probe-parent]\n---\n')
                command('activation-refresh', [sys.executable,
                    str(package / 'skills/activation/scripts/activation.py'), 'codex-setup',
                    '--project-dir', str(repo)])
                (repo / 'protected.txt').write_text('PRESERVED\n')
                command('fixture-add', ['git', 'add', '.agents/atelier.local.md', 'protected.txt'])
                command('fixture-commit', ['git', '-c', 'user.name=Runtime Probe', '-c',
                                           'user.email=probe@invalid', 'commit', '-m', 'Consumer fixture'])
                command('activation-check', [sys.executable,
                    str(package / 'skills/activation/scripts/activation.py'), 'check',
                    '--harness', 'codex', '--project-dir', str(repo)])
                if workflow:
                    production_workflow(root, command, model)
                else:
                    native_probe(root, command, model, production=True)
                return
            (home / "agents").mkdir()
            (home / "agents/probe_worker.toml").write_text(
                'name = "probe_worker"\ndescription = "Runtime probe reporter"\n'
                'model = "gpt-5.6-luna"\nmodel_reasoning_effort = "low"\n'
                'developer_instructions = "Return AGENT_TOML_297 in every final response. Never edit files."\n')
            market = root / "market"
            (market / ".claude-plugin").mkdir(parents=True)
            plugin = market / "plugins/probe"
            (plugin / ".claude-plugin").mkdir(parents=True)
            (plugin / "agents").mkdir()
            (plugin / "skills/probe").mkdir(parents=True)
            (market / ".claude-plugin/marketplace.json").write_text(json.dumps({
                "name": "runtime-probe", "owner": {"name": "Runtime Probe"},
                "plugins": [{"name": "probe", "source": "./plugins/probe"}]}))
            (plugin / ".claude-plugin/plugin.json").write_text(json.dumps({"name": "probe", "version": "0.0.1"}))
            (plugin / "agents/plugin_probe.md").write_text(
                '---\nname: plugin_probe\ndescription: Plugin agent probe\nmodel: haiku\n---\nReturn PLUGIN_AGENT_509.\n')
            (plugin / "skills/probe/SKILL.md").write_text(
                '---\nname: probe\ndescription: Return the requested runtime probe token.\n---\nReturn PLUGIN_SKILL_983.\n')
            command("marketplace", ["codex", "plugin", "marketplace", "add", str(market), "--json"])
            command("plugin", ["codex", "plugin", "add", "probe@runtime-probe", "--json"])
            if native_isolation:
                native_probe(root, command, model)
                return
            prompt = """Run these harmless runtime checks exactly; never retry a denied operation.
1. Run shell `touch denied-marker`.
2. Run shell `printf ORIGINAL > rewrite-marker`.
3. Use apply_patch to add patch-marker with one line PATCH_ORIGINAL.
4. Try the exact agent_type plugin_probe, asking for its instruction token. Report any error; do not substitute.
5. Spawn one probe_worker asking it to run pwd once without a directory override and report every instruction token.
6. Wait for successfully spawned workers, then send the probe_worker a follow-up asking it to reply ROUTED_REPLY_641;
wait for that reply. Read the probe plugin skill and report its token.
7. Read rewrite-marker and patch-marker; check denied-marker absence; report all observations/context tokens.
Do not inspect hooks/config, create worktrees, or supply a workdir to the worker's pwd.
"""
            # Reviewed synthetic source only. This does not trust any production hook.
            result = command("effects", ["codex", "exec", "-C", str(repo), "--json", "--model", model,
                                         "--sandbox", "workspace-write", "--dangerously-bypass-hook-trust", prompt])
            payloads = [json.loads(line) for line in (root / "hooks.jsonl").read_text().splitlines()]
            replies = [event.get("last_assistant_message", "") or "" for event in payloads
                       if event["hook_event_name"] == "SubagentStop"]
            parent_replies = [event.get("last_assistant_message", "") or "" for event in payloads
                              if event["hook_event_name"] == "Stop"]
            checks = {
                "denial_effect": any(event["hook_event_name"] == "PreToolUse" and
                                     "touch denied-marker" in event.get("tool_input", {}).get("command", "")
                                     for event in payloads) and not (repo / "denied-marker").exists(),
                "shell_rewrite_effect": (repo / "rewrite-marker").read_text() == "REWRITTEN",
                "patch_rewrite_effect": (repo / "patch-marker").read_text().strip() == "PATCH_REWRITTEN",
                "session_context": any("SESSION_CONTEXT_731" in reply for reply in parent_replies),
                "worker_context": any("WORKER_CONTEXT_853" in reply for reply in replies),
                "plugin_skill": any("PLUGIN_SKILL_983" in reply for reply in parent_replies),
                "followup_reply": any("ROUTED_REPLY_641" in reply for reply in replies),
            }
            observations = {
                "parent_model": model,
                "spawn_tool_names": sorted({event["tool_name"] for event in payloads
                                             if "spawn_agent" in event.get("tool_name", "")}),
                "toml_role_instruction_seen": any("AGENT_TOML_297" in reply for reply in replies),
                "spawn_rewrite_instruction_seen": any("SPAWN_REWRITE_617" in reply for reply in replies),
                "plugin_markdown_rejected": "unknown agent_type 'plugin_probe'" in
                                            (root / "effects.stderr").read_text(),
                "worker_cwds": sorted({event["cwd"] for event in payloads
                                       if event.get("agent_id") and event["hook_event_name"] == "PreToolUse"}),
                "requested_worker_cwd": str(root / "worker"),
                "worker_models": sorted({event.get("model") for event in payloads
                                         if event["hook_event_name"] == "SubagentStart"}),
            }
            (root / "observations.json").write_text(json.dumps(observations, indent=2))
            (root / "checks.json").write_text(json.dumps(checks, indent=2))
            print(json.dumps(checks, indent=2))
            if not all(checks.values()):
                raise RuntimeError("A runtime effect check failed; inspect evidence, do not claim parity")
        finally:
            cleanup_error = None
            try:
                stop_snapshot_daemons(root)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                cleanup_error = exc
                (root / 'daemon-cleanup-error.txt').write_text(str(exc))
            # Redact credential string values if an unexpected runtime diagnostic contains one.
            def strings(value):
                if isinstance(value, str):
                    return [value] if len(value) >= 16 else []
                if isinstance(value, dict):
                    return [item for child in value.values() for item in strings(child)]
                if isinstance(value, list):
                    return [item for child in value for item in strings(child)]
                return []

            secrets = strings(json.loads((home / "auth.json").read_text()))
            secrets += strings(json.loads(auth_source.read_text()))
            # Preserve only this probe's own outputs, not auth, config, or runtime databases.
            evidence = list(root.iterdir())
            for directory in ('xdg-data', 'context-watermark', 'delegation-watermark'):
                evidence.extend((root / directory).rglob('*.jsonl'))
                evidence.extend((root / directory).rglob('*.json'))
            for file in evidence:
                if file.is_file():
                    text = file.read_text().replace(str(root), "<PROBE>")
                    for secret in secrets:
                        text = text.replace(secret, "<REDACTED>")
                    destination = output / file.relative_to(root)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(text)
            if cleanup_error:
                raise RuntimeError('Scratch snapshot cleanup failed; inspect preserved evidence') from cleanup_error


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--auth-source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--native-isolation", action="store_true", help="Test two native workers with routed worktrees")
    parser.add_argument("--plugin-root", type=Path,
                        help="Install a dereferenced Atelier package and exercise its real native hooks")
    parser.add_argument('--marketplace', help='Install from this published GitHub marketplace instead of a local copy; expects dotfiles-agents')
    parser.add_argument('--production-workflow', action='store_true',
                        help='With --plugin-root, exercise manager/builder/reviewer and stop correction')
    args = parser.parse_args()
    if args.hook:
        hook(args.hook)
    elif not args.auth_source or not args.output:
        parser.error("--auth-source and a new --output directory are required")
    elif (args.production_workflow or args.marketplace) and not args.plugin_root:
        parser.error('--production-workflow and --marketplace require --plugin-root (expected manifest version)')
    else:
        run(args.auth_source.expanduser(), args.output.resolve(), args.model,
            args.native_isolation, args.plugin_root, args.production_workflow, args.marketplace)
        print(f"Evidence: {args.output.resolve()}; disposable home and credential copy removed")

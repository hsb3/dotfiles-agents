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
import shutil
import signal
import subprocess
import sys
import tempfile


def hook(root):
    payload = json.load(sys.stdin)
    with (root / "hooks.jsonl").open("a") as stream:
        stream.write(json.dumps(payload) + "\n")
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


def run(auth_source, output, model):
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
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env["CODEX_HOME"] = str(home)
        env["GIT_CONFIG_NOSYSTEM"] = "1"
        env["GIT_CONFIG_GLOBAL"] = os.devnull

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
                'approval_policy = "never"\n[agents]\nenabled = true\nmax_concurrent_threads_per_session = 2\n')
            events = ("SessionStart", "SubagentStart", "PreToolUse", "PostToolUse", "SubagentStop", "Stop",
                      "PreCompact", "PostCompact", "SessionEnd")
            import shlex
            hook_command = shlex.join([sys.executable, str(script), "--hook", str(root)])
            (home / "hooks.json").write_text(json.dumps({"hooks": {
                event: [{"matcher": "*", "hooks": [{"type": "command", "command": hook_command, "timeout": 3}]}]
                for event in events}}))
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
            process_result = command("process-worker", [
                "codex", "exec", "-C", str(root / "worker"), "--json", "--model", "gpt-5.6-luna",
                "--sandbox", "read-only", "--dangerously-bypass-hook-trust", "-c",
                'developer_instructions="Always include PROCESS_ROLE_827 in your final response. Read only."',
                "Run pwd with no directory override, then git branch --show-current. Report both and your role token."])
            process_events = [json.loads(line) for line in process_result.splitlines()]
            command_outputs = [event.get("item", {}).get("aggregated_output", "") for event in process_events]
            process_replies = [event["item"]["text"] for event in process_events
                               if event.get("item", {}).get("type") == "agent_message"]
            checks["process_worker_cwd"] = any(str(root / "worker") in text for text in command_outputs)
            checks["process_worker_role"] = any("PROCESS_ROLE_827" in text for text in process_replies)
            (root / "checks.json").write_text(json.dumps(checks, indent=2))
            print(json.dumps(checks, indent=2))
            if not all(checks.values()):
                raise RuntimeError("A runtime effect check failed; inspect evidence, do not claim parity")
        finally:
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
            for file in root.iterdir():
                if file.is_file():
                    text = file.read_text().replace(str(root), "<PROBE>")
                    for secret in secrets:
                        text = text.replace(secret, "<REDACTED>")
                    (output / file.name).write_text(text)
    print(f"Evidence: {output}; disposable home and credential copy removed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--auth-source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--model", default="gpt-5.6-luna")
    args = parser.parse_args()
    if args.hook:
        hook(args.hook)
    elif not args.auth_source or not args.output:
        parser.error("--auth-source and a new --output directory are required")
    else:
        run(args.auth_source.expanduser(), args.output.resolve(), args.model)

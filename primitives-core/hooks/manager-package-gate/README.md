# manager-package-gate

Refuses to let a `manager` subagent end its turn on a mid-chain progress note. `SubagentStop`,
every agent type: when the stopping agent is a `manager` and its final message does not begin
with one of the two lines the doctrine prescribes, the hook returns `{"decision": "block"}` and
hands the manager an instruction to continue straight to the package.

Its companions are the prose it enforces: `agents/manager.md` ("Proof package upward") and
`skills/delegation/references/manager-brief.md` ("Evidence format"). Those state the rule to the
manager; this one checks it where the turn actually ends.

## Why

Field report, atelier 0.22.0, 2026-09-02. Two `manager` dispatches in one session
each ended their turn on a status line — "Both builders are fixing; waiting on them" — while the
harness reported no live children. Every builder they were waiting on had already returned; a
builder's returned report **is** its reply, so there was nothing left to wait for. The wave sat
idle until the strategist noticed and resumed each manager by hand, after which both produced the
full package normally.

The failure is silent, which is what makes it worth a hook: the completion notification for a
manager that stopped early looks exactly like the notification for a finished wave. Doctrine
already said not to do this. Prose alone did not hold.

## The sentinel

The doctrine prescribes a fixed first line so this check can be mechanical rather than a
judgement about prose quality. A manager's final message begins with either:

| First line | Meaning |
|---|---|
| `## Proof package` | The full package: per-criterion evidence, deferrals, out-of-scope notes, worker log. |
| `## Stopped: <named condition>` | An escalation against one of the brief's stop conditions. |

Leading blank lines and indentation are stripped before the comparison; nothing else about the
message is read. **The hook never inspects the package's contents** and has no opinion on whether
the evidence is any good — that stays the strategist's job, and a gate that tried to score
evidence would be a gate a manager could learn to satisfy with filler.

## Behaviour

| Payload | Result |
|---|---|
| `agent_type` is not a `manager` (last segment after `:` or `/`) | exit 0, no output, no ledger row |
| `stop_hook_active` is true | let through, ledger row `skip` |
| Final message starts with a sentinel | let through, ledger row `pass` |
| Anything else | `{"decision": "block", "reason": ...}`, ledger row `nudge` |
| Malformed stdin, or any internal error | exit 0, no output |

`atelier:manager` and a bare `manager` both match; `code-manager` does not.

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/manager-package-gate plugins/atelier/hooks/manager-package-gate`
3. Add a roster row to `primitives-core.yaml` (id `manager-package-gate`, type `hook`, source
   `primitives-core/hooks/manager-package-gate`, origin `authored`, disposition `qualified`,
   targets `[claude-code]`) — `make ci` reconciles the roster against disk and requires every
   field, `targets` included.
4. Add the `SubagentStop` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "hooks": [
          {
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/manager-package-gate/hook.py\"",
            "statusMessage": "Checking the manager's proof package...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "*"
      }
    ]
  }
}
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | set by Claude Code | Stamped on the ledger row as `project`; falls back to the payload `cwd` |
| `MANAGER_PACKAGE_GATE_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/manager-package-gate.jsonl` | Ledger |

## Design notes

- **One nudge, never a loop.** `stop_hook_active` is true when the stop already fired once
  through a hook, and it is honoured as an unconditional let-through. Claude Code independently
  caps at 8 consecutive blocks, but leaning on that cap would burn eight manager turns on a
  manager that genuinely cannot produce the package. One correction, then the strategist's
  problem — which is the right escalation anyway.
- **Fail-open, always.** Every path exits 0, and an exception can never emit a block: a broken
  gate must not strand a finished subagent inside a turn it cannot leave.
- **The final message is on stdin.** `SubagentStop` carries `last_assistant_message`, so the
  documented `agent_transcript_path` is deliberately not opened — reading it would buy nothing
  and add a failure mode.
- **Only the `manager` path logs.** A `SubagentStop` for any other agent type exits before the
  logger is bound, so the stream stays a record of manager turns rather than of every delegation
  in the marketplace. `subagent-telemetry` already covers the latter.
- **Passes are logged, not only nudges.** This is the opposite of `config-custody`, which logs
  matches only. The ratio of packages to progress notes is the evidence for whether the doctrine
  change or the hook is what holds, and a nudge-only ledger cannot show it.
- **No restart needed to change the ledger path.** Only a change to `hooks.json` requires
  restarting the session.

## Ledger

One row per **manager** `SubagentStop`, appended to the `manager-package-gate` stream.

Ledgers live outside the project, in one partitioned root shared with every other hook in
this plugin (and with the opencode mirror, which writes under its own `<harness>` segment):

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/<harness>/<plugin>/<stream>.jsonl
```

Every row carries an identity envelope — `v`, `plugin`, `harness`, `stream`, `ts`
(ISO-8601 UTC), `project` — so a row stays attributable after the files are concatenated.
The append path is `hooks/_lib/agentlog.py`; no hook writes its own rows.

```json
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"manager-package-gate",
 "ts":"2026-09-02T15:37:08.666Z","project":"/repo/x",
 "session_id":"...","agent_id":"agent-a4e33ee7440ec3a5a","agent_type":"atelier:manager",
 "decision":"nudge"}
```

`decision` is `pass`, `nudge`, or `skip`. A run of `nudge` rows with no following `pass` for the
same `agent_id` means the correction did not take, and the doctrine — not the hook — is what
needs the next change.

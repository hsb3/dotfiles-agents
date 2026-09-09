# Atelier's Codex runtime contract

Measured 2026-09-09 against **codex-cli 0.153.4**, macOS 26.6.2 arm64,
source `2cb732a`, atelier **0.30.4**. This is a porting contract, not a claim
that atelier's current release enforces its Claude guarantees in Codex.
Tracked work: kata **t0a8**, implementation children under **64bm**.

## Evidence and limits

The current desktop conversation loads atelier 0.30.4 skills from the existing
marketplace. That establishes discovery only; no desktop enforcement was tested.
The CLI probes used disposable repositories and `CODEX_HOME`, a private copy of
existing ChatGPT authentication, and a synthetic Claude-format plugin 0.0.1.
Production configuration, plugin installation and hook trust were untouched.
The temporary authentication copy is deleted, not retained with evidence.

| Probe | Observed result |
|---|---|
| Authentication | Isolated CLI returned `AUTH_OK`; this was an authenticated run. |
| Shell denial | `PreToolUse` returned deny; attempted `touch denied-marker` failed and the file stayed absent. |
| Shell and patch rewrite | Replacing `ORIGINAL` with `REWRITTEN` in `updatedInput.command` changed actual file contents. Patch input was `tool_name: apply_patch`, `tool_input.command: <whole patch>`, not a file path. |
| Context | SessionStart token reached the parent final reply; SubagentStart token reached the worker final reply. |
| Worker identity | Worker tool hooks contained `agent_id`, `agent_type`, parent `session_id`, worker transcript path and worker `cwd`. SubagentStop supplied `agent_transcript_path` and `last_assistant_message`. |
| Plugin discovery | Synthetic plugin installed through `.claude-plugin/marketplace.json`; its skill was read. Bare agent type `plugin_probe` was rejected: `unknown agent_type 'plugin_probe'`. Qualified plugin-agent registration remains unverified. |
| Native TOML agent | `$CODEX_HOME/agents/probe_worker.toml` registered. A luna parent/luna worker run delivered its developer-instruction token. A terra parent selected luna for this named role, but the instruction token was absent from that worker's reply. Role instruction parity on that path is **unverified**, not proven by model selection. |
| Native worktree | Hook rewrote a luna spawn with `cwd` pointing at a pre-created worker worktree and `isolation: worktree`. The call succeeded, but actual worker `pwd` and hook `cwd` stayed in the parent repository. These added fields did **not** enforce isolation. |
| Process worker | `codex exec -C <worker worktree> -m gpt-5.6-luna -s read-only -c developer_instructions=...` ran `pwd` and `git branch --show-current` in the intended worktree/branch and returned its developer-instruction token. Filesystem denial outside that tree was not tested. |
| Reply routing | Native worker completion reached its parent; a follow-up produced the requested worker reply. This does not prove Claude's tool exclusions or manager-only dispatch authority. |
| Compaction | App-server `thread/compact/start` produced a completed `contextCompaction` item. No PreCompact/PostCompact payload was captured through that invocation; hook trust/effect was not established there. Manual blocking and automatic-compaction behavior remain **unverified**, not declared unsupported. |

Tool identity varies **within the same CLI version**:

| Parent model | Hook tool name | Observed spawn input |
|---|---|---|
| `gpt-5.6-luna` | `spawn_agent` | `agent_type`, `fork_context`, plaintext `message`; brief rewrite took effect. |
| `gpt-5.6-terra` | `collaborationspawn_agent` | `task_name`, `agent_type`, `fork_turns`, encrypted message string. No message rewrite attempted on this path. |

Do not decrypt that message or claim a matcher alias normalizes the handler's
payload. Both model paths need explicit acceptance before native delegation ships.
Worker records were separate dated rollout JSONL files, not Claude's
`<parent-stem>/subagents/agent-*.meta.json` sidecars. Codex hook `permission_mode`
reported `bypassPermissions` in these runs despite requesting CLI sandbox modes;
these observations do **not** certify filesystem sandbox enforcement.

## Repeatable probe

Requires an installed authenticated Codex CLI and permission to make a small
number of model requests. This is an opt-in local probe, not a network CI gate:

```sh
python3 harness/codex_runtime_probe.py --auth-source ~/.codex/auth.json --output /tmp/atelier-codex-luna --model gpt-5.6-luna
python3 harness/codex_runtime_probe.py --auth-source ~/.codex/auth.json --output /tmp/atelier-codex-terra --model gpt-5.6-terra
```

Each output directory must be new. The probe reviews and runs **only its synthetic
hooks** using the CLI's explicit `--dangerously-bypass-hook-trust` automation flag;
it does not persist trust or bypass approvals/sandbox through that flag. It writes
the CLI version, raw synthetic event payloads, effect checks and negative/conditional
observations, redacting authentication string values. A passed `checks.json` is
proof of those narrow effects only. Read `observations.json` for role, model,
spawn and cwd differences; unknown behavior does not become a green guarantee.

The compaction discovery used `codex app-server --stdio`, initialized a client,
then sent `thread/start`, `turn/start` and `thread/compact/start` with the returned
thread ID. The installed CLI's `app-server generate-json-schema --experimental`
provides the exact request shapes. A trusted manual-compaction probe is still
required before closing the corresponding enforcement criterion in **dq22**.

## Assembly inventory and implementation ownership

This is the observed source contract, not a second packaging catalog. Membership
comes from symlinks under `plugins/atelier/{skills,agents,hooks,commands}` and their
records in `primitives-core.yaml`: **28 primitives**, all currently declaring
`targets: [claude-code]`. `_lib` is support, not a primitive. Re-derive the rows when
membership changes. **Reuse** below means reusable implementation/doctrine with the
stated runtime qualification; it does not certify an unexecuted workflow.

| Primitive | Actual trigger/input → output | Verdict; proof or remaining work | Owner |
|---|---|---|---|
| skill `activation` | Target project → activation file, loader-state report | **Adapt**: parsed settings are not proof of runtime enforcement. Full Codex activation unverified. | dq22 |
| skill `comment-hygiene` | Comments + tracker context → rationale harvest and cleanup | **Reuse** procedure; end-to-end workflow unverified. | x9ma |
| skill `delegation` | Goal/contract → roles, briefs, dispatch and verification | **Adapt** tool names, models, role authority, isolation and reply routing; native probe results above. | x9ma |
| skill `deletion-pass` | Target + contract + green gate → behavior-preserving deletion | **Reuse** procedure; end-to-end workflow unverified. | x9ma |
| skill `handoff` | Session state + destination → body update, stamp last | **Adapt** invocation/hot-context and compaction claims; external destination procedure reusable. | dq22 |
| skill `layer-cycle` | Target/rubric/gate/budget → reviewed implementation | **Reuse** doctrine; companion role dispatch unverified. | x9ma |
| skill `rubric-panel` | Target/rubric/personas → independently derived scores | **Reuse** doctrine; independent role contexts unverified. | x9ma |
| skill `waves` | Tracker work → crews, verified landings, board/handoff | **Adapt** messages, dispatch and hook-backed claims; end-to-end unverified. | x9ma |
| agent `builder` | Owned files + criteria → implementation/evidence; sonnet, edit/shell tools | **Adapt** Markdown registration, tier mapping and actual authority; plugin registration unverified. | x9ma |
| agent `scout` | Read scope → cited findings; haiku, read/shell tools | **Adapt** registration/model/read-only tool contract; native role probe is conditional. | x9ma |
| agent `reviewer` | Claims/diff → independent verdict; opus, read/shell tools | **Adapt** registration/model/context/authority; complete role workflow unverified. | x9ma |
| agent `code-reviewer` | Diff → quality findings; sonnet, read/shell tools | **Adapt** registration/model/authority; complete role workflow unverified. | x9ma |
| agent `manager` | Chain scope → briefs and proof package; opus, Agent/SendMessage | **Adapt** hierarchy, messages, identity and authority; process alternative below. | x9ma |
| command `activate` | Optional project argument → load activation skill | **Adapt** invocation to existing skill; Claude command registration unverified. | dq22 |
| hook `comment-hygiene-gate` | PreToolUse Bash command → diff advisory context | **Adapt** effective command directory; shell name/input proven, real gate output unverified. | x37s |
| hook `config-custody` | Worker edit + protected paths → deny/advisory | **Adapt** all patch paths, moves and effective directory. Current file_path reader misses actual patch command. Denial mechanism proven. | x37s |
| hook `worker-git-scope-guard` | Worker Bash + cwd + topology → deny shared stash/protected writes | **Adapt** effective command directory; identity and shell fields proven, guard-specific cases unverified. | x37s |
| hook `live-worker-git-guard` | Parent Bash + live worker records → deny shared-tree mutation | **Adapt** Claude sidecar discovery returns no Codex workers; runtime ledger required. | x37s |
| hook `worktree-isolation` | PreToolUse literal Agent + subagent_type → updated isolation input | **Unsupported current mechanism**: rewritten cwd/isolation ignored in live native spawn. Replace dispatch mechanism; never report isolated from the rewrite alone. | x37s |
| hook `worker-context` | SubagentStart + activation → developer covenant | **Reuse** event/context mechanism proven; strict guarantees depend on actual safeguards. Process workers require explicit covenant injection. | dq22 |
| hook `manager-package-gate` | SubagentStop manager + final reply → one continuation block | **Adapt** registered manager identity/process completion boundary. Reply fields proven; continuation effect unverified. | dq22 |
| hook `context-watermark` | Prompt/worker tool event + usage tail → nudge/state | **Adapt** Claude usage records and model windows; no Codex usage measurement proven. | dq22 |
| hook `delegation-watermark` | Parent PostToolUse + transcript → count/nudge | **Adapt** Claude tool_use reader; current Codex rollout is not measured. | dq22 |
| hook `subagent-telemetry` | Worker stop/parent stop + sidecars → completion/stall ledger | **Adapt** worker source, usage and completion records; missing sidecars currently drop rows. | dq22 |
| hook `handoff-freshness-guard` | PreCompact manual/auto + stamp → block/notice | **Adapt/verify** event effect; stamp policy reusable, trusted compaction still unverified. | dq22 |
| hook `session-handoff-surfacer` | SessionStart startup/clear + destination → context | **Reuse** context mechanism proven; complete external-handoff invocation unverified. | dq22 |
| hook `branch-activity-surfacer` | SessionStart + branch/process ledger → peer/moved-tip context | **Adapt** owning-process detection recognizes only claude; actual Codex liveness unverified. | dq22 |
| hook `lane-snapshot` | SessionStart → daemon snapshots matching worktrees | **Adapt** default `.claude/worktrees/agent-*`; existing env override can describe chosen topology. Snapshot engine not live-probed. | x37s |

Source entry points are each primitive's `SKILL.md`, agent Markdown, or `hook.py`
under `primitives-core/`; event wiring is `plugins/atelier/hooks/hooks.json`.
Shared seams are `_lib/pending.py` (worker discovery), `_lib/agentlog.py` (currently
hardcodes `claude-code`), and `_lib/model_tiers.py` (Anthropic default windows).
Missing measurement must be reported as unavailable, never an empty worker set.

## Port constraints and candidate mechanisms

**Worker isolation is a hard requirement.** The ignored Claude-style fields above
rule out that particular rewrite, not every native Codex isolation mechanism.
Native worktree/cwd mechanisms require further source/schema research and an actual
binding probe before choosing the dispatch implementation. The process-worker
experiment below is a measured alternative, not an architecture decision.

1. Keep shared source and thin assemblies. Existing catalog distribution works;
   no second repo or universal translation framework is needed.
2. One proven cwd-binding candidate creates the owned git worktree explicitly and launches
   `codex exec -C <worktree>` with an explicit model and rendered role instructions.
   Verify actual cwd, branch, role token and result. This is a **process worker**,
   not a native subagent: its root hooks do not imply `agent_id`, SubagentStart or
   SubagentStop. Supply explicit worker identity and record process lifecycle before
   applying custody, live-worker guards, telemetry or package validation to it.
   Select it only after evaluating the native isolation mechanism; changing a worker
   prompt alone never satisfies the isolation requirement.
3. Generate any Codex role/config material at activation/run time from canonical
   source. Native TOML registration is optional until both supported tool paths
   preserve instructions and authority. Do not silently discard Claude tool lists.
4. Adapt shell/patch guards at their shared input boundary, using actual command
   directories and every edited path. Bind process workers to owned files and
   verify their restrictions; an instruction to stay in a directory is not enforcement.
5. Activation must report each Codex mechanism as verified, advisory, unsupported
   or unverified. Do not print “armed” from parsed settings when events never arrive.
   Trusted compaction and completion blocking need focused probes in **dq22**.
6. Changes land through green PRs into `dev`; **h168** owns sanctioned publishing
   to `main`, installed-version checks and consumer verification. A merged adapter
   is not yet a distributed release. Shared doctrine changes also need the opencode
   parity wave described in [atelier parity](atelier-parity.md).

Official references checked against the installed runtime: [plugin packaging](https://developers.openai.com/plugins/build/plugins),
[hooks](https://learn.chatgpt.com/docs/hooks), and [custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
The runtime observations above take precedence over an assumed translation of those interfaces.

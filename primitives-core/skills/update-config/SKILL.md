---
name: update-config
description: >-
  Configure the Claude Code harness through its settings files — use whenever the request
  is to change how the harness itself behaves: "add a permission rule", "allow/deny a
  command", "set up a hook", "run something automatically whenever X happens", "always do
  Y every time", "add an environment variable", "register an MCP server", "change a
  setting", or "why isn't my setting taking effect". Routes each change to the correct
  settings file by precedence (user vs project vs local vs managed policy), applies the
  narrowest-scope-that-works rule for permissions, and enforces the discipline that
  automated behaviors require a hook — the harness executes hooks, so instructions and
  memory can never satisfy an "always/every time" request. Teaches the ratified hook
  layout: a hook is a directory with a config plus a script file, never an inline shell
  string pasted into settings. Covers JSON-validity and take-effect verification after
  every edit, and when a fresh session is required for a change to apply.
---

# Configure the Claude Code harness

Configuring the harness means editing the JSON settings files that control what the agent is
**allowed to do** (permissions), what runs **automatically** on harness events (hooks), the
**environment** every session sees (env), and which **external tool servers** are wired in
(MCP). The job is always the same shape: put the *right change* in the *right file* at the
*narrowest scope that works*, keep the JSON valid, and verify it actually took effect.

Answer from this skill's reference content, not from a half-remembered key name. Inventing a
settings key that does not exist produces a file the harness silently ignores.

## First — which change is this?

| The request is to… | Read |
|---|---|
| Allow/deny/ask a tool or command; move a rule between scopes; tighten an over-broad rule | `references/permissions.md` |
| Run something **automatically** whenever an event happens ("always", "every time", "whenever X") | `references/hooks.md` |
| Add an environment variable, or a change isn't taking effect | `references/settings-files.md` + `references/verification.md` |
| Register / enable / disable an MCP server | `references/settings-files.md` (MCP section) |
| Pick which file a change belongs in, or see the full settings-key catalog | `references/settings-files.md` |
| Confirm an edit took effect, or debug a setting that "did nothing" | `references/verification.md` |
| See a copy-pasteable, valid example of any of the above | `references/examples/` + `assets/example-hook/` |

## The settings files (precedence, highest wins)

Four files can set the same key; the higher one wins. Full detail and the key catalog are in
`references/settings-files.md` — the summary:

| # | File | Scope | Committed? | Put here |
|---|---|---|---|---|
| 1 | Managed policy (admin-installed, system path) | Organization | n/a | Nothing you author — it overrides everything below |
| 2 | `.claude/settings.local.json` | This project, this machine | **No** (auto-gitignored) | Machine-local + secret-adjacent settings, personal experiments |
| 3 | `.claude/settings.json` | This project, shared | **Yes** | Team-shared project rules, project hooks, project env |
| 4 | `~/.claude/settings.json` | You, all projects | n/a (user home) | Your personal defaults across every project |

(Command-line flags sit between managed policy and the project-local file; they are per-invocation, not a file you edit.)

**Which file** is the first real decision. Narrowest scope that works: a rule only this
project needs goes in the project file, not your user file; anything secret or machine-specific
goes in `settings.local.json` (never in the committed `settings.json`); a preference you want
everywhere goes in your user file.

## Five disciplines (non-negotiable)

1. **Right file, narrowest scope.** Don't grant globally what one project needs, and never
   commit a machine-local or secret-adjacent setting into the shared `settings.json`.
2. **Automation is a hook — always.** "Do Y every time X happens" is a promise only the harness
   can keep, and the harness keeps it by *running a hook*. Writing "always do Y" into
   instructions, a memory file, or CLAUDE.md does **not** make it happen every time — those are
   read as guidance, not executed as a guarantee. If the request contains "always", "every
   time", "whenever", or "automatically", the answer is a hook. See `references/hooks.md`.
3. **Hooks are directories, never inline shell.** A hook is a folder with a script file
   (`hook.py`) plus its config; settings reference the script **by path**. Never paste a
   multi-line shell one-liner into a hook's `command` string — that is unversioned,
   unreviewable, and a quoting minefield. This is the ratified layout; see `references/hooks.md`
   and the working template in `assets/example-hook/`.
4. **Validate the JSON before saving.** A single trailing comma or missing quote makes the
   harness silently ignore the whole file — no error, the config just doesn't apply. Run
   `python3 -m json.tool < FILE` (or `jq . FILE`) and confirm it parses before you're done.
5. **Verify it took effect.** An edit that parses is not an edit that applied. Re-check with the
   relevant command, and start a fresh session when the change requires one (below). See
   `references/verification.md`.

## The universal edit workflow

1. **Classify** the change (permission / hook / env / MCP) with the router table above.
2. **Choose the file** by scope and secrecy (the precedence table). When unsure, prefer the
   narrower, project-local file.
3. **Read the current file** before editing — never blind-write over settings you can't see.
   If the file doesn't exist yet, create it with a single top-level JSON object.
4. **Make the minimal edit** — add/adjust only the needed key. Preserve everything else.
5. **Validate JSON**: `python3 -m json.tool < .claude/settings.json`. Fix any parse error now.
6. **Verify effect** with the matching check (`/permissions`, `/hooks`, `/mcp`, or by
   attempting the gated action).
7. **Restart if required** — env and hook changes need a fresh session (next section).

## When a fresh session is required

| Change | Takes effect |
|---|---|
| Permission allow/deny/ask rule | Next tool call — usually immediately, no restart |
| `env` variable | **Fresh session** — env is read once at startup |
| Hook added / edited / removed | **Fresh session** — the hook set is snapshotted at startup (a deliberate safety measure; a mid-session edit is intentionally not live) |
| MCP server registration | Reconnect with `/mcp`, or a fresh session |
| `model`, `statusLine`, and most other keys | Next session; some apply live |

When in doubt, start a fresh session and re-verify — it is the one reliably clean state.

## Failure modes (the ones that bite silently)

| Symptom | Cause | Fix |
|---|---|---|
| "My setting does nothing" | JSON syntax error → whole file silently ignored | Validate with `json.tool`/`jq` every save |
| Agent still can't (or can too easily) do a thing | Rule in the wrong scope, or a higher file overrides it | Check precedence; move the rule to the right file |
| Over-permissioned | Rule too broad (e.g. bare `Bash` or `Bash(*)`) | Narrowest specifier that works (`Bash(npm run test:*)`) |
| Hook "installed" but never fires | Wrong event/matcher, or script not executable when invoked directly | Match the event to the trigger; `chmod +x` or invoke via `python3` (see hooks ref) |
| Secret leaked in git | Machine-local/secret setting written to committed `settings.json` | Move it to `.claude/settings.local.json` |
| "Always do Y" ignored intermittently | Encoded as an instruction/memory, not a hook | Convert to a hook |

## What this skill does NOT do

- **No settings implementation** — it configures Claude Code's own settings files; it does not
  build the harness.
- **No hook logic authoring beyond the layout** — it teaches the ratified hook *layout* and
  contract; the behavior a specific hook implements is that hook's own concern.
- **No secret storage** — credentials never go in a committed settings file or a hook body; use
  the machine-local file and environment references (`${VAR}`), and keep the real value out of
  the repo.

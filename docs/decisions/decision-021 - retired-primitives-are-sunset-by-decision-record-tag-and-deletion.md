---
id: decision-021
title: retired primitives are sunset by decision record, tag, and deletion (applied to kaneo)
date: '2026-09-08'
status: accepted
---
**Amended 2026-09-08:** After the Kaneo retirement, PR #509 placed task-authoring
in mise-en-place and PR #515 removed its remaining solo-skills membership. The statement
below that solo-skills is its only home describes the retirement baseline. Decision-024
separately establishes board-desk as its new topical home; it is not the #509/#515 move.

**Implementation note 2026-09-10:** Decision-024 makes board-desk the topical home
while retaining mise-en-place's task-authoring membership for its planning-desk dependency.
The shared source is unchanged; enabling both plugins can list the skill twice.

## Context

This repo has retired shipped units before — the vendored pptx base (decision-018) and
`dev-focus` (decision-019) — and each time the shape was argued from scratch. The default
when nobody argues is to leave the code in the tree "in case there is something to learn from
it", and that default is the expensive one: an unshipped primitive in `primitives-core/` still
pays the roster guard, README currency, its tests, and every drift gate for something nobody
installs. The README-currency backfill card (`wn8m`) already listed the kaneo skill and plugin
as stale on the day this record was written. That is the cost arriving.

The trigger is the `kaneo` plugin (marketplace version 0.13.3: the skill, the `kaneo-manager`
agent, three hooks, the MCP server definition). Its tracker was retired here on 2026-09-02
(decision-014), the owner retired Kaneo itself on 2026-09-08, and the plugin's last five open
cards were closed wontfix the same day — every one a fix for Kaneo's own shortcomings, nothing
to port. The reluctance to delete it was specific: the plugin encoded patterns the kata plugin
does not have yet, and plain git history is where lessons go to be forgotten.

## Decision

Owner ruling, 2026-09-08. A retired primitive or plugin is sunset in four moves, in order:

1. **A decision record carries the lessons, not the tree.** Template: decision-019, plus one
   section it lacks — **Patterns to carry forward** — one entry per unit, each naming its
   destination: a card on another board, a generic primitive here, or "dropped, because ...".
   Extraction happens here, before anything is deleted.
2. **Tag the last shipping commit** `retired/<id>@<version>` and push the tag, so the code is
   one `git show` away with no archaeology. `dev-legacy` is the same idea as a branch. The tag
   goes on `dev`'s last commit that carries the unit, not on a PR branch that squash-merge will
   orphan.
3. **Delete in one commit with a removal verb**, which `scripts/check_removals.py` already
   demands: roster rows, the assembly, the marketplace entry, tests, and any adapter files in
   other skills that exist only for the retired tool.
4. **Never keep unshipped code in `primitives-core/`.** A `demoted` roster row is not a
   sunset state; it is the expensive default with a label on it.

## Applied to kaneo

- **Tag:** `retired/kaneo@0.13.3` on `315035c`, the last `dev` commit that ships the plugin.
- **Removed:** roster rows `kaneo`, `kaneo-manager`, `kaneo-mcp-policy`, `kaneo-bash-tripwire`,
  `kaneo-preflight`, `kaneo-server`; `primitives-core/skills/kaneo/`,
  `primitives-core/agents/kaneo-manager.md`, the three hook directories,
  `primitives-core/mcp/kaneo.json`; the `plugins/kaneo/` assembly and its marketplace entry;
  the Kaneo adapters that existed only for it — `board-triage/references/adapters/kaneo.md`,
  `board-triage/scripts/kaneo_board.py`, `waves/references/tracker-kaneo.md`; and the tests
  that tested only those bytes.
- **Kept:** `task-authoring` — tracker-agnostic doctrine, dual-homed in kaneo and solo-skills;
  solo-skills is now its only home. Historical mentions of Kaneo in AGENTS.md, `flow.yaml`,
  decision-011 and decision-014, and the opaque `Kaneo board task DFA-233` fixture string in
  atelier's handoff tests stay as written: they describe what happened, not what ships.

## Patterns to carry forward

| unit | pattern | destination |
|---|---|---|
| `kaneo-mcp-policy` | Claim authority stays in the root session. A subagent calling a claim-authority tool is denied; comments and creates are allowed and stamped. The allowlist is the authority, not the calling agent's own `tools:` grant, so a misconfigured agent fails closed. | kata-oversight `10tb`. The kata identity hook solves attribution; it does not stop a builder from closing its own card. |
| `kaneo-preflight` | Say loudly at session start that the board tools are not there, and which of the invisible causes it is — or that they work under the wrong identity. `startup` and `clear` only, silent when reachable. A skill that says "the board holds the work" while the board is silently absent produces a `TODO.md` within the hour. | kata-oversight `hf11`: `kata_doctor.py`'s checks as a SessionStart hook, so the rhythm's step 1 stops depending on memory. |
| `kaneo-bash-tripwire` | Deny a subagent's Bash that reaches the board host directly, with the ceiling stated in the first paragraph: a tripwire, not containment, because a string guard cannot stop a script the agent writes first. | kata-oversight `p8me`, filed as a decision, not an ask: for kata the sanctioned Bash path is the CLI itself, so the pattern may not be worth a hook. |
| `skills/kaneo/references/access-model.md` | The honest enforcement ceiling, written down: sound for MCP calls by agents whose only network access is MCP; the only sound configuration for an untrusted level is no Bash, which code-writing workers cannot have. Do not describe a plugin as containment when it is not. | Prose worth reusing verbatim in whichever hook lands from `10tb`. Otherwise dropped with the plugin. |
| the claim ritual (assign, then re-read) | Where a tracker has no atomic claim, assign-then-re-read is the entire race protection, and it belongs to one level. | Dropped: kata has `kata claim`. Recorded here so nobody rebuilds it for a tracker that does not need it. |
| `kaneo-manager` agent | A reference L2 agent whose `tools:` list *is* the append-only allowlist. | Dropped: harness-enforced tool lists are the general mechanism and need no kaneo-shaped example. |
| the kaneo skill prose | Claim ritual, levels, decision convention, handoff mechanics. | Dropped: every part of it that was not Kaneo-specific already lives in `task-authoring`, `handoff`, and `board-triage`, which is the "mostly mechanics -> keep the tool skill" resolution in `docs/overlap-eval.md` running to its end. |

## Consequences

- The marketplace loses a plugin. Anyone with `kaneo@dotfiles-agents` installed keeps their
  cached copy and stops receiving updates; the code is at `retired/kaneo@0.13.3`.
- `solo-skills`, `code-desk`, and `atelier` each ship changed bytes (a lost dual home, a lost
  adapter, a lost tracker reference) and bump per `check_version_bump.py`. The removal is
  declared in the commit message per `check_removals.py`; there is no removals inventory.
- `board-triage` and `waves` keep exactly the backends someone still uses: GitHub Projects and
  kata. The adapter shape was proved by having had three, and losing one does not un-prove it.
- The next retirement follows this record instead of re-deciding. If a retirement needs a
  fifth move, amend this record rather than the next one's.

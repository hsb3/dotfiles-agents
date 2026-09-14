---
id: "decision-010"
title: Commands become a fourth primitive type
date: '2026-08-10 05:35'
status: accepted
---
## Context

Until now the roster carried three kinds of thing an agent runs — `skill`, `agent`, `hook` —
plus `mcp`. `TYPES` in `scripts/check_roster.py` encoded that as a closed set, and nothing in
`primitives-core/` or any assembly was a command. Claude Code has supported plugin commands the
whole time; this repo simply never shipped one.

TASK-058 asked for an easier way to set up `.claude/atelier.local.md`. The `activation` skill
shipped first (PR #295). The open half was whether a command should ship beside it, and the
argument against was cost: a command is the first of its kind, so it reshapes the roster schema
and lands in `check_roster.py`, `gen_opencode.py`, `check_symlinks.py`, and `flow.yaml` before it
does anything useful. Skills are already reachable as a slash invocation, so on the operator axis
alone the command buys little.

The owner overruled that on a different axis: **"the agent can run it on my behalf as well."**
A skill is knowledge a model reaches for; a command is an instruction an operator or an agent
issues. Wanting the setup performed unattended, on request, is a command-shaped want, and no
amount of skill polish makes a skill the thing you hand to an agent to *do*.

## Decision

`command` is a fourth primitive type, first-class in the roster and in the gates. The cost of the
schema change was raised before the ruling and accepted by the owner explicitly and twice.

The first command wraps the `activation` skill and stays thin. **The procedure lives in the skill
and is never duplicated into the command** — the command loads the skill and drives it. That
boundary is what keeps a second surface from becoming a second source of truth, which is the
failure this whole card exists to fix (the shipped README had already drifted from the schema it
copied).

## Consequences

- The roster type enum is open to a fourth value, and every gate that hardcoded the three-plus-mcp
  set is now a place a fifth type would have to be added. That is the standing cost of the
  decision, not a defect.
- `gen_opencode.py` must take a position on commands, since opencode has them too. Translating or
  excluding are both acceptable; the reason has to live in the code, because an unexplained
  exclusion is how the opencode lane became a silent subset in the first place (TASK-033).
- A command and a skill can share a plugin, which raises a naming question the docs do not answer.
  Settled by probe rather than by reasoning, per the house rule.
- TASK-058's last open criterion is answered: whether a command primitive ships is now a recorded
  ruling rather than a decision implied by its absence.

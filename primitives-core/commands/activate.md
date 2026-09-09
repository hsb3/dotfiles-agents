---
description: Arm atelier in this project — create the selected per-project activation file if it is missing, then report per key what the hooks actually resolved, including any key that is present but silently doing nothing.
argument-hint: "[project dir]"
allowed-tools: Skill, Bash, Read
---

Load the `atelier:activation` skill and drive it. **The procedure lives in the skill.** Read
it there and follow it; do not restate it here and do not re-derive it from memory.

<!-- harness:claude-code -->
Target project: `$1` if one was given, otherwise the current project root. Its activation
file is `.claude/atelier.local.md` in Claude Code. Codex uses the activation skill
directly with `.codex/atelier.local.md` and legacy fallback; no native slash command is registered.
<!-- /harness -->

## What to do

1. Load `atelier:activation`.
2. Run the skill's `create` without `--force`. It safely migrates an existing identical
   policy to its canonical location, and refuses a divergent copy. Use `--force` only
   when the person asked for a reset in this same turn.
3. Run the skill's `check`.
4. Report the result in the form below.

## How to report

Do not paste the raw `check` output. Translate it. `check` labels every key with a state and
prints a one-line summary; group the keys under the states **it** reports, using its labels,
and do not add, rename, or merge states of your own. Per key, a few words on what it is doing
or why it is not.

Give the reader's attention to any key `check` calls **inert** — set to something no hook
recognises. That is the failure this exists to expose: nothing errors, nothing warns, and it
reads as configured while being off. For each one say plainly which setting it is, what was
written, what the hook accepts instead, that it is having no effect, and any other key whose
effect depends on it. `check` exits nonzero when it finds one, so treat a nonzero exit as a
finding to report rather than a command that failed. Say what would need to change, then stop
— do not edit the activation file to fix it unless you are asked to.

Close by stating which parts of atelier are enforcing in this project right now and which are
not. Do not reduce that to a single yes or no: armed and inert keys routinely coexist, and a
blanket "atelier is not enforcing anything" is false whenever any key is armed. If the file
was already present and nothing changed, say so in one line and stop.

<!-- harness:claude-code -->
In Codex, invoke the activation skill directly. Run its `codex-setup` and
`check --harness codex` steps, then verify the reviewed hooks in native `/hooks`.
Report parsed settings and runtime trust separately; do not claim enforcement from
the activation file alone.
<!-- /harness -->

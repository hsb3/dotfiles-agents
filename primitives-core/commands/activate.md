---
description: Arm atelier in this project — create .claude/atelier.local.md if it is missing, then report per key what the hooks actually resolved, including any key that is present but silently doing nothing.
argument-hint: "[project dir]"
allowed-tools: Skill, Bash, Read
---

Load the `atelier:activation` skill and drive it. **The procedure lives in the skill.** Read
it there and follow it; do not restate it here and do not re-derive it from memory.

Target project: `$1` if one was given, otherwise the current project root.

## What to do

1. Load `atelier:activation`.
2. If the target's `.claude/atelier.local.md` does **not** exist, run the skill's `create`.
   If it already exists, leave it as it is — **never pass `--force`** unless the person asked
   for a reset in this same turn. The file holds hand-tuned local settings, it is gitignored,
   and overwriting it destroys the only copy.
3. Run the skill's `check`.
4. Report the result in the form below.

## How to report

Do not paste the raw `check` output. Translate it. `check` sorts every key into three states,
and only the third one needs the reader's attention:

- **armed** — the key is set and the hook that reads it agrees. Name the key and, in a few
  words, what it is now doing.
- **not configured** — absent, which is off by design. Say so once, as a list of names. No
  alarm; this is the normal state for a key nobody set.
- **present but silently inert** — set to something no hook recognises. This is the failure
  the skill exists to expose: nothing errors, nothing warns, and it reads as configured while
  being off. For each one, say plainly which setting it is, what was written, what the hook
  accepts instead, and that it is currently having no effect at all.

`check` exits nonzero when it finds an inert key, so treat a nonzero exit as a finding to
report rather than a command that failed. Say what would need to change, then stop — do not
edit the activation file to fix an inert key unless you are asked to.

Close with one line stating whether atelier is enforcing anything in this project right now.
If it was already armed and nothing changed, say that in one line and stop.

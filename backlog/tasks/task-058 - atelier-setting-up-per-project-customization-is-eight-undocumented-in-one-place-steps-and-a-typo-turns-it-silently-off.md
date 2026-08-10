---
id: TASK-058
title: >-
  atelier: setting up per-project customization is eight
  undocumented-in-one-place steps and a typo turns it silently off
status: To Do
assignee: []
created_date: '2026-08-10 02:46'
updated_date: '2026-08-10 02:53'
labels:
  - primitives
milestone: m-2
dependencies: []
priority: high
type: feature
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Turning on atelier local customization in a fresh project today means hand-authoring `.claude/atelier.local.md`, editing settings.json, adding a gitignore line, and knowing two things written only in this repo memory. Nothing scaffolds the file and nothing validates it — `rg -l atelier.local` returns docs, hook readers, and backlog cards, no generator. **Owner, 2026-08-09: the current setup is not working.** Take that as the problem statement, not the ergonomics complaint it sounds like.

The part that bites is not the step count, it is the failure mode. The hooks treat an absent file, an unrecognized value, and an unparseable file identically as off (`plugins/atelier/README.md` enforce table). So a typo in the frontmatter reads exactly like a deliberate decision not to enforce, and the operator gets no signal at all — they believe custody is armed and it is not. That is the standing pattern where a discovered silent failure becomes a machine-checkable check rather than a doc note.

Two smaller defects in the same surface, worth folding in because they are the same file:

- The schema is documented twice and the copies have drifted. `primitives-core/skills/delegation/references/activation.md` documents five keys; the shipped `plugins/atelier/README.md` block and its key table both omit `handoff:`. A consumer copying the README loses a key that exists.
- `effort:` is the only key with no machine reader. Every other key is parsed by a hook per call; `effort:` is honored only if the model remembers to open the file (`primitives-core/skills/delegation/SKILL.md`). That asymmetry is undocumented, so it reads as equally reliable and is not.

## Shape — owner ruling 2026-08-09

Both surfaces ship: **a command and a skill.** The command is the operator one-shot; the skill is what an agent loads when it needs to reason about activation mid-task. They must not duplicate the procedure between them.

**The validation is executable, not prose.** Ship scripts in the skill resources that an agent runs to check an activation file, or a mini CLI — the shape is open, the requirement is that checking validity is a command an agent invokes, never a checklist it is asked to apply by reading. A prose boundary has already failed once in this estate on exactly this reasoning.

**One parser, not a third.** Each hook currently carries its own `_parse_frontmatter`; a validator that adds a third copy can disagree with the two that decide behavior, which is worse than no validator. Make the checker read the file through the same code the hooks do. This is the same consolidation TASK-057 wants for hook logging — if both land, they should not invent two different notions of a shared hook helper.

Standing invariants: hooks and any shipped script stay stdlib-only and zero-install; anything under `primitives-core/` is self-authored; the command and skill are new primitives with roster entries.

Open question the worker should answer first, not assume: which project the owner saw fail, and whether it failed at authoring, at parsing, or at a hook never firing. The three have different fixes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An operator can create a valid `.claude/atelier.local.md` in a fresh project without hand-copying a schema block from a README
- [ ] #2 A malformed or misspelled activation file produces a visible signal rather than silently reading as off
- [ ] #3 The schema exists in one authoritative place; any second copy is generated from it or is a pointer, and the `handoff:` key appears wherever the schema is shown
- [ ] #4 The docs state which keys are machine-enforced and which depend on the model reading them
- [ ] #5 The full setup path for a fresh project is written down in one place, including the steps currently recorded only in repo memory
- [ ] #6 A test fails if a documented key is unparseable by the code that reads it, or if a schema copy drifts from the authoritative one
- [ ] #7 Checking an activation file for validity is a command an agent can run, shipped in the skill resources or as a mini CLI, not a procedure written in prose for the agent to apply
- [ ] #8 Both a command and a skill ship, the command for the operator one-shot and the skill for mid-task reasoning, with the procedure living in exactly one of them
- [ ] #9 The checker and the hooks read the activation file through the same parser, so a file the checker passes cannot be ignored by a hook
- [ ] #10 The reported non-working setup is reproduced and its failure point named — authoring, parsing, or a hook that never fired — before the fix is designed
- [ ] #11 Any new script is stdlib-only and runs with zero install
<!-- AC:END -->

---
id: TASK-058
title: >-
  atelier: setting up per-project customization is eight
  undocumented-in-one-place steps and a typo turns it silently off
status: To Do
assignee: []
created_date: '2026-08-10 02:46'
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
Turning on atelier local customization in a fresh project today means hand-authoring `.claude/atelier.local.md`, editing settings.json, adding a gitignore line, and knowing two things written only in this repo memory. Nothing scaffolds the file and nothing validates it — `rg -l atelier.local` returns docs, hook readers, and backlog cards, no generator.

The part that bites is not the step count, it is the failure mode. The hooks treat an absent file, an unrecognized value, and an unparseable file identically as off (`plugins/atelier/README.md` enforce table). So a typo in the frontmatter reads exactly like a deliberate decision not to enforce, and the operator gets no signal at all — they believe custody is armed and it is not. That is the standing pattern where a discovered silent failure becomes a machine-checkable check rather than a doc note.

Two smaller defects in the same surface, worth folding in because they are the same file:

- The schema is documented twice and the copies have drifted. `primitives-core/skills/delegation/references/activation.md` documents five keys; the shipped `plugins/atelier/README.md` block and its key table both omit `handoff:`. A consumer copying the README loses a key that exists.
- `effort:` is the only key with no machine reader. Every other key is parsed by a hook per call; `effort:` is honored only if the model remembers to open the file (`primitives-core/skills/delegation/SKILL.md`). That asymmetry is undocumented, so it reads as equally reliable and is not.

Steer, not a plan: the user framing was "maybe a new skill". A skill is the wrong surface — this is a one-shot the operator invokes, not knowledge the model needs mid-task, so prefer a command over a skill unless the work proves otherwise. And the hooks already carry a frontmatter parser each; validation should read the file the same way the hooks do rather than growing a third parser that can disagree with them.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An operator can create a valid `.claude/atelier.local.md` in a fresh project without hand-copying a schema block from a README
- [ ] #2 A malformed or misspelled activation file produces a visible signal rather than silently reading as off
- [ ] #3 Validation resolves the file exactly as the hooks do, so a file that validates cannot then be ignored by a hook
- [ ] #4 The schema exists in one authoritative place; any second copy is generated from it or is a pointer, and the `handoff:` key appears wherever the schema is shown
- [ ] #5 The docs state which keys are machine-enforced and which depend on the model reading them
- [ ] #6 The full setup path for a fresh project is written down in one place, including the steps currently recorded only in repo memory
- [ ] #7 A test fails if a documented key is unparseable by the code that reads it, or if a schema copy drifts from the authoritative one
<!-- AC:END -->

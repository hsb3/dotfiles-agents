---
id: TASK-058
title: >-
  atelier: setting up per-project customization is eight
  undocumented-in-one-place steps and a typo turns it silently off
status: To Do
assignee: []
created_date: '2026-08-10 02:46'
updated_date: '2026-08-10 05:30'
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
- [x] #1 An operator can create a valid `.claude/atelier.local.md` in a fresh project without hand-copying a schema block from a README
- [x] #2 A malformed or misspelled activation file produces a visible signal rather than silently reading as off
- [x] #3 The schema exists in one authoritative place; any second copy is generated from it or is a pointer, and the `handoff:` key appears wherever the schema is shown
- [x] #4 The docs state which keys are machine-enforced and which depend on the model reading them
- [x] #5 The full setup path for a fresh project is written down in one place, including the steps currently recorded only in repo memory
- [x] #6 A test fails if a documented key is unparseable by the code that reads it, or if a schema copy drifts from the authoritative one
- [x] #7 Checking an activation file for validity is a command an agent can run, shipped in the skill resources or as a mini CLI, not a procedure written in prose for the agent to apply
- [x] #8 The checker and the hooks read the activation file through the same parser, so a file the checker passes cannot be ignored by a hook
- [x] #9 Any new script is stdlib-only and runs with zero install
- [x] #10 The skill ships and is reachable by the operator as a slash invocation, carrying the procedure and the authoritative key reference
- [ ] #11 Whether a separate command primitive also ships is recorded as an owner ruling, not left implied by its absence
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Shipped in PR #295, merged to dev as a752839. `primitives-core/skills/activation/` — SKILL.md, examples/atelier.local.md, scripts/activation.py — symlinked into atelier only; roster entry, atelier version 0.11.1 to 0.12.0 in both manifests, 26 stdlib tests. make ci exit 0 (464 tests), check_version_bump.py exit 0, both re-run independently of the build. CI green on both required checks.

`check` adds no sixth parser: it importlib-loads all five hook modules and calls each hook own loader, toggling sys.dont_write_bytecode so auditing an installed plugin leaves no __pycache__. Path resolution works in both layouts because they share the relative shape ../../../hooks/<name>/hook.py, verified in the dev tree, through the symlink, and against a dereferenced copy.

Two ship-blockers were caught by adversarial review AFTER the builders self-reported clean, both fixed before commit. (1) The documented invocation `python3 scripts/activation.py check` could not work — bash runs from the project dir; now the house ${CLAUDE_PLUGIN_ROOT} form. (2) `create` left a project WORSE off: the example set handoff: to a path absent in a fresh project, and the hooks deliberately do not fall back, so create-and-stop silently disabled handoff surfacing — the exact failure class this skill exists to expose, nearly shipped as the default. That key now ships commented out with the reason inline.

Two corrections to the brief premises, both from hook source. handoff: naming a nonexistent in-root file is NOT inert — it is authoritative and suppresses the standard search, so check reports it armed-with-warning. And `protected:` cannot carry a trailing comment: config-custody only enters list-collecting mode when the text after the colon is empty, so `protected:  # patterns` silently yields zero patterns. Both are now documented in the example and pinned by tests.

Spun out: TASK-059, the membership gate reads a proxy for hook coupling rather than the property.

AC 11 is the only one open — whether a command primitive also ships is the owner ruling, unmade. This repo has no command type; adding one reshapes the roster schema plus the roster guard, the symlink guard, and the opencode generator.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-08-10 04:21
---
Owner ruling 2026-08-09/10, two parts.

DIAGNOSIS, settled — do not re-litigate. The failure point is AUTHORING and DISCOVERABILITY, not parsing and not a hook that never fires: "there is no easy way to create a local override file and nothing documents all the different things I can set in it. An example that ships, and a command and/or skill to do it right, is what I need." AC on reproducing the failure is therefore removed as answered.

SHAPE. Skill plus executable validation, confirmed. The command half hit a structural finding that changes its cost: this repo ships NO commands at all — no primitives-core/commands/, no plugins/*/commands/, and the roster type enum is skill|agent|mcp|hook. A command would be the first of its kind, reshaping the roster schema plus the roster guard, the symlink guard, and the opencode generator. Skills are already reachable as a slash invocation, so the command buys an affordance the skill provides. Built the skill under the ruling's "and/or"; whether a command primitive type is worth introducing is a separate owner call and is now its own criterion rather than an assumption.

DERIVED KEY SET, from the readers rather than the docs: exactly five — enforce, protected, isolate, handoff (all hook-read), and effort (prose-only, no hook parses it). references/activation.md documents all five correctly and is authoritative; plugins/atelier/README.md is the drifted copy, missing handoff from both its fenced example and its key table.

VALIDATION DESIGN. Five hand-rolled parsers exist, one per hook, standalone by ADR 0017 — so the checker must not add a sixth and must not refactor them into a shared module. It importlib-loads each hook and calls that hook's own loader, which is ground truth and cannot drift. The three states it has to separate are not configured / armed / present but silently inert, because those are exactly the three an operator cannot tell apart today.
---
<!-- COMMENTS:END -->

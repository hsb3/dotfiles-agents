## What

Encode a bundle-composition principle and apply it, starting with comms:

1. **Principle (as an ADR extending 0016):** a plugin bundle covers one focused area; any
   component that is useful outside that area must be installable without the bundle
   (standalone plugin or dual-homed), and its convention touchpoints (output dirs, handoff
   file, board/registry) must be parameterized or auto-detected, never hardwired.
2. **First application — comms:** make the comms skill installable without code-desk, with
   its code-desk touchpoints (`_meta/briefings/` output home, handoff file location,
   board/registry pointers) resolved per-project instead of assumed.
3. **Audit the rest of code-desk** against the principle and record a disposition per skill
   (stays bundle-only / dual-home / standalone) — candidates on the same footing as comms:
   pptx-themes, dev-focus, readme-value-and-proof.

## Why

The ADR 0016 lineup (`primitives-core.yaml:17-27`) folded the executive-desk bundle into
code-desk, so code-desk now mixes the repo-standards/task-management convention family
(planning-desk, board-triage, repo-meta-structure, repo-compliance-audit,
mise-en-place-scaffold, project-memory) with skills that have nothing intrinsic to those
conventions (comms, pptx-themes, dev-focus, readme-value-and-proof).

Motivating case: `~/developer/tmp-learn-pocketbase` adopted Backlog.md for task management
instead of the code-desk conventions. Enabling code-desk there would import the whole
convention family it deliberately replaced — so it stays off, and the project loses comms,
which is about producing communication deliverables, not managing tasks. The coupling is
shallow: comms's own standard already says its per-project parameters are "auto-detect,
never hard-code" (`primitives-core/skills/comms/references/comm-package-standard.md:31`);
only the `_meta/briefings/` output home and the handoff-file assumption
(`skills/comms/SKILL.md:10,36-37,62-63`) are inherited convention.

The lineup already contains both shapes the principle needs: focused bundles (diagrams,
obsidian-toolkit) and standalone-only skills (github-project-board, private-fork,
opencode-expertise); the roster's `plugins:` field is a list, so dual-homing is a roster
edit, not new machinery.

**Open owner decisions** (this issue is the approval vehicle — reshaping the roster needs
owner sign-off per CLAUDE.md):

1. comms: dual-home (`plugins: [code-desk, comms]`-style) vs move to standalone-only.
   Recommend dual-home — existing code-desk consumers keep it with no migration.
2. Which of pptx-themes / dev-focus / readme-value-and-proof get the same treatment now vs
   recorded as bundle-only with rationale.

## Done when

- [ ] An ADR records the bundle-focus principle and the per-skill dispositions, marked as
      extending ADR 0016.
- [ ] comms is installable in a project without enabling code-desk (verifiable:
      `claude plugin enable <comms-home>@dotfiles-agents` in a repo with code-desk off
      loads the skill).
- [ ] comms resolves its output home and handoff file per-project (documented
      auto-detect + override), and works in a repo with no `_meta/` directory.
- [ ] Every code-desk skill has a recorded disposition against the principle (in the ADR).
- [ ] `make ci` green; `dist/` regenerated via `make build`; roster entries carry the full
      schema.

## Context

- Sibling issue: #220 (foreman-kit configurable handoff-file location; same motivating project;
  comms's handoff-file touchpoint should reuse that mechanism where possible).
- ADR 0016 (`docs/decisions/0016-marketplace-lineup-recomposition.md`) — the lineup this
  amends.
- Roster comment block (`primitives-core.yaml:17-27`) must be updated in the same change
  that re-homes any skill.

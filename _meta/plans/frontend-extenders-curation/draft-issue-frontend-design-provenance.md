# fix: record upstream + pinned ref for the frontend-design external (and typescript-lsp)

> **Draft — staged, not filed.** Follow-on from #48 curation-plan.md (ruling 48.5). Owner approves before filing.

## Problem

The `frontend-design` external is tracked in `externals.yaml:164` but with `upstream: null`,
`ref: null`, `provides: ""` — a provenance gap against the externals convention (`externals.yaml:11`
requires upstream + a pinned ref for reproducible clones). It is a real Anthropic-official plugin
(cached at `~/.claude/plugins/cache/claude-plugins-official/frontend-design/`, `plugin.json` names
Anthropic, one `frontend-design` skill). It is the #48 core survivor of the name collision with
webapp-designer's internal skill (overlap B row 5), so its record must be clean.

`typescript-lsp` (externals.yaml:248) has the **same** null upstream/ref/empty provides — fold its
fix in as a second row (it is out of frontend curation scope but shares the gap).

## Deliverables

- Set `upstream` (the anthropics/claude-plugins-official source) and a pinned `ref` for
  `frontend-design`; populate `provides` (the single visual-design skill).
- Same for `typescript-lsp`.
- No name change here — the `frontend-design` collision is resolved by the curation naming pass
  (webapp-designer's internal is dropped, not renamed).

## Acceptance

- [ ] `rg -A4 "id: frontend-design" externals.yaml` shows non-null upstream + ref + non-empty provides.
- [ ] Same for `typescript-lsp`.
- [ ] `yamllint externals.yaml` passes.

## Gates

- yamllint lane (externals.yaml edit). No roster/targets gate (externals are cloned at build, not a primitive).

## Out of scope

- Enabling either plugin (both sit dormant in cache; enable is a separate decision).
- Renaming or dropping webapp-designer's internal frontend-design (that is the decomposition follow-on).

# Task-9 design pass: Recompose lineup — focused bundles + the multi-homing map

_Owner-ruled 2026-08-04 (in principle); full ratification needed before build (task-9 AC#1)._

## Background

ADR 0017 made the symlink mechanism free: a standalone skill is now just a directory + marketplace entry, same cost as membership in a bundle. This means the decision to bundle or standalone is a pure composition question, not an implementation constraint. Task-9 decides which direction each skill takes.

**code-desk today** carries 10 skills (board-triage, comms, dev-focus, mise-en-place-scaffold, planning-desk, pptx-themes, project-memory, readme-value-and-proof, repo-compliance-audit, repo-meta-structure) under one plugin. **The question**: which of those 10 are genuinely coupled, and which are independent enough to live standalone with optional code-desk co-install?

---

## ADR bundle-composition extension

**Principle:** A bundle coheres when every member needs another, OR when the bundle solves one end-user workflow atomically.

For code-desk: the 10 skills fall into three groups:

### Group 1: Desk ecosystem (tightly coupled, stay bundled)
- **board-triage** — surfaces the project's issue triage; part of the board loop
- **planning-desk** — stages plans; couples to board-triage (reads issue context)
- **repo-compliance-audit** — audit queries; uses planning-desk staging
- **rubric-panel** — part of layer-cycle; used by other skills

**Disposition: Stay in code-desk.** These form a coherent audit/planning surface.

### Group 2: Reusable helpers (independent, can dual-home for convenience)
- **pptx-themes** — PowerPoint authoring; orthogonal to the desk
- **readme-value-and-proof** — doc authoring; orthogonal to the desk  
- **repo-meta-structure** — metadata skill; stands alone

**Disposition: Remain in code-desk AS CONVENIENCE, but also install as standalones** for projects that want them without the full desk. Dual-home: appears in both code-desk/plugins/repo-meta-structure/skills/ (via symlink) and plugins/repo-meta-structure/skills/ (standalone).

### Group 3: Comms variants (split decision)
- **comms** — the general-purpose comms skill; requires local-mcp
- **project-memory** — project-scoped memory layer; requires dotfiles env
- **mise-en-place-scaffold** — new-project template; standalone-friendly

**Disposition:**
- **comms**: Stays in code-desk; too coupled to the desk ecosystem
- **project-memory**: Stays in code-desk; requires dotfiles env (project-local)
- **mise-en-place-scaffold**: Can dual-home (reusable, but comms-family convenient)

---

## The multi-homing mechanism (ADR 0017 + task-9 refinement)

Dual-homing means the skill lives in two plugin assemblies. Technically: the skill is sourced from primitives-core/, and **two different plugins/ directories symlink to the same source**.

Example (repo-meta-structure):
```
plugins/repo-meta-structure/skills/repo-meta-structure → ../../primitives-core/skills/repo-meta-structure
plugins/code-desk/skills/repo-meta-structure → ../../primitives-core/skills/repo-meta-structure
```

Both symlinks point to the same source; a session with either plugin (or both) loaded has the skill available exactly once. No duplication, no copy.

**Governance**: A skill that dual-homes must be:
1. Standalone-installable (works without code-desk or its dependencies)
2. Composable without coupling (the skill's README explains its dependencies + use cases independently)
3. Upsell-transparent (code-desk's README documents the dual-home and the standalone scope)

---

## Accepted ruling (summary for owner sign-off)

| Skill | Stay in code-desk? | New standalone? | Dual-home? | Notes |
|-------|---|---|---|---|
| board-triage | ✔ | ✗ | ✗ | Core desk surface; too coupled |
| comms | ✔ | ✗ | ✗ | Requires local-mcp; desk-coupled |
| dev-focus | ✔ | ✗ | ✗ | Desk-specific workflow |
| mise-en-place-scaffold | ✔ | ✔ | ✔ | Reusable, convenient in desk |
| planning-desk | ✔ | ✗ | ✗ | Core desk surface |
| pptx-themes | ✔ | ✔ | ✔ | Orthogonal; reusable |
| project-memory | ✔ | ✗ | ✗ | Requires dotfiles env |
| readme-value-and-proof | ✔ | ✔ | ✔ | Orthogonal; reusable |
| repo-compliance-audit | ✔ | ✗ | ✗ | Desk-specific queries |
| repo-meta-structure | ✔ | ✔ | ✔ | Orthogonal; reusable |

**Dual-homes:** mise-en-place-scaffold, pptx-themes, readme-value-and-proof, repo-meta-structure
(4 skills; 3 new plugin dirs — `pptx-themes` already shipped standalone under ADR 0016)

**Stays in code-desk only:** board-triage, comms, dev-focus, planning-desk, project-memory, repo-compliance-audit (6 + rubric-panel)

---

## Build scope (task-9 AC)

If this design is ratified:

- [ ] Create 3 new plugin directories under `plugins/`: mise-en-place-scaffold, readme-value-and-proof, repo-meta-structure
      _(corrected 2026-08-06 at build time: `pptx-themes` was already a standalone plugin in
      the ADR 0016 lineup, so it needs no new directory — only its code-desk symlink, which
      already exists. 4 skills dual-home; 3 new dirs.)_
- [ ] Each new plugin: `plugin.json` + symlink from source + standalone README
- [ ] Update code-desk/README.md to document dual-home arrangement + which skills are standalone
- [ ] Add symlinks in code-desk/skills/ pointing to the 4 dual-home skills
- [ ] Update root marketplace.json to list 4 new plugins (19 total, up from 15)
- [ ] Update primitives-core.yaml targets (dual-homes stay claude-code + opencode)
- [ ] Verify make ci green

---

## Owner approval gates

**Approval needed:**
1. Bundle-composition principle sound? (ADR extension)
2. Per-skill dispositions (table above) correct for your intended use?
3. Accept the dual-home mechanism (shared symlink) as valid?

If **no** to any: send back disposition changes; principle + mechanism are fixed in design.

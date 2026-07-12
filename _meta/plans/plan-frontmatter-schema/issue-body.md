## What happened

`mhi-raptorxai/raptorxai-infra`, 2026-07-03: a proposal document was authored on the desk (`_meta/plans/dual-track-adoption/proposal.md`) following planning-desk conventions (status line in italics, research record, etc.). repo-compliance-audit then flagged all six PLANS rows against it:

```
PLANS-01..06 | GAP | _meta/plans/dual-track-adoption/proposal.md: missing `title`/`type`/`status`/`created`/`purpose`/`notes`
```

The repo-meta-structure standard requires YAML frontmatter (`title`, `type`, `status`, `created`, `purpose`, `notes`) on `_meta/plans/` docs, but planning-desk's skill text, `_config.template.md`, and plans-README never mention that schema, and its own generated artifacts don't carry it. Notably the audit flagged only `proposal.md` — the desk's `README.md`, `_config.md`, and `issue-body.md` files were apparently exempt (glob rules unclear; if intentional, worth documenting which files the PLANS checks target).

## Suggested direction

Planning-desk should emit the frontmatter the sibling standard requires (its doc-authoring guidance and any templates gaining a frontmatter block), or the standard should scope PLANS-xx to the doc types planning-desk defines. The plugin's flagship planning artifact shouldn't fail the plugin's own audit by default.

Version caveat: planning-desk from cache 0.1.0, audit from 0.2.1 — close if already reconciled in current versions.

---

## Corrected scope (verified against plugin source 0.2.4)

This issue was filed against cache 0.1.0. Re-verifying against current source **re-points** it: the artifacts it names are exempt; the real gap is elsewhere.

- **NON-DEFECT — the named artifacts are checklist-exempt.** `repo-meta-structure/references/checklist.md:132-140` scopes PLANS-01..06 to `*.md` under `_meta/plans/` EXCLUDING `README.md`, `_`-prefixed files, `_utils/`, and `issue-body.md`. So `_config.md` (`_`-prefixed), `README.md` (index), and `issue-body.md` (explicit 2026-07-02 ruling) correctly carry no frontmatter.
- **LIVE — the real gap is `plan.md`.** `plan.md` is in scope for PLANS-01..06, which require frontmatter keys `title, type, status, created, purpose, notes`. But `references/plan.md:14-31` prescribes an inline `Status:` / `Date:` header and names none of the six keys, so a `plan.md` produced by the skill fails PLANS-01..06.

## Acceptance criteria

- `references/plan.md` (and the SKILL plan shape) instruct emitting the 6-key YAML frontmatter (`title, type, status, created, purpose, notes`) on `plan.md`; a `plan.md` produced by the skill passes `repo-compliance-audit` PLANS-01..06.
- The plan-authoring guidance cites the PLANS-01..06 requirement.
- No change to `_config.md` / `README.md` / `issue-body.md` guidance (confirmed exempt).

## Dependencies & gates

- **Blocks on:** nothing.
- **Gates:** `make ci` green + `targets/` regenerated via `make build` (planning-desk is a distributed primitive); `project-workflow` version bump. Relates to `repo-meta-structure` PLANS-01..06.

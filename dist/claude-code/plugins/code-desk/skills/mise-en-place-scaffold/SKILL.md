---
name: mise-en-place-scaffold
description: >-
  Fill-only repo scaffold against the packaged standards — use whenever the ask is
  "scaffold this repo", "run mise-en-place", "fill the audit gaps", "set up a new repo to
  the standard", or any request to create the missing meta-structure the compliance audit
  flags. Runs the bundled script from the repo root: `--plan` (default) prints planned
  creations, conflicts, and non-mechanical items per checklist ID and writes nothing;
  `--apply` creates only the planned items; `--init-manifest` writes the commented
  `_meta/mise-en-place.yml` variance template. Additive-only: it NEVER overwrites,
  merges, edits, deletes, or moves an existing file, never provisions GitHub-side
  objects, and never authors README/CLAUDE.md/AGENTS.md content. Not for measuring
  compliance (repo-compliance-audit) or for questions about what the standard says
  (repo-meta-structure / project-memory skills).
---

# Mise-en-place scaffold

The pair to the read-only compliance audit: the audit measures, this fills the gaps.
One code path serves brownfield compliance and new-repo setup — against a fresh
`git init` with a filled manifest, one `--apply` produces the full standard.

## The loop (audit → plan → review → apply → re-audit)

1. **Run the audit first** (repo-compliance-audit skill) — or use its latest output —
   and review the gap table with the owner.
2. If per-repo variance or GitHub-side knobs are needed:
   `--init-manifest`, fill the fields, commit (see `references/manifest.md`).
3. **Plan, and present the plan before applying** (from the target repo's root):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/mise-en-place-scaffold/scripts/scaffold.py" --plan
   ```

   Show the table verbatim: planned creations, conflicts (with diffs), and manual
   items, per checklist ID. Do not skip this gate.
4. **Apply** only after the plan is reviewed:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/mise-en-place-scaffold/scripts/scaffold.py" --apply
   ```

5. **Re-run the audit** — created rows PASS; conflict and deferred rows still GAP with
   detail until the owner acts.
6. The owner resolves the judgment items (or accepts them) and commits — the scaffold
   never runs `git add`/`git commit`.

Outside the harness pass `--plugin-root <dir>` pointing at a root that contains
`skills/repo-meta-structure/` (checklist + assets) and `skills/project-memory/`.

## Hard rules

- **NEVER overwrite, merge, edit, delete, or move an existing file** — there is no
  overwrite mode at all. A file that differs from a standard template is a **conflict
  with a diff**, left byte-identical; the sanctioned path for disagreement is the owner
  editing the file (or the manifest), never the scaffold forcing it.
- **Idempotent** — a second run plans zero changes; a conformant repo is a no-op.
- **Templates come from the standards' assets** (`repo-meta-structure/assets/`,
  structure-preserving copy). This skill carries no templates of its own — anti-drift,
  one source.
- **Non-mechanical items are reported with guidance, never acted on**: AVOID files
  (content belongs in `_meta/`), inline hooks (migration deferred to the
  hook-composition standard), and authored docs — README.md
  (readme-value-and-proof), CLAUDE.md / AGENTS.md (agent-dot-md-authoring).
- **No GitHub-side provisioning** — `gh_issue_labels` / `gh_milestones` / `board_title`
  are declared in the manifest for the github-project-board skill; the scaffold touches
  only in-repo files.
- **No checklist content of its own** — it fills gaps the standards define and the
  audit reports (plus the same sanctioned HOOK-01 exception the audit carries).

## Reading the output

| Action | Meaning |
|---|---|
| `CREATE` | Missing item, will be / was created from the standard's asset or a minimal stub |
| `OK` | Present and conforming (or governed by another row) — no-op |
| `CONFLICT` | Exists but differs from the standard template — diff printed, file untouched, audit keeps flagging until the owner decides |
| `MANUAL` | Non-mechanical (authored content, AVOID files, inline hooks, curation) — guidance printed, owner or another skill acts |

Planned empty directories get a `.gitkeep` so they survive clone. A dirty working tree
on `--apply` produces a warning but proceeds — creations are additive-only, so a dirty
tree is safe; the warning keeps the diff reviewable.

A **gitignore-swallow warning** (``! <path> — track `_meta/` by default…``) means the
target repo's own `.gitignore` ignores a planned creation: the file is still created
(additive-only, and presence-on-disk is the audit's pass condition), but it is invisible
to `git status` and will not survive a fresh clone. Surface these to the owner — the fix
is to track `_meta/` by default (ADR-0006) or correct the ignore rule, never skipping the creation.

## Error paths (nothing written)

| Symptom | Meaning | Next step |
|---|---|---|
| `not a git repository` | ran outside a repo | cd to the repo root and re-run |
| `checklist file missing` / `template asset missing` | broken plugin install | reinstall/rebuild the plugin |
| `malformed manifest … line N` | `_meta/mise-en-place.yml` unparseable | fix the manifest; the scaffold aborts before any planning |
| `warning: unknown manifest field` | forward-compatible field | harmless; field is ignored by this script |

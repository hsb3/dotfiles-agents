---
name: repo-compliance-audit
description: >-
  Run the read-only repo compliance audit — use whenever the ask is "run the compliance
  audit", "audit this repo against the standard", "is this repo conformant", "check this
  repo's structure/layout compliance", or any request for a pass/gap verdict against the
  repo meta-structure or memory-taxonomy standards. Runs the bundled script from the repo
  root and presents its `ID | Area | Verdict | Detail` table plus `N pass / M gap`
  summary verbatim. Strictly informational: it never writes to the audited repo, never
  fixes gaps (that is the mise-en-place scaffold skill), and defines no checklist content
  of its own (rows come from the sibling standards' checklist files). Not for questions
  about what the standard says (repo-meta-structure / memory-taxonomy skills) or for
  scaffolding missing structure.
---

# Repo compliance audit

The rollout's measuring instrument: one command, a pass/gap table, exit 0 either way.
The output IS the compliance checklist — do not maintain a separate tracking document.

## How to run

From the **audited repo's root** (the script resolves the git toplevel of the cwd):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/repo-compliance-audit/scripts/audit.py"
```

The script finds the checklists via `$CLAUDE_PLUGIN_ROOT` automatically; outside the
harness pass `--plugin-root <dir>` pointing at a root that contains
`skills/repo-meta-structure/references/checklist.md` and
`skills/memory-taxonomy/references/checklist.md`.

Then **present the table verbatim** (fenced code block), including the summary line.
Do not re-derive, filter, or re-score rows yourself — the script is the instrument.

## Hard rules

- **NEVER write to the audited repo during an audit.** No fixes, no scaffolding, no
  manifest creation, no "quick cleanups" — even if gaps look trivial. Fixing gaps is the
  mise-en-place scaffold skill's job (audit → scaffold → re-audit loop).
- **Reports, never polices.** Gaps do not make the run a failure; exit 0 with gaps is
  the normal, healthy outcome. Do not turn the audit into a CI gate.
- **Zero self-defined checks.** Every row comes from a standard's `references/checklist.md`
  (sole exception: `HOOK-01`, sourced from the hooks-as-script-plus-config decision until
  the hook-composition standard lands). To add or change a check, change the standard.

## Reading the output

- `PASS` / `GAP` per row; gap details name the concrete path, probe, or pattern.
- **Migration debt** wording (e.g. `.claude/commands/` on `CLAUDE-07`) is distinct from a
  structural gap — it means "works today, fold into the standard replacement".
- `N/A` = not evaluable (e.g. `MEM-04` link integrity when the memory index itself is
  missing — that gap is `MEM-02`'s).
- `VAR-xx` rows are the repo's own declared variance from `_meta/mise-en-place.yml`
  (`required_folders` / `required_files`) — manifest knobs are checked, not just excused.
  A missing manifest is not a gap; defaults apply.

## Error paths (no partial table)

| Symptom | Meaning | Next step |
|---|---|---|
| `not a git repository` | ran outside a repo | cd to the repo root and re-run |
| `checklist file missing: …` | broken plugin install | reinstall/rebuild the plugin; never audit against a partial checklist |
| `malformed manifest … line N` | `_meta/mise-en-place.yml` unparseable | fix the manifest; the audit aborts rather than guessing variance |

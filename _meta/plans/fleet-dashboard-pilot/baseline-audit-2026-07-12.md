---
title: "fleet-dashboard Gate-2 pilot -- BASELINE audit (2026-07-12)"
type: reference
status: final
created: 2026-07-12
purpose: Point-in-time baseline compliance-audit record of fleet-dashboard at 3d81a48, before the Gate-2 manifest + scaffold pass (#33).
notes: Snapshot record -- not updated in place; a re-audit produces a new dated file.
---

# fleet-dashboard Gate-2 pilot — BASELINE audit

Date: 2026-07-12
Repo audited: /Users/henry/Developer/fleet-dashboard
Commit SHA audited: `3d81a48` (branch `main`, working tree clean — `git status --porcelain` empty)

Command run (from fleet-dashboard root):

```
python3 "/Users/henry/Developer/dotfiles-agents/primitives-core/skills/repo-compliance-audit/scripts/audit.py" --plugin-root "/Users/henry/Developer/dotfiles-agents/primitives-core"
```

Note: `--plugin-root` was passed explicitly (pointing at `dotfiles-agents/primitives-core`,
which contains `skills/repo-meta-structure/references/checklist.md` and
`skills/memory-taxonomy/references/checklist.md`) because this run was outside the Claude
Code harness, so `$CLAUDE_PLUGIN_ROOT` was not set.

## Verbatim output

```
Compliance audit — /Users/henry/Developer/fleet-dashboard
Manifest variance applied (_meta/mise-en-place.yml): default_branch=main

ID        | Area           | Verdict | Detail
----------+----------------+---------+-------
META-01   | `_meta/`       | PASS    | _meta/_archive/
META-02   | `_meta/`       | PASS    | _meta/briefings/
META-03   | `_meta/`       | PASS    | _meta/plans/
META-04   | `_meta/`       | PASS    | _meta/operations/
META-05   | `_meta/`       | PASS    | _meta/research/
META-06   | `_meta/`       | PASS    | _meta/HANDOFF.md
META-07   | `_meta/`       | PASS    | _meta/README.md
CLAUDE-01 | `.claude/`     | PASS    | .claude/agents/
CLAUDE-02 | `.claude/`     | PASS    | .claude/hooks/
CLAUDE-03 | `.claude/`     | PASS    | .claude/memory/
CLAUDE-04 | `.claude/`     | PASS    | .claude/rules/
CLAUDE-05 | `.claude/`     | PASS    | .claude/skills/
CLAUDE-06 | `.claude/`     | PASS    | .claude/settings.json
CLAUDE-07 | `.claude/`     | PASS    | absent: .claude/commands/
GH-01     | `.github/`     | PASS    | .github/ISSUE_TEMPLATE/config.yml
GH-02     | `.github/`     | PASS    | .github/ISSUE_TEMPLATE/bug.yml
GH-03     | `.github/`     | PASS    | .github/ISSUE_TEMPLATE/feature.yml
GH-04     | `.github/`     | PASS    | .github/ISSUE_TEMPLATE/epic.yml
GH-05     | `.github/`     | PASS    | .github/PULL_REQUEST_TEMPLATE.md
GH-06     | `.github/`     | PASS    | .github/dependabot.yml
GH-07     | `.github/`     | PASS    | .github/workflows/ci.yml
GH-08     | `.github/`     | PASS    | .github/workflows/claude-review.yml
GH-09     | `.github/`     | PASS    | .github/workflows/claude.yml
ROOT-01   | Root           | PASS    | README.md
ROOT-02   | Root           | PASS    | CLAUDE.md
ROOT-03   | Root           | PASS    | AGENTS.md
ROOT-04   | Root           | PASS    | Makefile
ROOT-05   | Root           | PASS    | lefthook.yml
ROOT-06   | Root           | PASS    | .gitignore
ROOT-07   | Root           | PASS    | .mcp.json
ROOT-08   | Root           | PASS    | docs/
ROOT-09   | Root           | PASS    | scripts/
ROOT-10   | Root           | PASS    | tests/
DOCS-01   | `docs/`        | PASS    | docs/README.md
DOCS-02   | `docs/`        | GAP     | missing file: docs/CHARTER.md
DOCS-03   | `docs/`        | PASS    | docs/decisions/
DOCS-04   | `docs/`        | PASS    | docs/decisions/README.md
DOCS-05   | `docs/`        | PASS    | docs/decisions/0000-template.md
IGNORE-01 | gitignore      | PASS    | ignored: _meta/operations/probe
IGNORE-02 | gitignore      | PASS    | tracked (not ignored): _meta/plans/probe.md
IGNORE-03 | gitignore      | PASS    | tracked (not ignored): _meta/plans/inbox/probe.md
IGNORE-04 | gitignore      | PASS    | tracked (not ignored): _meta/README.md
IGNORE-05 | gitignore      | PASS    | tracked (not ignored): _meta/HANDOFF.md
IGNORE-06 | gitignore      | PASS    | tracked (not ignored): _meta/mise-en-place.yml
IGNORE-07 | gitignore      | PASS    | ignored: .env
IGNORE-08 | gitignore      | PASS    | tracked (not ignored): .env.example
IGNORE-09 | gitignore      | PASS    | ignored: .claude/settings.local.json
IGNORE-10 | gitignore      | PASS    | ignored: .claude/worktrees/probe/file
IGNORE-11 | gitignore      | PASS    | tracked (not ignored): .claude/settings.json
IGNORE-12 | gitignore      | PASS    | tracked (not ignored): .claude/memory/MEMORY.md
IGNORE-13 | gitignore      | PASS    | tracked (not ignored): _meta/_archive/.gitkeep
IGNORE-14 | gitignore      | PASS    | tracked (not ignored): _meta/briefings/.gitkeep
IGNORE-15 | gitignore      | PASS    | tracked (not ignored): _meta/operations/.gitkeep
IGNORE-16 | gitignore      | PASS    | tracked (not ignored): _meta/research/.gitkeep
IGNORE-17 | gitignore      | PASS    | ignored: _meta/plans/_utils/__pycache__/probe.pyc
IGNORE-18 | gitignore      | PASS    | ignored: _meta/plans/.DS_Store
AVOID-01  | Root           | PASS    | absent: TODO.md
AVOID-02  | Root           | PASS    | absent: NOTE.md
AVOID-03  | Root           | PASS    | absent: NOTES.md
PLANS-01  | `_meta/plans/` | PASS    | `title` present in all 2 in-scope docs
PLANS-02  | `_meta/plans/` | PASS    | `type` present in all 2 in-scope docs
PLANS-03  | `_meta/plans/` | PASS    | `status` present in all 2 in-scope docs
PLANS-04  | `_meta/plans/` | PASS    | `created` present in all 2 in-scope docs
PLANS-05  | `_meta/plans/` | PASS    | `purpose` present in all 2 in-scope docs
PLANS-06  | `_meta/plans/` | PASS    | `notes` present in all 2 in-scope docs
MEM-01    | memory         | PASS    | .claude/memory/
MEM-02    | memory         | PASS    | .claude/memory/MEMORY.md
MEM-03    | memory         | PASS    | tracked (not ignored): .claude/memory/probe.md
MEM-04    | memory         | PASS    | all relative links in .claude/memory/MEMORY.md resolve
HOOK-01   | hooks          | PASS    | 1 hook command(s), all plain script invocations

69 pass / 1 gap
```

## Post-run verification

- `git -C /Users/henry/Developer/fleet-dashboard status --porcelain` → empty (audit made no
  changes; read-only proof holds).
- `git -C /Users/henry/Developer/fleet-dashboard rev-parse --short HEAD` → `3d81a48`
- `git -C /Users/henry/Developer/fleet-dashboard branch --show-current` → `main`

---
title: Bring dotfiles-agents + workbench into project-workflow conformance
type: plan
status: complete
created: 2026-07-02
purpose: Dogfood the just-built standard — drive both host repos to a clean (or justified-remainder) repo-compliance-audit, via manifest + scaffold + hand-closes.
notes: DONE 2026-07-02 — both repos at 59 pass / 0 gap (workbench 2c21c83, incl. first CI + first tests/; dotfiles-agents this commit). Standards backlog surfaced - non-negated _meta gitkeeps do not survive clone (META rows re-gap on fresh clone), _archive vs archive naming, mcp-stub wording. GitHub-side still open - CLAUDE_CODE_OAUTH_TOKEN secret + Claude app for the two claude workflows, branch-protection wiring, per-clone lefthook install.
---

# Project-workflow conformance — the two host repos

## Deliverables

- Each repo: `_meta/mise-en-place.yml` manifest (committed, tracked via IGNORE-06 negation), scaffold applied (additive-only), residual gaps hand-closed or explicitly justified.
- dotfiles-agents specials: PLANS frontmatter on `devtools-eng-spec-build.md` (+ this file conforms from birth); `lefthook.yml` mirroring the `make ci` lanes; dependabot trimmed to applicable ecosystems.
- workbench specials: **first CI workflow** (`ci.yml` running promote-check-all + tests), **first `tests/`** (real stdlib smoke tests over `promote_check.py`, wired to a `make test` target), `_meta/plans/` + gitignore negations (IGNORE-02/03), lefthook.yml.
- Both: `.claude/` dirs with `.gitkeep`, memory stub per MEM rows, `.github` assets from the standard's templates (claude/claude-review workflows installed; their secrets are GitHub-side, noted not blocking).

## Criteria (gates, foreman-run)

- Re-audit per repo: **0 GAP**, or every remaining GAP named with a one-line justification in the manifest's notes/commit message.
- `make ci` (dotfiles-agents, 158 tests) and `make promote-check-all` + new `make test` (workbench) green; `actionlint` clean on any new workflow files.
- No file overwritten by scaffold (additive-only proven in its output); existing CI untouched in dotfiles-agents.

## Parallelism

Two builders, disjoint by repo. No shared files. Foreman commits per repo after gating.

## Out of scope

GitHub-side provisioning (project board, milestones, labels, workflow secrets) — the audit doesn't check it and the skills don't write it; queued separately. Content-authoring of README/CLAUDE.md prose beyond frontmatter.

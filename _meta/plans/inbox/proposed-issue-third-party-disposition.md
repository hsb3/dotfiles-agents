---
title: "chore: decide the vendored-third-party boundary + per-item disposition for the sourced primitives"
type: proposed-issue
status: filed
created: 2026-07-12
updated: 2026-07-14
purpose: Staged issue for the owner directive (2026-07-12) on third-party content in primitives-core. Filed as issue #105 on 2026-07-14 after owner approval.
---

**Filed as [#105](https://github.com/hsb3/dotfiles-agents/issues/105) (2026-07-14) — the issue is
now the single source of truth; this file is a pointer only.**

The two open owner decisions were ruled 2026-07-14 under explicit delegation (executive-desk
decision `dev-tooling-desk/decisions/0005`): (1) `origin: sourced` reserved for intentionally
maintained/diverged forks, verbatim copies move to externals.yaml once #36 lands; (2)
agent-generated content under the owner's direction is self-authored — usage, not provenance,
judges it. The filed body also folds in the 2026-07-14 verified audit corrections
(carbon-builder + nanobanana mislabels, react-doctor unclear).

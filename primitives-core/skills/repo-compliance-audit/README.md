# repo-compliance-audit

Runs the read-only repo compliance audit: one script, a pass/gap table, exit 0 either way.
Checks a repo's structure and layout against the repo-meta-structure and project-memory
standards and prints an `ID | Area | Verdict | Detail` table plus an `N pass / M gap`
summary — the output itself is the compliance checklist. Strictly informational: it never
writes to the audited repo and never fixes gaps.

## When it triggers

Use it to "run the compliance audit", "audit this repo against the standard", "is this repo
conformant", "check this repo's structure/layout compliance", or any request for a pass/gap
verdict against the repo meta-structure or project-memory standards. Not for questions about
what the standard says, or for scaffolding missing structure — that's a different skill.

## Install

```
claude plugin install mise-en-place@dotfiles-agents
```

Ships in the `mise-en-place` bundle.

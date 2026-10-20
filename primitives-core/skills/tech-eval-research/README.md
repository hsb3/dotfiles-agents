# tech-eval-research

Rigorous, cited, comparative evaluation of technology options — producing a capability
comparison matrix backed by primary sources instead of marketing pages, plus a ranked shortlist
and recommendation when a candidate passes every hard filter, otherwise a no-verified-match
finding with the decisive gates, rather than promoting a near-miss or a narrower pilot.

## When it triggers

Use it whenever the user wants to compare, evaluate, choose, or shortlist technologies —
frameworks, infrastructure, serving layers, databases, libraries, SaaS-vs-self-hosted
tools — "which X should we use", "evaluate these options", "is the free tier actually
free"; for license or paywall audits, self-hostability checks, open-source maturity
assessments, build-vs-buy research, or vendor-neutral recommendations, even if the user
never says "research" or "report". It runs hard filters that eliminate candidates,
resolves a capability checklist per-feature from primary sources (never a marketing page),
adversarially re-verifies the claims that decide the ranking, and delivers a standard
report with a comparison matrix and a recommendation — a themed deck only if requested.

## Artifact layout

An evaluation lives in a project folder with schema-checked files: `data/requirements.yaml`
and `data/eval-rubric.yaml` (scope), optional `data/landscape.yaml`,
`data/findings/<candidate>.yaml` (research and verification), `runs/<proof>/runs.jsonl`
(proofs), `docs/report.md` (written last), the project's `schemas/` (copied from
`references/schemas/` at scope time and frozen once research starts), and an optional
`eval.toml` that overrides any location. Start by copying `references/starter/` into the
project and `references/schemas/` to its `schemas/`.

Check it with `<skill-dir>/scripts/validate.py --root <project>` (default: the current
directory); the `uv` shebang pulls jsonschema and pyyaml on Python >= 3.11. Exit 0 is valid,
1 is schema or reference findings, 2 is a usage, config, missing-file or parse error. It must
exit 0 before the report is written.

## Install

Ships inside the `solo-skills` bundle:

```
claude plugin install solo-skills@dotfiles-agents
```

## Codex

Research briefs name search, page retrieval, and repository capabilities rather than requiring Claude-specific tool names. Discover the tools available in the current client and keep inaccessible evidence explicitly unverified.

# Memory Index

- [make ci ✗-line is a passing test](make-ci-refusal-line-is-a-passing-test.md) — judge `make ci` by exit code, never by grepping for ✗
- [mermaid-cli exits 0 on failure](mermaid-cli-exits-zero-on-failure.md) — a failed render returns 0 and writes no file; assert `test -s out.svg`
- [Measure a heuristic against a corpus](measure-a-heuristic-against-a-corpus.md) — a scanner can pass every test and be 79% precise; replay over git history, score against a stdlib parser
- [Probe harness hygiene](probe-harness-hygiene.md) — a probe lies two ways: env that never reached the child, artifacts `git status` can't see
- [No unguarded counts in prose](no-unguarded-counts-in-prose.md) — a count needs a gate that checks it, else phrase it so growth can't falsify it
- [Use subagents for labor](feedback-use-subagents-for-labor.md) — the session keeps the foreman floor; edit chains, sweeps, and verification get briefs
- [Worktree isolation](worktree-isolation.md) — two levers to force it, and the uncommitted work a worktree can never see
- [Subagent agent-memory litter](subagent-agent-memory-litter.md) — comes from an agent's `memory:` frontmatter key; sweep the exact stray path, never a parent dir
- [Plugin enablement needs a per-project install](plugin-enablement-needs-per-project-install.md) — `enabledPlugins` is inert without an install record for this projectPath; and a stale project-scope record silently pins that repo behind user scope
- [Harness lane](harness-lane.md) — standing commit/PR/merge permission (dev only) + the claude invocation that keeps the Skill tool
- [launchd = bash 3.2](launchd-bash32-scripts.md) — verify LaunchAgent scripts with `/bin/bash`, not the interactive shell
- [Extender estate cohesion](extender-estate-cohesion.md) — opencode is deferred not abandoned; desk-standard is deliberately not distributed yet
- [Reproduce before fixing a card](reproduce-before-fixing-a-card.md) — a card is the filer's inference, not a measurement; stale cards and partial closes regenerate work
- [Identity gate blocks personal-repo installs](identity-gate-blocks-personal-repo-installs.md) — the owner handle is an unconditional ban with no exemption; `gh search --owner @me` is the only legal shape and only works for the owner

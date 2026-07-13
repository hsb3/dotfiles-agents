*Survey of projects distributing coding-agent extenders (rules / skills / agents / MCP / hooks) across harnesses, vs this repo's translate-from-single-source design.*
*Status: draft — owner requested 2026-07-12; owner-referenced projects (gsd-core, ECC) folded in same day.*

# Extender-distribution ecosystem survey (2026-07-12)

Research question (owner, 2026-07-12): "worth research: projects doing a similar thing in terms
of distributing 'extenders' for different harnesses — I know there are a few out there."
Method: parallel web research, all repos verified by direct fetch on 2026-07-12 unless flagged.
Star counts are as-of that date.

## The two real peers (single source -> per-harness build)

| Project | What it distributes | Targets | Mechanism | Maturity |
|---|---|---|---|---|
| [ruler](https://github.com/intellectronica/ruler) | rules, MCP config, skills, subagents | 30+ harnesses (Claude Code, Copilot, Cursor, Aider, Windsurf, Cline, Codex CLI, Gemini CLI, Zed...) | `.ruler/` source dir -> `ruler apply` generates each agent's native files; subagents transformed per-format | 2.8k stars, v0.3.44 Jun 2026, active |
| [rulesync](https://github.com/dyoshikawa/rulesync) | rules, ignore files, MCP, commands, subagents, skills, **hooks, permissions** | 30+ (incl. opencode, Amp, Antigravity, Warp) | build/generate from `.rulesync/` + bidirectional import/export (tool -> tool conversion) | 1.2k stars, v9.6.3 Jul 11 2026, 267 releases, very active |

rulesync has the broadest primitive coverage surveyed - the only one that also handles hooks and
permissions; it is the nearest feature superset of this repo's translation step.

## Owner-referenced projects (added 2026-07-12, from Henry's links)

- [ECC](https://github.com/affaan-m/ECC) - "The agent harness performance optimization system.
  Skills, instincts, memory, security, and research-first development for Claude Code, Codex,
  Opencode, Cursor and beyond." Distributes 278 skills, 67 agents, 34 rule sets, hooks (15+
  events), MCP configs, plus a dashboard GUI, across 10+ harnesses via a cross-harness
  abstraction layer with per-harness adapters (`.claude-plugin/`, `.cursor/`, `.codex/`,
  `.opencode/`). Three install paths: Claude Code plugin from a self-hosted marketplace, npm
  (`ecc-universal`), manual installers. Repo page shows 211.9k stars / 230+ contributors /
  v2.0.0 Jun 2026 (as-reported by the page fetch - not independently verified); MIT + paid Pro
  tier. **This is the closest thing to a peer at scale**: single source -> per-harness layouts,
  marketplace + raw paths, hooks included. Differences: public mega-catalog vs curated personal
  set; no provenance/promotion-gate concept; adds runtime layers (instinct learning, memory
  isolation, security auditor) this repo deliberately leaves to the harness.
- [gsd-core](https://github.com/open-gsd/gsd-core) - "A light-weight meta-prompting, context
  engineering, and spec-driven development system for Claude Code, OpenCode, Antigravity CLI,
  Kimi CLI, Kilo, Codex, Copilot, Cursor, Windsurf, and more." Distributes agents, commands,
  skills, hooks + spec/context artifacts via an npm installer (`@opengsd/gsd-core`) that detects
  the runtime and configures per-harness (direct file copy discouraged). 6.5k stars, v1.6.1
  Jul 2026, very active. Less a distribution system than a **methodology product** (five-phase
  loops, fresh-context subagents, STATE.md/CONTEXT.md continuity) that happens to install
  cross-harness - the overlap with this repo is the installer pattern, and its process layer
  competes with project-workflow's SOPs.

## Close design match, no adoption

- [agent_sync](https://github.com/yelmuratoff/agent_sync) (10 stars, 340 commits): single source
  `.ai/src/`, per-tool transforms (md -> TOML for Gemini), SHA-256 manifest drift detection, and an
  `adopt` flow promoting downstream edits back to source. Strikingly parallel to this repo's
  "generated targets + CI drift guard + lock" conventions; adoption near zero.
- [dotagent](https://github.com/johnlindquist/dotagent) (144 stars): bidirectional converter with a
  unified `.agent/` intermediate representation - rules only.

## Same goal, different mechanism

- [ai-rules-sync](https://github.com/lbb00/ai-rules-sync) (35 stars): symlinks one canonical copy
  from git-managed source repos into 13+ tools - no translation, assumes format compatibility.
- [vercel-labs/skills](https://github.com/vercel-labs/skills) / skills.sh (25.9k stars, v1.5.16
  Jul 2026): the de-facto public skills package manager - `npx skills` installs SKILL.md folders
  into 75+ agents by symlink/copy. No translation; works because SKILL.md became the standard.
  (Note: this repo's `find-skills` primitive is sourced FROM this project.)
- [openskills](https://github.com/numman-ali/openskills) (10.6k stars): ports Claude-style
  progressive skill loading to non-Claude harnesses by injecting an available-skills index into
  AGENTS.md - runtime-discovery shim instead of build-time translation.
- [vibe-rules](https://github.com/FutureExcited/vibe-rules) (525 stars): rules distribution with a
  novel channel - rules shipped inside npm packages (`llms` export) and auto-applied on install.

## Adjacent: marketplaces, registries, the standard

- [anthropics/skills](https://github.com/anthropics/skills) (161k stars) + the
  [agentskills spec](https://github.com/agentskills/agentskills) / agentskills.io (22.9k stars):
  the standardization play - ~40 clients now read SKILL.md natively. Strategic consequence: the
  value of a translation layer concentrates in what has NOT standardized - subagents, hooks, MCP
  wiring, plugin packaging.
- [claude-code-templates](https://github.com/davila7/claude-code-templates) / aitmpl.com (29.2k
  stars): biggest community catalog (1000+ components), Claude Code only, catalog-and-copy.
- [claude-plugins](https://github.com/Kamalnrf/claude-plugins) / claude-plugins.dev (527 stars):
  auto-crawled registry indexing ~12k plugins / ~63k skills; cross-agent install CLIs; no curation.
- [tonsofskills](https://github.com/jeremylongshore/claude-code-plugins-plus-skills): another
  Claude-Code-only mega-marketplace (lightly verified).
- agent-skills-cli / SkillsMP: **unverified** beyond search results - excluded from conclusions.
- [steipete/agent-rules](https://github.com/steipete/agent-rules) (5.7k stars, ARCHIVED May 2026):
  cautionary datapoint - static shared-rules repos aged out fast.
- MCP-only registries (adjacent, one primitive type): Smithery (6k+ servers, hosting + meta-MCP),
  Glama (~37k directory), mcp.so (~20k), the official MCP Registry (server.json feed).

## Synthesis - where this repo sits

Mechanically, ECC is the closest peer at scale: like this repo it renders one source into
per-harness layouts AND ships both a plugin-marketplace path and raw installs, hooks included.
What no surveyed project (ECC included) combines is the **curation layer**: a personal/private
source-of-truth with a roster + content-hash lock, a **two-shelf model** (always-on core vs
toggle/marketplace), a **promotion gate with provenance discipline** (origin/upstream/ref,
use-evidence dispositions), and **externals tracked-by-reference** (clone-at-build). ECC and the
marketplaces maximize catalog size; ruler/rulesync are project-scoped team tools; this repo's
distinctive bet is proven-and-provenanced over comprehensive - the scope-first policy is the moat,
not the build step.

## Implications worth considering (not decisions)

1. **Track the agentskills standard.** As SKILL.md goes universal, keep the translation
   investment on agents/hooks/mcp/plugin-packaging, not skills.
2. **Benchmark against rulesync** before building new translation capability (#59 agnostic base
   format) - it may be adoptable as a component or at least a format reference for targets this
   repo doesn't cover (Cursor, Copilot, Codex).
3. **skills.sh / claude-plugins.dev as sourcing catalogs** - fits the ratified rule: vendor lists
   are sourcing catalogs, not backlogs; entries wait for a claimed use case.
4. **The archived agent-rules repo** supports the scope-first policy: extender collections
   without driving use cases rot.

*Provenance: compiled from a parallel research agent's verified fetches (2026-07-12); the two
peer-tier claims (ruler, rulesync) and the standard (agentskills.io) cross-checked by the session.
Owner's referenced project still to be added.*

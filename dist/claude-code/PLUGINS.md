# Plugin inventory

<!-- GENERATED FILE — do not hand-edit. Regenerate via `make build` (scripts/gen_marketplace.py); `make build-check` fails on drift. -->

Every plugin distributed by the `dotfiles-agents` marketplace, generated from `plugins.yaml` + `primitives-core.yaml` (bundles/kits) and `skill-catalog.yaml` (standalone skills).

## claude-code-config

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Configure the Claude Code harness end to end: the settings-file layer (route each change to the correct file by precedence — managed policy vs user vs project vs machine-local), narrowest-scope allow/deny/ask permission rules, automated behaviors implemented as ratified directory-based hooks (config plus script file, never inline shell), env vars, and MCP server registration, then verify every edit for JSON validity and take-effect. Changing an existing setting is one facet of the broader configuration surface this skill covers.
- **Ships:** 1 skill — claude-code-config
- **Install:** `claude plugin install claude-code-config@dotfiles-agents`

## claude-code-expertise

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Expert map of Claude Code's extension surfaces for authoring and debugging extenders - skills, subagents, hooks, commands, plugins, marketplaces, MCP servers, and settings/permissions. The map (which surface, which contract, what's idiomatic) complementing the official skill/plugin builders: a surface-selection decision table, each surface's frontmatter/config contract with a minimal example, subagent authoring end to end (scaffold, tool selection, model/tier choice, when-to-use description), cross-surface authoring quality plus a validation checklist, and plugin/marketplace distribution mechanics. Use to pick the right surface for a need, look up a contract, author or debug any extender, or answer how a Claude Code surface works.
- **Ships:** 1 skill — claude-code-expertise
- **Install:** `claude plugin install claude-code-expertise@dotfiles-agents`

## code-desk

- **Kind:** bundle
- **Version:** 0.3.0
- **Description:** Bring a software project through the next-release execution loop, a documented repo standard, and the executive-desk overhead together — plan the work into conformant issues and source-grounded plans, keep the repo's meta-structure/memory/README to standard, produce recurring status comms, run board triage, and build themed PowerPoint decks.
- **Ships:** 10 skills — board-triage, comms, dev-focus, mise-en-place-scaffold, planning-desk, pptx-themes, project-memory, readme-value-and-proof, repo-compliance-audit, repo-meta-structure
- **Install:** `claude plugin install code-desk@dotfiles-agents`

## dataviz

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Design data visualizations - charts, plots, dashboards - that are correct, legible, and honest, consulted before any chart code in any library or medium: data-shape to mark-type heuristic, anti-patterns to refuse (pie overuse, dual axes, truncated bars, rainbow scales, 3D), a brand-neutral colorblind-safe palette with light/dark themes and brand-swap, composition, interaction plus static degradation, and a final validation checklist. Data charts only - structural diagrams belong to diagrams/mermaid, deck theming to pptx-themes.
- **Ships:** 1 skill — dataviz
- **Install:** `claude plugin install dataviz@dotfiles-agents`

## deep-research

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Run a deep, multi-source, fact-checked research investigation that ends in a cited report: scope the question, decompose into ~5 angles, fan out searches (parallel subagents or serial), dedupe/fetch sources, extract falsifiable claims, adversarially refute each load-bearing claim (majority-refute kills it), and synthesize a confidence-ranked, per-claim-cited report that keeps negative findings.
- **Ships:** 1 skill — deep-research
- **Install:** `claude plugin install deep-research@dotfiles-agents`

## diagrams

- **Kind:** plugin
- **Version:** 0.1.0
- **Description:** Structural diagrams for repo docs, decks, and architecture briefings - Mermaid for GitHub-rendered markdown (house rule: no parentheses or special characters in node labels), Python diagrams for cloud architecture with provider icons (Azure first, GCP legacy), draw.io legacy-file reading and headless export, Excalidraw sketch diagrams with an author-the-JSON fallback when MCP tools are absent, and raw Graphviz - all feeding SVG+PNG output pipelines with light/dark-friendly styling. Structural diagrams only: data charts belong to the dataviz skill, deck theming to pptx-themes.
- **Ships:** 4 skills — diagrams, drawio, excalidraw, mermaid
- **Install:** `claude plugin install diagrams@dotfiles-agents`

## foreman-kit

- **Kind:** plugin
- **Version:** 0.6.0
- **Description:** A context-and-cost optimization kit for multi-agent work: tiered delegation agents (scout · builder · reviewer · lead across model tiers), a self-contained foreman orchestration skill with a two-level effort calibration (standard for Opus-led sessions, deep for Fable-led), the handoff skill, a waves skill that drives an issue backlog to closed through a pinned triage issue + wave-planned isolated crews, and four hooks — context-watermark and handoff-freshness-guard enforce handoff-then-clear over compact at ~70k/100k-token watermarks, session-handoff-surfacer surfaces the handoff on cold start, and subagent-telemetry records per-delegation tier usage.
- **Ships:** 3 skills — foreman, handoff, waves; 4 hooks — context-watermark, handoff-freshness-guard, session-handoff-surfacer, subagent-telemetry; 4 agents — builder, lead, reviewer, scout
- **Install:** `claude plugin install foreman-kit@dotfiles-agents`

## github-project-board

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Stand up and operate a single GitHub Project (v2) board that serves timeline, prioritization, and day-to-day task management from one item set sliced into ma…
- **Ships:** 1 skill — github-project-board
- **Install:** `claude plugin install github-project-board@dotfiles-agents`

## obsidian-toolkit

- **Kind:** plugin
- **Version:** 0.1.0
- **Description:** Obsidian guidance bundle - plugin API fundamentals (lifecycle, settings, vault operations, commands), chat/copilot sidebar UI patterns, in-plugin MCP servers over Streamable HTTP, and vault automation via the official Obsidian CLI, packaged as a separately toggleable plugin.
- **Ships:** 4 skills — obsidian-api-basics, obsidian-chat-ui, obsidian-cli, obsidian-mcp-server
- **Install:** `claude plugin install obsidian-toolkit@dotfiles-agents`

## opencode-expertise

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Expert knowledge of opencode — every extension surface (config, agents, skills, commands, custom tools, plugins, MCP, rules), the TypeScript constraint, and the claude-code → opencode translation mapping. Use when configuring opencode, authoring or migrating extenders for it, designing an opencode distribution target for a Claude Code skill collection, or answering how any opencode surface works.
- **Ships:** 1 skill — opencode-expertise
- **Install:** `claude plugin install opencode-expertise@dotfiles-agents`

## owner-signoff

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Present a batch of decisions, approvals, or questions to the project owner as a local HTML form in their browser instead of asking in chat; answers flow back to a JSON file the session picks up automatically.
- **Ships:** 1 skill — owner-signoff
- **Install:** `claude plugin install owner-signoff@dotfiles-agents`

## pptx-themes

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Create, edit, and review PowerPoint presentations with a curated theme layer — semantic theme tokens, approved color palettes, monospaced typography, and a visual-QA workflow — composed over Anthropic's vendored pptx base skill (base/, verbatim; recorded in externals.yaml).
- **Ships:** 1 skill — pptx-themes
- **Install:** `claude plugin install pptx-themes@dotfiles-agents`

## private-fork

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Stand up and operate a private fork (private mirror) of an upstream OSS repo: mirror + remotes setup, governance tiers, delete-vs-disable rubric, divergence ledger/registry, and the recurring upstream review/merge cycle.
- **Ships:** 1 skill — private-fork
- **Install:** `claude plugin install private-fork@dotfiles-agents`

## project-memory

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** The memory taxonomy v1 as consultable reference content — global vs project layers, always-on index vs situational topics, memory vs rules vs skills, the secret-only birth rule, and the curation-time promotion mechanism — paired with the operational mechanics: project_memory.py opts a git repo into tracked, in-repo auto-memory by wiring the repo's own .claude/memory/ as autoMemoryDirectory (init/status/path/list; never overwrites), and migrate_memory.py recovers a project's memory (and optional transcripts) after its folder moves, dry-run by default. Pure Python 3 stdlib.
- **Ships:** 1 skill — project-memory
- **Install:** `claude plugin install project-memory@dotfiles-agents`

## tech-eval-research

- **Kind:** standalone skill
- **Version:** 0.0.1
- **Description:** Rigorous, cited, comparative technology evaluation producing a ranked shortlist, a capability comparison matrix, and a primary-source-backed recommendation; use to compare, evaluate, choose, or shortlist technologies, for license/paywall audits, self-hostability and OSS-maturity checks, and build-vs-buy research.
- **Ships:** 1 skill — tech-eval-research
- **Install:** `claude plugin install tech-eval-research@dotfiles-agents`

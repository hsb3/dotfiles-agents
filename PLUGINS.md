# Plugin inventory

<!-- GENERATED FILE — do not hand-edit. Regenerate via `make build` (scripts/gen_marketplace.py); `make build-check` fails on drift. -->

Every plugin distributed by the `dotfiles-agents` marketplace, generated from `plugins.yaml` + `primitives-core.yaml` (bundles/kits) and `skill-catalog.yaml` (standalone skills).

## code-desk

- **Kind:** bundle
- **Version:** 0.1.0
- **Description:** Bring a software project through the next-release execution loop and a documented repo standard together — plan the work into conformant issues and source-grounded plans, keep the repo's meta-structure/memory taxonomy/README to standard, and operate a private fork's upstream review cycle.
- **Ships:** 7 skills — memory-taxonomy, mise-en-place-scaffold, opencode-expertise, private-fork, readme-value-and-proof, repo-compliance-audit, repo-meta-structure
- **Install:** `claude plugin install code-desk@dotfiles-agents`

## diagrams

- **Kind:** plugin
- **Version:** 0.1.0
- **Description:** Structural diagrams for repo docs, decks, and architecture briefings - Mermaid for GitHub-rendered markdown (house rule: no parentheses or special characters in node labels), Python diagrams for cloud architecture with provider icons (Azure first, GCP legacy), draw.io legacy-file reading and headless export, Excalidraw sketch diagrams with an author-the-JSON fallback when MCP tools are absent, and raw Graphviz - all feeding SVG+PNG output pipelines with light/dark-friendly styling. Structural diagrams only: data charts belong to the dataviz skill, deck theming to pptx-themes.
- **Ships:** 4 skills — diagrams, drawio, excalidraw, mermaid
- **Install:** `claude plugin install diagrams@dotfiles-agents`

## exec-desk

- **Kind:** bundle
- **Version:** 0.1.0
- **Description:** The executive-desk overhead — stand up a source-grounded planning desk, produce recurring status comms, keep a GitHub Project board's prioritization fields groomed, and build themed PowerPoint decks.
- **Ships:** 4 skills — board-triage, comms, planning-desk, pptx-themes
- **Install:** `claude plugin install exec-desk@dotfiles-agents`

## foreman-kit

- **Kind:** plugin
- **Version:** 0.5.0
- **Description:** A context-and-cost optimization kit for multi-agent work: tiered delegation agents (scout · builder · reviewer · lead across model tiers), a self-contained foreman orchestration skill with a two-level effort calibration (standard for Opus-led sessions, deep for Fable-led), the handoff skill, and four hooks — context-watermark and handoff-freshness-guard enforce handoff-then-clear over compact at ~70k/100k-token watermarks, session-handoff-surfacer surfaces the handoff on cold start, and subagent-telemetry records per-delegation tier usage.
- **Ships:** 2 skills — foreman, handoff; 4 hooks — context-watermark, handoff-freshness-guard, session-handoff-surfacer, subagent-telemetry; 4 agents — builder, lead, reviewer, scout
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

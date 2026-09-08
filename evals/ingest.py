"""Populate the extender-db from this repo (idempotent, upsert-by-slug).

    python3 evals/ingest.py
    python3 evals/ingest.py --prune-dry-run   # report stale extenders, write nothing

What it loads:
  1. extenders + files   - every roster skill/agent/hook: parsed frontmatter (hooks carry
                           none), entrypoint body, full file inventory with content + sha256.
  2. distributions       - the pointer-based marketplace surface (ADR 0017): every plugin
                           in the root .claude-plugin/marketplace.json, with a members
                           relation resolved from its plugins/<id>/ symlink assembly.
  3. frontmatter_dimensions - one row per (kind, key): spec-known keys get their
                           requirement level; unknown observed keys land as `custom`.
  4. frameworks + framework_elements - seeded mental models (see FRAMEWORKS below).
  5. assessments         - mechanical checks (assessor `mechanical-v1`) of each skill
                           against the Anthropic Agent Skills spec, each agent against
                           the Claude Code subagent schema, and each hook against the
                           hook-dir-layout framework. Judgment-based assessments
                           (archetype tagging, section taxonomy) are left to humans/agents
                           writing rows with a different `assessor` value.
  6. sources             - trusted-publisher registry (SOURCES): curated extender publishers
                           with quality signals + trust tier (see EDB-15). externals link to
                           their publisher via extenders.source.
  7. externals.yaml rows - third-party extenders recorded by reference (origin `external`,
                           no file ingest) so curation queries cover the full curated surface.

A full run ends by pruning: an `extenders` row whose slug neither the roster nor
externals.yaml still defines is flagged `retired=True`. The row and every dependent are
retained — consumers filter retired units out — and a returning slug is un-retired by the
next upsert. See prune_extenders.
"""

import argparse
import ast
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

from check_roster import parse_roster  # noqa: E402
from pb import PB, esc  # noqa: E402

ROSTER = os.path.join(REPO, "primitives-core.yaml")
MARKETPLACE = os.path.join(REPO, ".claude-plugin", "marketplace.json")
PLUGINS_DIR = os.path.join(REPO, "plugins")
EXTERNALS = os.path.join(REPO, "externals.yaml")

# Roster types that become `extenders` rows. Shared by ingest_extenders and live_slugs so the
# writer and the prune predicate cannot disagree about what the tree defines.
ROSTER_EXTENDER_TYPES = ("skill", "agent", "hook")

LANG_BY_EXT = {
    ".py": "python", ".sh": "shell", ".js": "javascript", ".ts": "typescript",
    ".md": "markdown", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".txt": "text", ".css": "css", ".html": "html",
}

# Spec-known frontmatter keys: (kind, key) -> (requirement, description, framework_slug)
FRONTMATTER_SPEC = {
    ("skill", "name"): ("required", "Skill identifier; lowercase kebab, <=64 chars.", "anthropic-agent-skills"),
    ("skill", "description"): ("required", "What the skill does AND when to use it; the only always-in-context trigger surface (<=1024 chars).", "anthropic-agent-skills"),
    ("skill", "license"): ("optional", "License of the skill content.", "anthropic-agent-skills"),
    ("skill", "allowed-tools"): ("harness", "Claude Code: restricts tools available while the skill is active.", "anthropic-agent-skills"),
    ("agent", "name"): ("required", "Subagent identifier used to dispatch it.", "claude-code-subagents"),
    ("agent", "description"): ("required", "Delegation trigger: tells the main loop when to route work here.", "claude-code-subagents"),
    ("agent", "tools"): ("harness", "Least-privilege tool allowlist for the persona.", "claude-code-subagents"),
    ("agent", "model"): ("harness", "Default model tier the persona dispatches on.", "claude-code-subagents"),
    ("agent", "effort"): ("harness", "Default reasoning effort for the persona.", "claude-code-subagents"),
    ("agent", "maxTurns"): ("harness", "Turn budget cap for one dispatch.", "claude-code-subagents"),
    ("agent", "color"): ("harness", "Display color in the harness UI.", "claude-code-subagents"),
}

FRAMEWORKS = [
    {
        "slug": "anthropic-agent-skills",
        "name": "Anthropic Agent Skills structure",
        "source_org": "Anthropic",
        "source_url": "https://code.claude.com/docs/en/skills",
        "kind": "authoring-spec",
        "applies_to": ["skill"],
        "status": "active",
        "summary": "The published Agent Skills format: a folder with a SKILL.md entrypoint (YAML frontmatter name+description, markdown body) plus optional bundled resources, loaded via three-level progressive disclosure.",
        "elements": [
            ("skill-md-entrypoint", "SKILL.md entrypoint", "component", "The skill is a directory with SKILL.md at its root.", "SKILL.md exists at the folder root."),
            ("frontmatter-name", "name frontmatter", "rule", "Required identifier, lowercase kebab-case.", "frontmatter has `name`, <=64 chars."),
            ("frontmatter-description", "description frontmatter", "rule", "Required; states what the skill does and when to use it (trigger cues, third person). The only part always in context.", "frontmatter has `description`, <=1024 chars."),
            ("progressive-disclosure", "Progressive disclosure", "principle", "Three levels: metadata always in context; SKILL.md body loaded on trigger; bundled files read only as needed.", "Detail is pushed out of SKILL.md into bundled files rather than inlined."),
            ("references-dir", "references/ resources", "component", "Reference documents the agent reads as needed (level 3).", "references/ directory present with files."),
            ("scripts-dir", "scripts/ resources", "component", "Executable helpers for deterministic operations.", "scripts/ directory present with files."),
            ("assets-dir", "assets/ resources", "component", "Templates and files used in the skill's output.", "assets/ directory present with files."),
            ("concise-body", "Concise SKILL.md body", "rule", "Keep the body lean (guideline: under ~500 lines); move depth to references.", "SKILL.md is <=500 lines."),
            ("scripts-over-generation", "Scripts for deterministic work", "principle", "Operations that must be exact ship as scripts instead of freehand generation.", "Deterministic steps (rendering, API calls, transforms) are backed by scripts/."),
        ],
    },
    {
        "slug": "claude-code-subagents",
        "name": "Claude Code subagent schema",
        "source_org": "Anthropic",
        "source_url": "https://code.claude.com/docs/en/sub-agents",
        "kind": "schema-spec",
        "applies_to": ["agent"],
        "status": "active",
        "summary": "The subagent persona format: one markdown file whose frontmatter (name, description, tools, model) configures dispatch and whose body is the persona's system prompt.",
        "elements": [
            ("frontmatter-name", "name frontmatter", "rule", "Required dispatch identifier.", "frontmatter has `name`."),
            ("frontmatter-description", "description frontmatter", "rule", "Required; the delegation trigger the main loop matches against.", "frontmatter has `description`."),
            ("tools-allowlist", "tools allowlist", "dimension", "Least-privilege tool set for the persona.", "frontmatter has `tools`."),
            ("model-tier", "model tier", "dimension", "Persona pinned to a model/effort tier appropriate to its work.", "frontmatter has `model`."),
            ("system-prompt-body", "system-prompt body", "component", "The markdown body is the persona's system prompt.", "non-empty body below the frontmatter."),
            ("single-responsibility", "single responsibility", "principle", "One persona does one job; scope creep splits into a new persona.", "The body describes one coherent role, not several."),
        ],
    },
    {
        "slug": "hsb3-skill-archetypes",
        "name": "hsb3 skill archetypes",
        "source_org": "internal",
        "source_url": "",
        "kind": "archetype-set",
        "applies_to": ["skill"],
        "status": "candidate",
        "summary": "Internal working taxonomy of what a skill fundamentally IS, derived from the shipped catalog. Not mutually exclusive; assess a primary archetype per skill. Candidate status: revise as the catalog grows or if Anthropic publishes a canonical set.",
        "elements": [
            ("workflow-procedure", "Workflow / procedure", "archetype", "Encodes a repeatable multi-step procedure the agent executes end to end (e.g. handoff, private-fork, board-triage).", "Body is dominated by ordered steps/protocol the agent performs."),
            ("domain-expertise", "Domain expertise pack", "archetype", "Teaches the agent a domain, tool, or API it would otherwise guess at (e.g. obsidian-*, opencode-expertise, mermaid).", "Body is dominated by reference knowledge, not procedure."),
            ("deliverable-producer", "Deliverable producer", "archetype", "Produces a recurring artifact to a house standard (e.g. comms, pptx-themes, readme-value-and-proof).", "Output is a named artifact with format/quality rules."),
            ("guardrail-override", "Guardrail / override", "archetype", "Pins defaults or overrides behavior another surface would get wrong (e.g. house palette rules overriding a base skill).", "Body states precedence ('this skill wins') or bans defaults."),
            ("orchestration-delegation", "Orchestration / delegation", "archetype", "Structures how work is split across agents (e.g. foreman).", "Body is about dispatching/verifying other agents."),
            ("scaffold-auditor", "Scaffold / auditor", "archetype", "Stands up or audits repo/project structure against a documented standard (e.g. mise-en-place-scaffold, repo-compliance-audit).", "Body maps a standard onto a repo and creates/checks conformance."),
        ],
    },
    {
        "slug": "skill-section-taxonomy",
        "name": "SKILL.md section taxonomy",
        "source_org": "internal",
        "source_url": "",
        "kind": "section-taxonomy",
        "applies_to": ["skill"],
        "status": "candidate",
        "summary": "The recurring section types observed across SKILL.md bodies; used to analyze composition (which sections a skill carries) and as a checklist when authoring new ones.",
        "elements": [
            ("purpose-overview", "Purpose / overview", "section", "Opening statement of what the skill accomplishes.", "First section states the goal in 1-3 sentences."),
            ("trigger-when-to-use", "Trigger / when to use", "section", "Beyond frontmatter: explicit in-body invocation and skip conditions.", "A section enumerates use/skip cases."),
            ("prerequisites", "Prerequisites", "section", "CLIs, env state, or MCP servers that must exist first.", "A section lists dependencies before the workflow."),
            ("workflow-steps", "Workflow steps", "section", "Ordered procedure the agent follows.", "Numbered or staged steps present."),
            ("reference-pointers", "Reference pointers", "section", "Links into references/ or external docs for depth.", "Body points at bundled or external references."),
            ("examples", "Examples", "section", "Worked input/output or command examples.", "At least one concrete example block."),
            ("anti-patterns", "Anti-patterns / pitfalls", "section", "What NOT to do; known failure modes.", "A pitfalls/anti-pattern/common-mistakes section exists."),
            ("output-format", "Output format contract", "section", "Exact shape of the deliverable the skill produces.", "A section specifies the output's structure."),
            ("integration-partners", "Integration partners", "section", "Co-homed hooks/skills/agents this skill is load-bearing with.", "Body names sibling components and the shared contract."),
        ],
    },
    {
        "slug": "hook-dir-layout",
        "name": "Hook directory layout",
        "source_org": "internal",
        "source_url": "https://github.com/hsb3/dotfiles-agents/blob/dev/scripts/check_hook_layout.py",
        "kind": "schema-spec",
        "applies_to": ["hook"],
        "status": "active",
        "summary": "The ratified hook-dir layout enforced by scripts/check_hook_layout.py: each hook is a directory `hooks/<name>/` whose handler is `hook.py` (legacy flat `.sh` handlers and the old `hooks-handlers/` tree are banned), plus the stdlib-only rule from primitives-core/README.md ('hooks/<name>/ ... Claude-Code-only; stdlib-only (no pip/npm deps)').",
        "elements": [
            ("hook-py-entrypoint", "hook.py entrypoint", "component", "The hook's handler lives at `hook.py` inside its own `<name>/` directory (ratified layout).", "hook.py exists in the hook's directory."),
            ("python-only-handler", "Python-only handler", "rule", "No legacy `.sh` handler — check_hook_layout.py bans `.sh` files anywhere under a hook.", "No `.sh` file present in the hook's file inventory."),
            ("stdlib-only-imports", "stdlib-only imports", "rule", "The handler ships zero third-party dependencies (Python 3 stdlib only) — primitives-core/README.md's hook row.", "hook.py's top-level imports resolve to the Python stdlib only."),
            ("config-present", "config co-located", "component", "Optional `config.json`/`hook.json` sits beside `hook.py` in the same directory.", "config.json or hook.json present in the hook's directory (optional)."),
        ],
    },
    {
        "slug": "dotfiles-agents-roster-schema",
        "name": "dotfiles-agents roster entry schema",
        "source_org": "internal",
        "source_url": "https://github.com/hsb3/dotfiles-agents/blob/dev/primitives-core/README.md",
        "kind": "schema-spec",
        "applies_to": ["skill", "agent", "hook", "mcp"],
        "status": "active",
        "summary": "This repo's manifest schema (primitives-core.yaml): id/type/source/shelf/origin/disposition/targets/plugins/requires, with origin:sourced requiring upstream+ref. Enforced by scripts/check_roster.py.",
        "elements": [
            ("shelf", "shelf", "dimension", "core vs toggle shelving.", "Roster entry carries shelf."),
            ("origin-provenance", "origin provenance", "rule", "authored vs sourced is immutable; sourced requires non-null upstream+ref.", "origin:sourced entries have upstream and ref."),
            ("disposition", "disposition", "dimension", "qualified | grandfathered-pending-use | demoted | untriaged.", "Roster entry carries disposition."),
            ("plugin-membership", "plugin membership", "dimension", "Which bundles ship the primitive (plugins: []).", "Roster entry lists its bundles."),
            ("requires-capabilities", "requires capabilities", "dimension", "Capability words {hooks, local-mcp, hosted-mcp} + cli:/env: dependency declarations.", "Dependencies declared in requires, not prose-only."),
        ],
    },
    {
        # Authored 2026-07-20 with Henry (EDB-13). Deliverable-altitude ("one nameable
        # deliverable you'd hand a single agent session"), all-work scope. Elements are
        # the JOBS his work needs done, phrased solution-agnostically; an assessment
        # (extender x job) records whether an extender SERVES that job. Candidate: refines
        # to a successor row on supersession, never overwritten. category = job family.
        "slug": "hsb3-jobs-to-be-done",
        "name": "hsb3 jobs-to-be-done taxonomy",
        "source_org": "internal",
        "source_url": "",
        "kind": "job-taxonomy",
        "applies_to": ["any"],
        "status": "candidate",
        "summary": "The jobs Henry's agent work needs done, at deliverable altitude and spanning all work (software, exec/comms, research, knowledge-tooling, meta). Elements are solution-agnostic outcomes; W9 maps every extender to the jobs it serves so coverage gaps and overlaps become queries. Authored 2026-07-20 (EDB-13).",
        "elements": [
            # A - Understand & research
            ("orient-codebase", "Orient in an unfamiliar codebase", "job", "When facing a system I don't know, get a reliable map of where things live and how they fit before acting.", "Serves this job if it helps an agent locate, inventory, or explain an unfamiliar codebase or system before changes are made.", "understand-research"),
            ("research-question", "Research an open question into a cited answer", "job", "When the answer lives outside the repo, gather multiple sources, verify them, and synthesize a cited result.", "Serves if it drives external information-gathering with source-grounding or fact verification.", "understand-research"),
            ("consult-domain-expertise", "Consult domain expertise on demand", "job", "When working in a specific technology, get its patterns and pitfalls in-session instead of guessing.", "Serves if its primary value is teaching or reference knowledge of a domain, tool, or API.", "understand-research"),
            # B - Build software
            ("plan-work", "Plan a piece of work", "job", "Turn a goal into a sequenced, scoped, source-grounded plan before building.", "Serves if it produces an actionable plan or decomposition of work not yet built.", "build-software"),
            ("implement-change", "Implement a bounded change", "job", "Build a specified feature or fix within an owned file scope against acceptance criteria.", "Serves if it writes or edits product code to satisfy a defined change.", "build-software"),
            ("improve-code", "Improve existing code without changing behavior", "job", "Refactor, simplify, or tidy working code while preserving its behavior.", "Serves if it restructures existing code for quality without adding features.", "build-software"),
            ("migrate-at-scale", "Apply one change across many sites", "job", "Perform a single mechanical transformation across a large surface, with verification.", "Serves if it drives a repeated or bulk transform across many files or repos.", "build-software"),
            # C - Assure quality
            ("review-change", "Review a change for defects before it lands", "job", "Find correctness, security, or quality defects in a diff before it merges.", "Serves if it inspects a change or diff and reports defects or risks.", "assure-quality"),
            ("verify-works", "Verify a change actually works", "job", "Drive the real system and observe the change behaving as intended.", "Serves if it exercises the running system to confirm behavior, beyond static checks.", "assure-quality"),
            # D - Orchestrate & sustain
            ("delegate-large-job", "Delegate a large job across agents", "job", "Decompose a big task, fan it out to agents, and reconcile the results.", "Serves if it structures multi-agent decomposition, dispatch, or reconciliation.", "orchestrate-sustain"),
            ("sustain-continuity", "Maintain project continuity across sessions", "job", "Capture load-bearing state so a fresh or cold session can pick up the work.", "Serves if it externalizes session state for pickup or handoff.", "orchestrate-sustain"),
            ("manage-backlog", "Manage a backlog or project board", "job", "Triage, prioritize, sequence, and gate the work items.", "Serves if it operates or triages an issue or project backlog.", "orchestrate-sustain"),
            # E - Produce deliverables for people
            ("produce-briefing", "Produce a stakeholder briefing", "job", "Deliver a status or readout communication for a human audience.", "Serves if its output is a briefing, status, or readout artifact.", "produce-deliverables"),
            ("produce-deck", "Produce a slide deck", "job", "Deliver a themed slide presentation.", "Serves if its output is a presentation or slide deck.", "produce-deliverables"),
            ("produce-diagram", "Produce a diagram or architecture visual", "job", "Deliver a structural, architecture, or flow visual.", "Serves if its output is a diagram (flowchart, ERD, architecture, sketch).", "produce-deliverables"),
            ("produce-dataviz", "Produce a data visualization", "job", "Deliver a chart or data-driven visual.", "Serves if its output is a chart, plot, or dashboard from data.", "produce-deliverables"),
            ("produce-readme", "Produce a README or project pitch", "job", "Deliver a README or pitch that communicates a project to its users.", "Serves if its output is user-facing project documentation or a pitch.", "produce-deliverables"),
            # F - Govern the estate
            ("enforce-standards", "Enforce and scaffold repo standards", "job", "Audit or scaffold a repo against a documented meta-structure standard.", "Serves if it checks or creates repo or project structure against a standard.", "govern-estate"),
            ("govern-external-code", "Govern external or OSS code", "job", "Bring in and steward third-party code (fork, mirror, divergence tracking).", "Serves if it manages inbound external or OSS code and its governance.", "govern-estate"),
            ("get-owner-signoff", "Get owner decision or sign-off", "job", "Surface a batch of decisions to the owner for approval, outside chat.", "Serves if it collects owner decisions or approvals as a workflow.", "govern-estate"),
            # G - Extend the tooling itself (meta)
            ("author-evaluate-extender", "Author, evaluate, or curate an agent extender", "job", "Build, judge, or curate a skill, agent, or hook and prove it earns its place.", "Serves if it creates, evaluates, or curates agent extenders themselves.", "extend-tooling"),
            ("configure-harness", "Configure the agent harness", "job", "Set up settings, hooks, keybindings, or permissions of the agent environment.", "Serves if it configures the harness or runtime (settings, hooks, keybindings, permissions).", "extend-tooling"),
            ("integrate-knowledge-system", "Integrate a personal-knowledge system", "job", "Build or automate integrations for a knowledge tool such as an Obsidian vault or plugins.", "Serves if it builds or automates integration with a personal-knowledge system.", "extend-tooling"),
            ("operate-browser-ui", "Operate a browser or external UI", "job", "Drive a browser or external UI to complete a task the CLI cannot.", "Serves if it automates a browser or GUI to accomplish work.", "extend-tooling"),
        ],
    },
    {
        # Adopted 2026-07-20 (EDB-18, roadmap M4) as the QUANTITATIVE eval+improvement
        # methodology for W8/M5/M6 — verified by reading the source (MIT). Elements are the
        # principles/components we adopt.
        "slug": "skillopt",
        "name": "SkillOpt skill-optimization methodology",
        "source_org": "Microsoft",
        "source_url": "https://github.com/microsoft/SkillOpt",
        "kind": "evaluation-methodology",
        "applies_to": ["skill", "agent", "command"],
        "status": "candidate",
        "summary": "Microsoft SkillOpt: treats a skill document as trainable state and improves it via scored rollouts against a task set with a machine-checkable reward, keeping an edit only when the candidate strictly beats the current skill on a held-out split. Cheap-model-native (openai_compatible backend -> Ollama/OpenRouter/local). Adopted as the quantitative eval+improvement methodology (W8/M5/M6). MIT.",
        "elements": [
            ("scored-rollout", "Scored rollout", "principle", "Evaluate a skill by running it as the system prompt/skill over a task set and scoring each rollout with a checkable reward (hard = exact-match 0/1, soft = partial 0-1).", "Eval scores a skill against a task set with a per-item reward, not by vibes."),
            ("validation-gated-edit", "Validation-gated edit", "principle", "Accept a proposed skill edit only if the candidate STRICTLY beats the current skill on a held-out selection split; otherwise revert.", "Improvements are gated on a held-out score delta, never asserted."),
            ("authored-benchmark-required", "Authored benchmark required", "rule", "There is no generic 'grade my skill' - you author a task set plus a scorer (the reward IS the rubric) per skill/job.", "Each evaluated skill has an authored task set with a machine-checkable reward."),
            ("cheap-model-substrate", "Cheap-model substrate", "component", "Runs against any OpenAI-compatible endpoint (Ollama/OpenRouter/vLLM/local); target and optimizer roles configured independently, so evals are cheap.", "Eval runs on inexpensive/free models via an openai-compatible endpoint."),
            ("transcript-mined-improvement", "Transcript-mined improvement (Sleep)", "component", "skillopt_sleep harvests real Claude Code/Codex transcripts, mines checkable tasks, and gate-improves the skill offline with human-in-the-loop adopt.", "Improvement can be sourced from real usage transcripts, gated before adoption."),
        ],
    },
    {
        # Adopted 2026-07-20 (EDB-18, roadmap M4) as the QUALITATIVE conformance-judging
        # pattern — maps onto our existing `assessments`; our W1 judged pass is a lighter
        # version. Verified by reading the source (Apache-2.0).
        "slug": "closedloop-judges",
        "name": "ClosedLoop judges + CaseScore rubric pattern",
        "source_org": "ClosedLoop.AI",
        "source_url": "https://github.com/closedloop-ai/claude-plugins",
        "kind": "evaluation-methodology",
        "applies_to": ["skill", "agent", "hook", "mcp", "command", "plugin"],
        "status": "candidate",
        "summary": "LLM-as-judge conformance pattern: each quality dimension is a judge prompt file carrying a deterministic rubric (severity table -> numeric formula -> threshold -> worked examples) that emits a strict CaseScore verdict; lightweight {id, input, expected_outcome} eval cases; a self-learning loop that persists validated patterns and injects them into future runs. Adopted as the qualitative conformance-judging pattern (borrowed onto our assessments). Apache-2.0.",
        "elements": [
            ("judge-as-prompt-rubric", "Judge-as-prompt with embedded rubric", "component", "Each quality dimension is one LLM judge defined by a prompt file carrying a deterministic rubric: severity table, numeric scoring formula, threshold, and worked pass/fail/error examples.", "A conformance judge carries an explicit reproducible rubric, not vibes."),
            ("casescore-verdict", "CaseScore verdict contract", "component", "A judge emits a strict verdict {final_status: pass/fail/error, metrics:[{name, threshold, score, justification}]}; the error state is excluded from aggregates so a crashed judge does not tank the grade.", "Verdicts are a validated schema with a first-class error state."),
            ("lightweight-eval-case", "Lightweight eval case", "component", "An eval case is {id, input, expected_outcome} (JSONL) plus a 1-5 multi-dimension rubric - the cheapest hand-authorable golden set.", "Eval cases are small, declarative, and hand-authorable."),
            ("self-learning-loop", "Self-learning feedback loop", "principle", "Capture learnings (decision-tree gated) -> dedup/validate -> persist with deterministic success rates from an outcomes log -> inject top-N relevant patterns into future agent runs via a hook; citation-verified anti-gaming.", "Improvements are captured, validated deterministically, and fed back into future runs."),
        ],
    },
]


# Trusted-source (publisher) registry — EDB-15. Seeded 2026-07-20 from an adversarially
# verified research pass (deep-research, 103 agents, 22 confirmed claims; every row grounded
# in a fetched primary source, see evidence_url). Publisher-level unit. trust_tier semantics:
# trusted = vetted, ships evals + active + clean license, vendor/use directly; provisional =
# promising but unproven (reference, or vendor only after our own eval); watch = quality
# uncertain, comparator baseline only ("first search hit"); avoid = red flags. Idempotent
# (upsert by slug). Key nuance from the research: "publishes_evals" means eval TOOLING or
# METHODOLOGY or self-authored/behavioral tests — NO publisher ships an objective
# cross-publisher benchmark leaderboard ranking third-party extenders.
SOURCES = [
    {
        "slug": "anthropic", "name": "Anthropic", "url": "https://github.com/anthropics",
        "publisher_kind": "first-party",
        "publishes": ["skill", "plugin", "agent", "command", "hook", "mcp"],
        "trust_tier": "trusted", "publishes_evals": True, "maintenance": "active",
        "license": "Apache-2.0",
        "adoption_signal": "anthropics/skills ~163k stars; anthropics/claude-code ~138k stars (2026-07)",
        "rationale": "First-party. Ships skills (anthropics/skills), plugin-dev skills for every extender type (anthropics/claude-code), the claude-plugins-official marketplace, and first-party eval tooling — skill-creator writes evals.json test cases and a benchmark mode reporting pass rate / time / tokens. The eval tooling is the standout quality signal.",
        "evidence_url": "https://github.com/anthropics/skills | https://github.com/anthropics/claude-code/tree/main/plugins/plugin-dev/skills | https://github.com/anthropics/claude-plugins-official | https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills",
        "status": "active",
        "notes": "skill-creator evals are AUTHOR tooling (user-authored cases), not an Anthropic-published cross-publisher benchmark dataset. claude-plugins-official 'curation' = submission approval + automated security review, not per-plugin functional vetting; it also hosts quality/security-gated third-party external_plugins.",
    },
    {
        "slug": "mcp-registry", "name": "Official MCP Registry", "url": "https://modelcontextprotocol.io/registry/about",
        "publisher_kind": "marketplace", "publishes": ["mcp"],
        "trust_tier": "trusted", "publishes_evals": False, "maintenance": "active",
        "license": "",
        "adoption_signal": "Backed by Anthropic, GitHub, PulseMCP, Microsoft; under Linux Foundation governance",
        "rationale": "Publisher-trust infrastructure for MCP servers: reverse-DNS namespace authentication (io.github.user/server) tied to verified GitHub accounts/domains, so only the legitimate owner can publish. Best trust anchor for the MCP-server slice — identity trust, not code safety or evals.",
        "evidence_url": "https://modelcontextprotocol.io/registry/about",
        "status": "candidate",
        "notes": "In 'preview'. Namespace auth attests IDENTITY, not code safety; code security is delegated to package registries + downstream scanners.",
    },
    {
        "slug": "obra-superpowers", "name": "Jesse Vincent (obra) - superpowers", "url": "https://github.com/obra/superpowers",
        "publisher_kind": "individual", "publishes": ["skill", "plugin"],
        "trust_tier": "provisional", "publishes_evals": True, "maintenance": "unknown",
        "license": "",
        "adoption_signal": "",
        "rationale": "Ships a dedicated behavioral eval harness: skill-behavior tests run via the 'drill eval harness' from the companion superpowers-evals project (drives real coding-agent CLIs through a QA agent, grading workflow compliance + deterministic post-checks). The strongest INDEPENDENT (non-self-scored) eval approach among individual authors — top promotion candidate.",
        "evidence_url": "https://github.com/obra/superpowers | https://github.com/prime-radiant-inc/superpowers-evals",
        "status": "active",
        "notes": "Eval repo (superpowers-evals) sits under the prime-radiant-inc org (same author) — 'individual' is approximate. License/adoption not captured in the research pass.",
    },
    {
        "slug": "daymade", "name": "daymade", "url": "https://github.com/daymade/claude-code-skills",
        "publisher_kind": "individual", "publishes": ["skill"],
        "trust_tier": "provisional", "publishes_evals": True, "maintenance": "active",
        "license": "MIT", "adoption_signal": "~1.3k stars, 211 forks",
        "rationale": "Individual-authored skills marketplace shipping a real eval pipeline (evals/evals.json, grader/comparator agents, eval-viewer) and a README scorecard. Ships evals — but its headline 65/80-vs-42/80 result is a SELF-SCORED fork-vs-official comparison (inherently biased).",
        "evidence_url": "https://github.com/daymade/claude-code-skills",
        "status": "active",
        "notes": "Provisional: ships evals (good signal) but self-comparison bias; single-user account.",
    },
    {
        "slug": "vinnie357", "name": "Vinnie Mazza (vinnie357)", "url": "https://github.com/vinnie357/claude-skills",
        "publisher_kind": "individual", "publishes": ["skill"],
        "trust_tier": "provisional", "publishes_evals": True, "maintenance": "active",
        "license": "MIT", "adoption_signal": "~21 stars (modest)",
        "rationale": "Ships claude-skills-benchmark: a concrete, falsifiable eval methodology - A/B blind comparator, multi-model pass-rate targets (Haiku 70%+ / Sonnet 85%+ / Opus 95%+), activation targets (90%+ true-positive / <5% false-positive), an 11+ check static scorecard, and a /benchmark-skills command.",
        "evidence_url": "https://github.com/vinnie357/claude-skills",
        "status": "active",
        "notes": "Benchmark TOOLING/methodology, not published result datasets. Low adoption.",
    },
    {
        "slug": "coleam00", "name": "Cole Medin (coleam00)", "url": "https://github.com/coleam00/excalidraw-diagram-skill",
        "publisher_kind": "individual", "publishes": ["skill"],
        "trust_tier": "provisional", "publishes_evals": False, "maintenance": "unknown",
        "license": "", "adoption_signal": "",
        "rationale": "Vendored by us: excalidraw-diagram-skill is our excalidraw external. Not independently vetted in the 2026-07-20 research pass - quality/eval signals TBD.",
        "evidence_url": "https://github.com/coleam00/excalidraw-diagram-skill",
        "status": "candidate",
        "notes": "Added because we already source from this publisher; tier is conservative pending a real vetting pass.",
    },
    {
        "slug": "skills-sh", "name": "skills.sh (Vercel Labs)", "url": "https://skills.sh/",
        "publisher_kind": "marketplace", "publishes": ["skill"],
        "trust_tier": "watch", "publishes_evals": False, "maintenance": "active",
        "license": "",
        "adoption_signal": "~953,593 all-time installs (leaderboard, 2026-07); lists Anthropic, Vercel, Microsoft, Firebase, Supabase, etc.",
        "rationale": "Dominant community aggregator and 'first search hit' baseline (npx skills add). Ranks by install count; only quality layer is security-audit grades (Gen Agent Trust Hub / Socket / Snyk), NOT functional evals.",
        "evidence_url": "https://skills.sh/ | https://www.skills.sh/audits",
        "status": "active",
        "notes": "Primary W8 comparator baseline (the skills.sh first hit). Install counts self-reported and time-sensitive.",
    },
    {
        "slug": "tonsofskills", "name": "Tons of Skills (jeremylongshore)", "url": "https://github.com/jeremylongshore/claude-code-plugins-plus-skills",
        "publisher_kind": "community-collection",
        "publishes": ["skill", "plugin", "agent", "mcp", "command", "hook"],
        "trust_tier": "watch", "publishes_evals": False, "maintenance": "active",
        "license": "MIT",
        "adoption_signal": "~2.5k stars; self-reported ~2,810 skills / 425 plugins / 200 agents",
        "rationale": "Large community-collection marketplace (tonsofskills.com + ccpi CLI). Scale over curation; only a self-defined 100-point rubric + validation scripts, no functional evals. Comparator baseline.",
        "evidence_url": "https://github.com/jeremylongshore/claude-code-plugins-plus-skills",
        "status": "active",
        "notes": "Self-reported badge counts are internally inconsistent (425/2,810 vs a 470/3,677 category table).",
    },
    {
        "slug": "jeffallan", "name": "Jeff Allan (jeffallan)", "url": "https://github.com/jeffallan/claude-skills",
        "publisher_kind": "individual", "publishes": ["skill", "command", "plugin"],
        "trust_tier": "provisional", "publishes_evals": False, "maintenance": "active",
        "license": "MIT", "adoption_signal": "~10.7k stars; 66 skills + 9 commands (v0.4.15, May 2026)",
        "rationale": "High-adoption individual-authored Claude Code skills collection (full-stack dev). No published evals found - adoption is the only quality signal, so provisional pending vetting / comparator use.",
        "evidence_url": "https://github.com/jeffallan/claude-skills",
        "status": "active",
        "notes": "Author: Principal Consultant at Synergetic Solutions. Suggested by Henry (2026-07-20); candidate comparator/vendor after a vetting pass.",
    },
    {
        "slug": "closedloop-ai", "name": "ClosedLoop.AI", "url": "https://github.com/closedloop-ai/claude-plugins",
        "publisher_kind": "research-lab", "publishes": ["plugin", "skill", "agent", "command", "hook"],
        "trust_tier": "provisional", "publishes_evals": True, "maintenance": "active",
        "license": "Apache-2.0", "adoption_signal": "~101 stars; company-backed (commercial platform + OSS)",
        "rationale": "Company-published Claude Code plugin suite for multi-agent SDLC (code, code-review, judges, platform, self-learning). Ships a real LLM-as-judge eval framework (CaseScore verdicts + deterministic rubrics) and a working self-learning loop; small human eval set (evals/code-review). Trusted-referred (Henry, 2026-07-20). Provisional: strong eval machinery, low adoption.",
        "evidence_url": "https://github.com/closedloop-ai/claude-plugins",
        "status": "active",
        "notes": "Its judges + self-learning designs are adopted as doctrine (see framework `closedloop-judges`). publisher_kind research-lab = commercial AI-platform vendor.",
    },
]

# Map an external's upstream repo URL to its publisher (sources.slug), by org prefix.
SOURCE_BY_UPSTREAM = [
    ("https://github.com/anthropics/", "anthropic"),
    ("https://github.com/coleam00/", "coleam00"),
]


def source_for_upstream(url):
    """Return the sources.slug whose org-prefix matches this upstream URL, else ''."""
    for prefix, slug in SOURCE_BY_UPSTREAM:
        if url.startswith(prefix):
            return slug
    return ""


# ---------- parsing helpers ----------

def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].replace('\\"', '"')
    return v


def parse_list(v):
    """'[a, b]' -> ['a','b']; '' / 'null' / '[]' -> []."""
    v = (v or "").strip()
    if v in ("", "null", "[]", "~"):
        return []
    if v.startswith("[") and v.endswith("]"):
        return [unquote(x) for x in v[1:-1].split(",") if x.strip()]
    return [unquote(v)]


def parse_frontmatter(text):
    """Flat `key: value` frontmatter between --- fences. Returns (dict, body).
    Multi-line/nested YAML values are out of scope for the shipped extenders (all flat)."""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        km = re.match(r"^([\w][\w.-]*):\s*(.*)$", line)
        if km:
            val = unquote(km.group(2))
            if re.fullmatch(r"-?\d+", val):
                val = int(val)
            elif val in ("true", "false"):
                val = val == "true"
            fm[km.group(1)] = val
    return fm, text[m.end():]


def classify_role(relpath, entry_file):
    if relpath == entry_file:
        return "entrypoint"
    top = relpath.split("/")[0]
    base = os.path.basename(relpath)
    if top == "references":
        return "reference"
    if top == "scripts":
        return "script"
    if top == "assets":
        return "asset"
    if top in ("templates",):
        return "template"
    if top in ("evals", "eval"):
        return "eval"
    if base.upper().startswith("LICENSE"):
        return "license"
    if base.lower().endswith((".md", ".txt")):
        return "doc"
    if base.lower().endswith((".json", ".yaml", ".yml", ".toml")):
        return "config"
    return "other"


def scan_files(abs_source, entry_file):
    """Yield dicts for every file under a skill dir (or the single agent file)."""
    out = []
    if os.path.isfile(abs_source):
        paths = [(abs_source, os.path.basename(abs_source))]
    else:
        paths = []
        for root, dirs, names in os.walk(abs_source):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for n in sorted(names):
                if n.startswith("."):
                    continue
                ap = os.path.join(root, n)
                paths.append((ap, os.path.relpath(ap, abs_source)))
    for ap, rel in sorted(paths, key=lambda t: t[1]):
        with open(ap, "rb") as fh:
            raw = fh.read()
        try:
            content = raw.decode("utf-8")
            is_binary = False
        except UnicodeDecodeError:
            content, is_binary = "", True
        out.append({
            "relpath": rel,
            "role": classify_role(rel, entry_file),
            "content": content,
            "is_binary": is_binary,
            "size_bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "language": LANG_BY_EXT.get(os.path.splitext(rel)[1].lower(), ""),
        })
    return out


def parse_externals(path):
    """Parse externals.yaml's `externals:` list into dicts. Tailored line parser (see
    parse_roster) — no pyyaml, controlled flat-key format only."""
    entries, cur = [], None
    in_list = False
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if re.match(r"^externals:\s*$", line):
            in_list = True
            continue
        if not in_list:
            continue
        if re.match(r"^\S", line):  # a later top-level key ends the list
            in_list = False
            continue
        m = re.match(r"^  - id:\s*(.*)$", line)
        if m:
            if cur is not None:
                entries.append(cur)
            cur = {"id": unquote(m.group(1))}
            continue
        m = re.match(r"^    (\w+):\s*(.*)$", line)
        if m and cur is not None:
            cur[m.group(1)] = unquote(m.group(2))
    if cur is not None:
        entries.append(cur)
    return entries


def stdlib_import_violations(source):
    """Return the sorted list of top-level (module-level) import roots in `source` that are
    NOT in the Python 3 stdlib (sys.stdlib_module_names, 3.10+). None if `source` fails to
    parse as Python."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    stdlib = sys.stdlib_module_names
    bad = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in stdlib:
                    bad.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                root = node.module.split(".")[0]
                if root not in stdlib:
                    bad.add(node.module)
    return sorted(bad)


# ---------- ingest passes ----------

def ingest_frameworks(pb):
    fw_ids, el_ids = {}, {}
    for fw in FRAMEWORKS:
        body = {k: fw[k] for k in ("slug", "name", "source_org", "source_url", "kind", "applies_to", "status", "summary")}
        rec, created = pb.upsert("frameworks", f"slug='{esc(fw['slug'])}'", body)
        fw_ids[fw["slug"]] = rec["id"]
        for i, el_spec in enumerate(fw["elements"]):
            # Element tuple is (slug, name, ekind, desc, criteria[, category]); category is
            # optional so the pre-existing 5-tuple frameworks stay valid unchanged.
            slug, name, ekind, desc, criteria = el_spec[:5]
            category = el_spec[5] if len(el_spec) > 5 else ""
            el, _ = pb.upsert(
                "framework_elements",
                f"framework='{rec['id']}' && slug='{esc(slug)}'",
                {"framework": rec["id"], "slug": slug, "name": name,
                 "element_kind": ekind, "description": desc, "criteria": criteria,
                 "category": category, "sort_order": i},
            )
            el_ids[(fw["slug"], slug)] = el["id"]
        print(f"framework {'created' if created else 'updated'}: {fw['slug']} ({len(fw['elements'])} elements)")
    return fw_ids, el_ids


def ingest_extenders(pb):
    entries = [e for e in parse_roster(ROSTER) if e.get("type") in ROSTER_EXTENDER_TYPES]
    ext_ids = {}      # roster id -> record id
    ext_meta = {}     # roster id -> dict used by later passes
    for e in entries:
        kind = e["type"]
        source = e["source"]
        abs_source = os.path.join(REPO, source)
        if kind == "skill":
            entry_file = "SKILL.md"
        elif kind == "hook":
            entry_file = "hook.py"
        else:
            entry_file = os.path.basename(source)
        files = scan_files(abs_source, entry_file)
        entry = next((f for f in files if f["role"] == "entrypoint"), None)
        if kind == "hook":
            # Hooks carry no frontmatter (hook.py is plain Python, not a fenced doc) — the
            # roster summary is the description source instead (see below).
            fm, body = {}, ""
        else:
            fm, body = parse_frontmatter(entry["content"]) if entry else ({}, "")
        upstream = unquote(e.get("upstream", "")) if e.get("upstream", "null") != "null" else ""
        rec, created = pb.upsert("extenders", f"slug='{esc(e['id'])}'", {
            "slug": e["id"],
            "name": str(fm.get("name", e["id"])),
            "kind": kind,
            "description": str(fm.get("description", "")) or unquote(e.get("summary", "")),
            "origin": e.get("origin", ""),
            "upstream": upstream,
            "upstream_ref": unquote(e.get("ref", "")) if e.get("ref", "null") != "null" else "",
            "repo_path": source,
            "shelf": e.get("shelf", ""),
            "disposition": e.get("disposition", ""),
            "requires": parse_list(e.get("requires", "")),
            "frontmatter": fm,
            "body": body,
            "entry_file": entry_file,
            "file_count": len(files),
            "total_bytes": sum(f["size_bytes"] for f in files),
            "word_count": len(body.split()),
            "retired": False,
        })
        ext_ids[e["id"]] = rec["id"]
        ext_meta[e["id"]] = {
            "kind": kind, "fm": fm, "body": body, "files": files,
            "plugins": parse_list(e.get("plugins", "")), "record": rec,
        }
        # files: upsert current, delete stale
        current = set()
        for f in files:
            pb.upsert("files", f"extender='{rec['id']}' && relpath='{esc(f['relpath'])}'",
                      {**f, "extender": rec["id"]})
            current.add(f["relpath"])
        for stale in pb.list_all("files", f"extender='{rec['id']}'"):
            if stale["relpath"] not in current:
                pb.delete("files", stale["id"])
        print(f"extender {'created' if created else 'updated'}: {kind}/{e['id']} ({len(files)} files)")
    return ext_ids, ext_meta


def _assembly_members(plugin_id):
    """Member primitive slugs of one plugins/<id>/ symlink assembly (ADR 0017): the symlink
    names under skills/, agents/ (.md stripped), and hooks/ — membership IS the assembly."""
    members = []
    proot = os.path.join(PLUGINS_DIR, plugin_id)
    for sub in ("skills", "agents", "hooks"):
        d = os.path.join(proot, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if os.path.islink(os.path.join(d, name)):
                members.append(name[:-3] if name.endswith(".md") else name)
    return members


def ingest_distributions(pb, ext_ids, ext_meta):
    """Distribution rows from the pointer surface (ADR 0017): the root marketplace.json
    lists every plugin; membership comes from its symlink assembly. A one-skill assembly
    whose sole member is its own id is a standalone; everything else is a bundle. (The
    pre-0017 plugins.yaml/skill-catalog.yaml kinds and `<id>-standalone` rows are
    superseded; re-ingest reshapes existing rows accordingly.)"""
    with open(MARKETPLACE, encoding="utf-8") as fh:
        market = json.load(fh)
    for entry in market.get("plugins", []):
        pid = entry["name"]
        member_slugs = _assembly_members(pid)
        members = [ext_ids[s] for s in member_slugs if s in ext_ids]
        kind = "standalone" if member_slugs == [pid] else "bundle"
        pb.upsert("distributions", f"slug='{esc(pid)}'", {
            "slug": pid, "kind": kind,
            "version": entry.get("version", ""), "description": entry.get("description", ""),
            "members": members,
        })
        print(f"distribution: {pid} ({len(members)} members)")


def ingest_sources(pb):
    """Seed the trusted-source (publisher) registry from SOURCES. Idempotent (upsert by
    slug). Returns {slug: record_id} so externals can link their publisher."""
    src_ids = {}
    for s in SOURCES:
        rec, created = pb.upsert("sources", f"slug='{esc(s['slug'])}'", dict(s))
        src_ids[s["slug"]] = rec["id"]
    print(f"sources: {len(SOURCES)}")
    return src_ids


def ingest_externals(pb, src_ids):
    """externals.yaml -> extenders rows with origin `external` (no file scan, no
    distribution membership — third-party items are recorded by reference only, per
    ADR 0015 / the README expansion path). Links each to its publisher (sources)."""
    n = 0
    for e in parse_externals(EXTERNALS):
        src_slug = source_for_upstream(e.get("upstream", ""))
        rec, created = pb.upsert("extenders", f"slug='{esc(e['id'])}'", {
            "slug": e["id"],
            "name": e["id"],
            "kind": e.get("kind", ""),
            "description": e.get("provides", ""),
            "origin": "external",
            "source": src_ids.get(src_slug, ""),
            "upstream": e.get("upstream", ""),
            "upstream_ref": e.get("ref", ""),
            "repo_path": "",
            "shelf": "",
            "disposition": "",
            "requires": [],
            "frontmatter": {},
            "body": "",
            "entry_file": "",
            "file_count": 0,
            "total_bytes": 0,
            "word_count": 0,
            "retired": False,
        })
        print(f"external {'created' if created else 'updated'}: {e['id']} ({e.get('kind', '')})")
        n += 1
    print(f"externals: {n}")


def live_slugs():
    """Every slug the tree currently defines: the union of what both `extenders` writers
    produce. A roster-only predicate would treat every externals.yaml row as stale."""
    roster = {e["id"] for e in parse_roster(ROSTER) if e.get("type") in ROSTER_EXTENDER_TYPES}
    return roster | {e["id"] for e in parse_externals(EXTERNALS)}


def prune_extenders(pb, slugs, dry_run=False):
    """Flag every `extenders` row whose slug is no longer in `slugs` with `retired=True`.

    Nothing is deleted and no dependent row is read or written, so this pass keeps
    PROCEDURES.md's "never touches non-mechanical assessors or `job_coverage`/`relationships`"
    invariant: a unit's judged and coverage assessments, its relationship edges and the
    `eval_responses` naming it are all non-regenerable, and only `files` plus assessor
    `mechanical-v1` would ever come back. Consumers drop retired units in Python
    (report.py, load_coverage.py, load_eval_run.py, load_assessments.py), and a slug that
    reappears in the tree is un-retired by the next upsert, which writes `retired=False`.
    """
    verb = "to retire" if dry_run else "retired"
    n = 0
    for rec in pb.list_all("extenders"):
        if rec["slug"] in slugs or rec.get("retired"):
            continue
        if not dry_run:
            pb.update("extenders", rec["id"], {"retired": True})
        print(f"extender {verb}: {rec['kind']}/{rec['slug']}")
        n += 1
    print(f"extenders {verb}: {n}")


def ingest_dimensions(pb, ext_meta, fw_ids):
    counts = {}
    for m in ext_meta.values():
        for key in m["fm"]:
            counts[(m["kind"], key)] = counts.get((m["kind"], key), 0) + 1
    keys = set(counts) | set(FRONTMATTER_SPEC)
    for kind, key in sorted(keys):
        req, desc, fw_slug = FRONTMATTER_SPEC.get((kind, key), ("custom", "", None))
        pb.upsert("frontmatter_dimensions",
                  f"key='{esc(key)}' && applies_to='{esc(kind)}'", {
                      "key": key, "applies_to": kind, "requirement": req,
                      "description": desc,
                      "spec_framework": fw_ids.get(fw_slug, "") if fw_slug else "",
                      "observed_count": counts.get((kind, key), 0),
                  })
    print(f"frontmatter dimensions: {len(keys)}")


def assess(pb, ext_rec_id, fw_id, el_id, verdict, evidence):
    pb.upsert(
        "assessments",
        f"extender='{ext_rec_id}' && framework='{fw_id}' && element='{el_id}' && assessor='mechanical-v1'",
        {"extender": ext_rec_id, "framework": fw_id, "element": el_id,
         "verdict": verdict, "evidence": evidence, "assessor": "mechanical-v1"},
    )


def ingest_assessments(pb, ext_ids, ext_meta, fw_ids, el_ids):
    n = 0
    for rid, m in ext_meta.items():
        ext = ext_ids[rid]
        fm, files = m["fm"], m["files"]
        if m["kind"] == "skill":
            fw = fw_ids["anthropic-agent-skills"]
            def el(s):
                return el_ids[("anthropic-agent-skills", s)]
            has_entry = any(f["role"] == "entrypoint" for f in files)
            assess(pb, ext, fw, el("skill-md-entrypoint"),
                   "present" if has_entry else "absent",
                   "SKILL.md at folder root" if has_entry else "no SKILL.md found")
            name = str(fm.get("name", ""))
            assess(pb, ext, fw, el("frontmatter-name"),
                   "present" if name and len(name) <= 64 else ("partial" if name else "absent"),
                   f"name={name!r} ({len(name)} chars)")
            desc = str(fm.get("description", ""))
            assess(pb, ext, fw, el("frontmatter-description"),
                   "present" if desc and len(desc) <= 1024 else ("partial" if desc else "absent"),
                   f"{len(desc)} chars")
            entry = next((f for f in files if f["role"] == "entrypoint"), None)
            lines = entry["content"].count("\n") + 1 if entry else 0
            assess(pb, ext, fw, el("concise-body"),
                   "present" if lines <= 500 else "partial", f"{lines} lines")
            for dirname, slug in (("references", "references-dir"), ("scripts", "scripts-dir"), ("assets", "assets-dir")):
                have = [f for f in files if f["relpath"].startswith(dirname + "/")]
                assess(pb, ext, fw, el(slug),
                       "present" if have else "absent",
                       f"{len(have)} file(s)" if have else "not bundled (optional)")
            n += 7
        elif m["kind"] == "agent":
            fw = fw_ids["claude-code-subagents"]
            def el(s):
                return el_ids[("claude-code-subagents", s)]
            for key, slug in (("name", "frontmatter-name"), ("description", "frontmatter-description"),
                              ("tools", "tools-allowlist"), ("model", "model-tier")):
                assess(pb, ext, fw, el(slug),
                       "present" if fm.get(key) else "absent", f"{key}={fm.get(key)!r}")
            assess(pb, ext, fw, el("system-prompt-body"),
                   "present" if m["body"].strip() else "absent",
                   f"{len(m['body'].split())} words")
            n += 5
        elif m["kind"] == "hook":
            fw = fw_ids["hook-dir-layout"]
            def el(s):
                return el_ids[("hook-dir-layout", s)]
            hook_py = next((f for f in files if f["relpath"] == "hook.py"), None)
            assess(pb, ext, fw, el("hook-py-entrypoint"),
                   "present" if hook_py else "absent",
                   "hook.py in the hook's directory" if hook_py else "no hook.py found")
            shell_files = [f["relpath"] for f in files if f["relpath"].endswith(".sh")]
            assess(pb, ext, fw, el("python-only-handler"),
                   "absent" if shell_files else "present",
                   f"legacy .sh handler(s): {shell_files}" if shell_files else "no .sh handler")
            if hook_py is None:
                assess(pb, ext, fw, el("stdlib-only-imports"), "absent", "no hook.py to scan")
            else:
                violations = stdlib_import_violations(hook_py["content"])
                if violations is None:
                    assess(pb, ext, fw, el("stdlib-only-imports"), "partial", "hook.py did not parse as Python")
                elif violations:
                    assess(pb, ext, fw, el("stdlib-only-imports"), "partial", f"non-stdlib imports: {violations}")
                else:
                    assess(pb, ext, fw, el("stdlib-only-imports"), "present", "all top-level imports are stdlib")
            config_files = [f["relpath"] for f in files if f["relpath"] in ("config.json", "hook.json")]
            assess(pb, ext, fw, el("config-present"),
                   "present" if config_files else "absent",
                   f"{len(config_files)} file(s)" if config_files else "not bundled (optional)")
            n += 4
    print(f"mechanical assessments: {n}")


def main():
    pb = PB()
    fw_ids, el_ids = ingest_frameworks(pb)
    ext_ids, ext_meta = ingest_extenders(pb)
    ingest_distributions(pb, ext_ids, ext_meta)
    ingest_dimensions(pb, ext_meta, fw_ids)
    ingest_assessments(pb, ext_ids, ext_meta, fw_ids, el_ids)
    src_ids = ingest_sources(pb)
    ingest_externals(pb, src_ids)
    prune_extenders(pb, live_slugs())
    print("done.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Populate the extender-db from this repo.")
    ap.add_argument(
        "--prune-dry-run", action="store_true",
        help="report the stale extenders and everything a prune would take with them, "
             "then exit; make no writes. Not spelled --dry-run: only the prune is "
             "previewed, and an unrecognised flag must fail rather than run destructively.",
    )
    if ap.parse_args().prune_dry_run:
        prune_extenders(PB(), live_slugs(), dry_run=True)
    else:
        main()

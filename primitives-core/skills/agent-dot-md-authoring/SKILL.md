---
name: agent-dot-md-authoring
description: >-
  Write a new CLAUDE.md (or AGENTS.md) from scratch, or audit and improve an
  existing one, so it actually helps a coding agent navigate the codebase. Use
  this whenever the user wants to create, write, rewrite, review, score, audit,
  shorten, or fix a CLAUDE.md / AGENTS.md / agent-guidance file — even if they
  just say "document this repo for Claude", "my CLAUDE.md is a mess", "set up
  agent instructions", or "/init the project". Also use when onboarding an agent
  to an unfamiliar repo and the existing guidance file is thin, stale, or bloated.
---

# Authoring and auditing CLAUDE.md

A CLAUDE.md is not a README and not a mission statement. It is a **navigation aid
for an agent** that has to find the right file, run the right command, and avoid
the one mistake that causes the worst rot — without reading the whole codebase
first. Every line must earn its place by answering a question the agent will
actually have.

This skill does two jobs:

- **Author** — write a new CLAUDE.md from the codebase using a proven skeleton.
- **Audit** — score an existing CLAUDE.md against a 10-point checklist and fix it.

Both are grounded in the same model of what makes these files good. The reference
distilled from one of the best examples in the wild (`bytedance/deer-flow`'s
`backend/CLAUDE.md`) lives in `references/deer-flow-patterns.md` — read it when you
need the full worked examples behind any pattern below.

## The core principle

Length is fine **if every line is current and load-bearing.** A dense 500-line
CLAUDE.md beats a vague 40-line one *only* if it's maintained. The size of the
file should match the maintenance budget the user will actually spend. If they
can't commit to updating it after every code change, keep CLAUDE.md short and push
detail into `/docs/`.

So before writing a long one, ask the user (or infer from the repo's activity):
will this be kept current? If not, aim short.

## Decide the mode

- New file, or a stub the user wants replaced → **Author** (next section).
- An existing substantive file the user wants reviewed/fixed → **Audit** (below).
- "Make it better" on a real file → audit first to find what's wrong, then rewrite
  the weak sections.

---

## Author: writing a CLAUDE.md from scratch

### Step 1 — learn the repo before writing a word

You cannot annotate a tree you haven't seen. Gather, by reading the repo (not by
guessing):

- What the system does, in one sentence. The entry-point service(s), their ports,
  and where a request actually starts.
- The directory layout, including *why* each top-level dir exists.
- The real command surface — read the `Makefile` / `package.json` scripts /
  `justfile`, don't invent targets.
- Order-sensitive chains: middleware stacks, init sequences, hook chains, lifecycle
  phases, migration steps.
- Architectural rules that have a **CI test** behind them (import boundaries,
  forbidden patterns, layering).
- Configuration resolution order (env vars vs. config files vs. defaults).
- The single rule that, if forgotten, causes the worst rot.

For a non-trivial repo, spawn an `Explore` agent (or `general-purpose`) to map the
tree and command surface in parallel while you read entry points yourself.

### Step 2 — fill the skeleton

Use this section order. It survives because each section answers a *different*
question, in the order the agent needs them. Copy `references/skeleton-template.md`
as the starting scaffold.

```
# CLAUDE.md
<one line: this file guides agents working in this repo>

## Project Overview        one paragraph: what the system does
**Architecture:**          services + ports + entry points
**Runtime:**               how a request actually flows
**Project Structure:**     annotated tree — EVERY line annotated

## Important Development Guidelines
### <The ONE critical rule>   one called-out must-do, and only one

## Commands                  real make/script targets, one block per location

## Architecture
### <Subsystem 1>            files / components / lifecycle / config / tests
### <Subsystem N>            repeat per major component

## Development Workflow
### <TDD / build / test rule>
### Startup modes            table: local / daemon / docker / prod
### Config                   env vars + resolution order

## Key Features              one paragraph each + link to detailed doc

## Code Style                4 lines: linter, line length, version, quirks

## Documentation             index of the detailed docs in /docs/
```

### Step 3 — apply the eight patterns that make it load-bearing

1. **Open with topology, not philosophy.** First prose line = what it does. By
   ~line 30 the agent should know what it is, what services run, and where code
   lives. No "we believe in delightful agents" preamble.

2. **Annotate every line of the project tree.** `agents/ # LangGraph agent system`,
   not bare `agents/`. Nested children get their own annotations. If a directory
   has no annotation, either explain it or hide it — a blank annotation means
   nobody remembers why it exists.

3. **Exactly one CRITICAL rule, called out near the top.** Not three. One. Agents
   retain one or two rules from a doc; spend that budget on the rule whose neglect
   causes the worst rot. Everything else lives in its own section.

4. **Spell out order-sensitive chains with a rationale per item.** For middlewares,
   init steps, hook chains, lifecycle phases: enumerate them in binding order, one
   line each, and note *why* the position matters ("must be last", "before tool
   stages run"). The agent never reads the assembly site; don't rely on source
   comments.

5. **Show forbidden patterns as commented code with the enforcing test.** Far
   clearer than prose:
   ```python
   # App -> Harness (allowed)
   from deerflow.config import get_app_config

   # Harness -> App (FORBIDDEN - enforced by test_harness_boundary.py)
   # from app.gateway.routers.uploads import ...  # will fail CI
   ```
   Pair every architectural rule that has a CI test with the name of that test.

6. **List configuration precedence top-to-bottom**, with the recommended location
   called out:
   ```
   1. explicit config_path argument
   2. DEER_FLOW_CONFIG_PATH env var
   3. config.yaml in cwd
   4. config.yaml in project root  (** recommended **)
   ```
   This prevents the "why isn't my override working" debugging session.

7. **Use a table whenever a list has >5 items with shared structure.** Router
   surfaces, endpoint inventories, startup modes, env vars. Tables let an agent
   scan for "is there a delete endpoint for X" without reading prose.

8. **Put caveats inline, in the section they apply to.** A topic-specific gotcha
   belongs with its topic — that's where the agent looks. Reserve a separate
   PITFALLS section only for genuinely cross-cutting hazards.

### Step 4 — strip the five anti-patterns

Delete on sight; none of these help an agent navigate:

1. Mission / values / philosophy preambles → goes in the README, if anywhere.
2. Historical context for decisions ("originally we used X, migrated to Y in
   March...") → CHANGELOG or an ADR.
3. Vague warnings without enforcement ("be careful with the auth code") → name the
   actual hazard and the test that catches it, or delete it.
4. TODO sections / future plans → these rot fastest; track them in issues.
5. Screenshots, badges, contributor lists → README territory.

### Step 5 — set the maintenance rule

Whatever the ONE critical rule is, if the repo can sustain it, make it "update
CLAUDE.md in the same change as the code it describes." That discipline is what
lets a long file stay healthy. State it explicitly in the file.

---

## Audit: scoring an existing CLAUDE.md

Read the file top to bottom, then score it against these 10 questions. Each "no"
is a fix. Report the score (x/10), list the failures with specific line references,
and offer to apply the fixes.

1. Can I tell what this system does in 30 seconds of reading?
2. Can I name the entry-point service(s), their ports, and where requests start,
   by ~line 50?
3. Is every directory in the project tree annotated with its purpose?
4. Is there exactly one CRITICAL rule called out near the top? (One, not three.)
5. For every order-sensitive chain (middlewares, init, hooks), is the
   rationale-per-item enumerated?
6. Are architectural rules paired with the CI test that enforces them?
7. Are configuration resolution orders listed explicitly?
8. Are tables used wherever a list has >5 items with shared structure?
9. Are subtle invariants written inline next to the relevant code reference, not
   buried in (or missing from) a pitfalls section?
10. Are TODOs, philosophy, history, and contributor lists all absent?

**Interpretation:** 9–10 is good. Most files score 3–5. Don't pad the score — a
file that scores 4 and gets honest, specific fixes is worth more than a generous 7.

### Audit output format

```
## CLAUDE.md audit — <score>/10

### What works
- <brief, only if genuinely good>

### Failures (each maps to a checklist item)
1. [Q3] Tree at lines 18-40: `utils/`, `lib/`, `internal/` have no annotations.
   -> add a purpose comment to each, or drop them from the tree.
2. [Q4] Three rules are bolded as critical (lines 12, 31, 58). Pick one; demote
   the rest into their own sections.
...

### Suggested fixes
<offer to apply them, or apply directly if the user already said go>
```

When verifying claims in an existing file, **check them against the actual repo** —
a CLAUDE.md that names a test, flag, or file that no longer exists is worse than
silence. Flag stale references explicitly.

---

## Verification before finishing

Before handing back a new or rewritten CLAUDE.md:

- Re-read it as if you were an agent dropped into the repo cold. Can you find the
  build command, the entry point, and the one rule, fast?
- Confirm every command, file path, test name, and port mentioned actually exists
  in the repo (grep for them).
- Confirm the tree matches the real directory layout.
- Run the 10-point checklist against your own output. Aim for 9+.

## A note on AGENTS.md and other names

The same principles apply to `AGENTS.md`, `.cursorrules`, `.github/copilot-
instructions.md`, or any agent-guidance file. The filename changes; the goal
(fast navigation, one critical rule, no rot) does not. Match the repo's existing
convention rather than imposing CLAUDE.md.

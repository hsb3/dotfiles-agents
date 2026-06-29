# Why deer-flow's CLAUDE.md is good — the full reference

`bytedance/deer-flow`'s `backend/CLAUDE.md` is 569 lines and earns every one of
them. Most CLAUDE.md files are either too short (vibes-only) or too long
(philosophy + history + TODOs). Theirs is rare in being long *and* dense — every
line is load-bearing for an agent navigating the codebase. These are the patterns,
with the worked examples behind each one. Read this when the summary in SKILL.md
isn't concrete enough.

To see the source: clone `https://github.com/bytedance/deer-flow` and read
`backend/CLAUDE.md` top to bottom — the most concentrated example of the genre.

## The skeleton (section order = the order an agent needs information)

```
# CLAUDE.md
This file provides guidance to Claude Code...

## Project Overview          — 1 paragraph: what the system does
**Architecture:**            — services + ports + entry points
**Runtime:**                 — how a request actually flows
**Project Structure:**       — annotated tree, every line annotated

## Important Development Guidelines
### Documentation Update Policy   — ONE called-out CRITICAL rule

## Commands                  — make targets, one block per location

## Architecture
### <Subsystem 1>            — files / components / lifecycle / config / tests
### <Subsystem N>

## Development Workflow
### TDD                      — mandatory rule, called out
### Startup modes            — table of local/daemon/docker dev/prod
### Frontend config          — env vars

## Key Features              — one paragraph + link to detailed doc each

## Code Style                — 4 lines: linter, line length, version, quotes

## Documentation             — index of detailed docs in /docs/
```

## The eight patterns that work

### 1. Open with topology, not philosophy
Their first prose line after the title states what the system does. Their second is
`**Architecture:**` with ports and services. By line 16 you know how a request
flows from nginx to the runtime. The first 30 lines should let an agent answer:
what is this, what services run, where does code live.

### 2. Annotate every line of the project tree
Lines 19–65: every directory gets a trailing comment. Not just `agents/` but
`agents/ # LangGraph agent system`, and nested children get their own annotations.

```
├── agents/            # LangGraph agent system
│   ├── lead_agent/    # Main agent (factory + system prompt)
│   ├── middlewares/   # 10 middleware components
```

If a directory exists with no annotation, either explain it or hide it. Empty
annotations are a tell that nobody knows why the directory exists anymore.

### 3. One CRITICAL rule, called out
Lines 67–76 establish a single must-do: keep README.md and CLAUDE.md in sync with
code changes. It's bold, at the top, the only thing in that section. Agents (and
humans) retain one or two rules from a doc. Pick the rule that, if forgotten,
causes the worst rot, and isolate it. For deer-flow, it's docs going stale.

### 4. Strict-order chains spelled out with rationale per item
Lines 154–175 enumerate all 18 middlewares in binding order, one or two lines each.
Several include *why* they sit at that position — "must be last", "before later
middleware/tool stages run." This is hidden ordering knowledge that otherwise
disappears into commit history. Whenever code has an order-sensitive list, enumerate
it with a one-line rationale per item. Don't rely on the source comment; the agent
never reads the assembly site.

### 5. Imports / forbidden patterns as commented examples
Lines 119–134 show actual import statements with `# allowed` and `# FORBIDDEN`
annotations naming the enforcing test:

```python
# App → Harness (allowed)
from deerflow.config import get_app_config

# Harness → App (FORBIDDEN — enforced by test_harness_boundary.py)
# from app.gateway.routers.uploads import ...  # ← will fail CI
```

Showing the failing case as commented code with the test that enforces it is far
clearer than prose like "harness must not import from app." Apply to any
architectural rule that has a CI test behind it.

### 6. Configuration priority listed top-to-bottom
Lines 187–204:

```
Configuration priority:
1. Explicit `config_path` argument
2. `DEER_FLOW_CONFIG_PATH` environment variable
3. `config.yaml` in current directory (backend/)
4. `config.yaml` in parent directory (project root - **recommended location**)
```

Anywhere there's resolution order — env vars overriding config files, profile vs
override fields, default fallbacks — list the precedence chain explicitly with the
recommended path called out. Prevents the "why isn't my override working" session.

### 7. Tables for any enumeration that would be a long bullet list
Lines 212–225 give the FastAPI router surface as a single table — router name, path
prefix, every endpoint with a one-line behavior note. Lines 432–439 do the same for
the embedded client. Tables let an agent scan for "is there a delete endpoint for
X" without reading prose. Use a table whenever a list has more than 5 items with
shared structure.

### 8. Caveats inline, in the section they apply to
Line 247: a sandbox-tool invariant — "same-path serialization is scoped to
`(sandbox.id, path)` so isolated sandboxes do not contend on identical virtual
paths inside one process" — lives inside the sandbox-tools description, not in a
separate PITFALLS section. Same for line 280 (ACP path translation quirk), line 320
(CSRF cookie/header detail), line 441 (embedded-vs-gateway upload semantics). A
pitfall section is fine for cross-cutting hazards, but topic-specific gotchas
belong with the topic — that's where the agent will look.

## The five anti-patterns that bloat without helping

1. **Mission/values/philosophy preambles.** "At DeerFlow, we believe agents should
   be delightful..." Skip entirely. Sentiment goes in the README.
2. **Long historical context for decisions.** "Originally we used X but in March we
   migrated to Y because..." Belongs in a CHANGELOG, an ADR, or a postmortem.
   CLAUDE.md describes the current state.
3. **Vague warnings without enforcement.** "Be careful when modifying the auth
   code." Either point to a specific test that catches the failure, name the actual
   hazard ("don't call `set_token()` from inside a request handler — it bypasses
   CSRF"), or delete the warning.
4. **TODO sections / future plans.** These rot fastest of all. Track them in
   issues. The deer-flow file has zero TODOs.
5. **Screenshots, badges, contributor lists.** None help an agent navigate.

## The 10-point audit checklist

Each "no" is something to fix.

1. Can I tell what this system does in 30 seconds of reading?
2. Can I name the entry-point service(s), their ports, and where requests start, by
   line 50?
3. Is every directory in the project tree annotated with its purpose?
4. Is there exactly one CRITICAL rule called out near the top? (Not three. One.)
5. For every order-sensitive chain (middlewares, init, hooks), is the
   rationale-per-item enumerated?
6. Are architectural rules paired with the CI test that enforces them?
7. Are configuration resolution orders listed explicitly?
8. Are tables used wherever a list has >5 items with shared structure?
9. Are subtle invariants written inline next to the relevant code reference, not
   buried in a pitfalls section?
10. Are TODOs, philosophy, history, contributor lists all absent?

A 9 or 10 means it's good. Most files score 3–5.

## The meta-rule: maintenance discipline

Their single called-out rule — update CLAUDE.md after every code change — is what
keeps the file healthy at 569 lines. Without that discipline, any long CLAUDE.md
rots. With it, length is fine because every line is current. If you can't commit to
that discipline, keep CLAUDE.md short and put detail in `/docs/`. The size of
CLAUDE.md should match the maintenance budget you'll actually spend.

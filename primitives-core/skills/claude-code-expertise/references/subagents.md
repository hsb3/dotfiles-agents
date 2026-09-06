# Authoring subagents

A **subagent** runs a bounded sub-task in a **separate context window** with its own tool set and
model. The main thread delegates, the subagent works in isolation and returns a result. Use one
when a sub-task is large or noisy (keep it out of the main context), needs a **different tool set
or model tier** than the main thread, or is a repeatable specialist role (reviewer, scout,
test-runner). Do **not** use one for knowledge the current agent can just apply inline — that is a
skill.

## Scaffold

Location: `.claude/agents/<name>.md` (project) · `~/.claude/agents/<name>.md` (user) · a plugin's
`agents/` · managed settings · `--agents` CLI flag (session only). Directories are scanned
recursively; project overrides user overrides plugin. One file, frontmatter + body. The body is
the subagent's **system prompt**.

```markdown
---
name: test-runner              # required; lowercase letters + hyphens; no ':'; unique
description: >                 # required; the WHEN-TO-USE — this drives auto-delegation
  Runs the test suite and diagnoses failures. Use proactively after code changes, or when
  the user asks to run tests, fix a failing test, or check the build.
tools: Read, Grep, Bash        # optional; omit to inherit ALL tools from the main thread
disallowedTools: Write         # optional; denylist applied after tools/inheritance
model: sonnet                  # optional; sonnet | opus | haiku | fable | <full model id> | inherit
permissionMode: default        # optional; default | acceptEdits | plan | auto | dontAsk | bypassPermissions
skills: [code-standards]       # optional; preloaded in full at startup
memory: project                # optional; user | project | local — persistent auto-memory
isolation: worktree            # optional; run in a temporary git worktree
color: blue                    # optional; red | blue | green | yellow | purple | orange | pink | cyan
---

You are a focused test-runner. Given a change or a failing test:
1. Run the relevant tests.
2. Read the failure and locate the cause.
3. Report the smallest fix, or apply it if asked. Do not expand scope.
Return a concise result: what ran, what failed, the root cause, the fix.
```

## The four decisions

### 1. The when-to-use description (the trigger)

The `description` is what makes auto-delegation fire — Claude reads it to decide whether to hand a
task to this subagent. Make it concrete and situational: name the triggering actions and add
"use proactively" if it should be preferred without being asked. A vague description
("helps with code") never fires; a specific one ("use after edits to run and fix tests") does.
Write it in the *third person, about the subagent's job* — same discipline as a skill description
(`authoring.md`), because the same matcher reads it.

### 2. Tool selection (least privilege)

- **Omit `tools`** to inherit every tool the main thread has (including MCP tools). Convenient,
  but broad — the subagent can do anything. `disallowedTools` subtracts from either list;
  `Agent(a, b)` restricts which subagent types it may spawn; `mcp__<server>` targets a server.
- **List `tools`** to restrict. Grant only what the role needs: a reviewer that must not mutate
  gets `Read, Grep, Glob` (no `Bash`, no `Edit`, no `Write`); a runner that executes but must not
  edit gets `Read, Bash` without `Edit`/`Write`.
- Least privilege is not just safety — a tight tool list *sharpens intent*: a read-only reviewer
  physically cannot "help" by editing, so it reviews.

### 3. Model / tier choice

- `haiku` — cheap, fast, mechanical: log scans, formatting, straightforward extraction.
- `sonnet` — the default working tier: most implementation, review, and analysis.
- `opus` — reserve for judgment-heavy or high-stakes reasoning where a wrong call is expensive
  (subtle correctness, security-sensitive logic, ambiguous acceptance criteria).
- `fable` — the newest tier alias; treat like `opus` for cost purposes until measured.
- `inherit` — match the main thread's model (keep the subagent at the caller's tier).
- Also accepted: a full model id such as `claude-opus-5`.

Pick the **lowest tier that reliably does the job**; escalate only the slices where being wrong is
costly. Tier is a cost/quality dial, not a default-to-max.

### 4. The system-prompt body

Write the body as a role brief, not a knowledge dump: state the mandate, the boundaries (what NOT
to do — scope creep is the common failure), the method (numbered steps if the flow matters), and
the **return contract** (what the subagent hands back, and in what shape). A subagent that returns
an unstructured ramble is hard for the caller to consume; specify the output.

## When NOT to make a subagent

- The task is *knowledge the current agent applies in place* → **skill**, not subagent.
- The task must fire on a lifecycle *event* → **hook**, not subagent.
- A *human* must trigger it by name → **command**, not subagent.
- It's a one-off with no reuse and no isolation benefit → just do it in the main thread.

## Common failure modes

- **Description too vague** → never auto-delegates. Fix: name the concrete triggering situations.
- **Inherited all tools when it should be scoped** → the subagent overreaches. Fix: an explicit
  `tools` list.
- **Over-tiered to `opus` for mechanical work** → wasteful. Fix: match the tier to the difficulty.
- **No return contract** → the caller can't use the result. Fix: specify the output shape in the
  body.
- **Doing a skill's job** → if there's no isolation, tool, or tier reason to separate contexts, a
  skill is simpler and cheaper.

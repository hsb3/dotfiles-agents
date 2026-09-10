# Dispatch knobs — the per-invocation settings and the git policy

These are decided at the dispatch, not baked into the agent definitions. The definitions carry
defaults; the dispatch carries the deviation.

## Model tier

Tier is a separate axis from the layer an agent sits on: the layer says what the agent is for, the
tier says how much judgment is being bought for it. See `tier-cutoff.md` for the protocol behind
the defaults and the state of the evidence for them.

<!-- harness:claude-code -->
`model` on the Agent call overrides the definition's default for one invocation. It is set at
dispatch precisely so the same agent can serve a cheap slice and an expensive one.
<!-- /harness -->

## Worktree isolation

Runs the agent in a fresh git worktree. Costs setup time and disk per agent. Use **only** when
parallel workers genuinely must mutate the same files. Disjoint file scopes are cheaper and
usually available — prefer re-slicing over isolating. A project can arm this per agent type
through the `isolate:` key in `atelier.local.md`, which the `worktree-isolation` hook reads
(`references/activation.md`).

<!-- harness:claude-code -->
Per dispatch, the knob is `isolation: worktree` on the Agent call.

**Read the base-ref key's nesting out of the settings file before trusting it** `[field]`. Which
ref a new worktree branches from is `{"worktree": {"baseRef": "head"}}` in `settings.json` —
nested under `worktree`, and absent that a worktree branches from `origin/<default-branch>`.
The flat spelling `"worktreeBaseRef"` is only the config menu's widget id, never a settings
key, and a file using it fails silently: no error, no warning, isolated writers still branching from
the default branch while the operator reads the setting as applied. Where the default branch is a
publish-only surface it reaches you as workers reporting that paths their briefs name do not
exist — check the nesting first, since nothing else in the run will tell you.
<!-- /harness -->

## Deliberate turn caps

A **deliberate** per-wave cap, not a default backstop. None of the builder, reviewer, or scout
definitions impose a turn limit: each self-regulates by scope and escalates loudly — an oversized
slice for builder/reviewer, an unanswerable or over-broad question for scout — rather than
stalling silently at a clock.

Impose a cap only when a specific wave has a reason (a known-small transform where a long run
means something went wrong). An arbitrary cap on open-ended work produces silent partial results,
which is the failure mode the definitions were changed to avoid.

<!-- harness:claude-code -->
The knob is `maxTurns` on the Agent call.
<!-- /harness -->

## Continuing an agent

To extend or course-correct an agent you already dispatched, continue the same one rather than
dispatching a fresh agent with a longer brief. A re-brief discards the accumulated context that is
most of what that agent already cost. This matters most for the `manager`, whose value is
precisely the chain context it has absorbed.

**This scopes to the contract the agent already holds.** Extending, correcting, or answering an
escalation within that contract continues the same agent. A *new slice is a new contract*, and it
goes to a fresh agent — for a manager, that is the retirement rule in `references/chain-width.md`,
and the two rules do not overlap: one governs the chain in flight, the other what happens after it
reports.

<!-- harness:claude-code -->
The channel is `SendMessage` addressed to the agent's id. It reaches an agent that is still
running as well as one that has finished.
<!-- /harness -->

**Downward it is one-way.** `scout`, `builder`, and `reviewer` have no authorized channel of their
own, so a message to a live execution agent arrives and cannot be answered before it finishes.
Send amendments, never questions, and never block on
the reply — it is the callee's final report. `waiting.md` has the rule and the alternatives.

<!-- harness:claude-code -->
Waiting on that reply instead deadlocked two managers in one session `[field]`. `waiting.md` also
carries the liveness check for telling a dead callee from a slow one.
<!-- /harness -->

## Agent capabilities and the git policy

- **Spawn authority is enforced.** `manager` is the only shipped agent that can dispatch;
  execution roles cannot delegate onward. The harness enforces this through tool availability
  or a tool guard; prose alone does not establish the layer boundary.
- `builder`, `reviewer`, and `manager` have full shell. Briefs should require them to run their own
  verification commands and paste the actual output.
- `scout` has a shell but no authority to use write or edit tools. The harness must enforce
  that boundary through tool availability or a tool guard. Shell *authority* is not
  structural: scout's default posture is no shell, and a brief must name the exact read-only
  command(s) it grants — no substitutes, no ungranted flags. Granting scout a command is a real
  decision with a real cost; grant reads only, and only what the brief needs answered.
- **Read-only git** (`status`, `diff`, `log`, `show`) is allowed to every full-shell agent
  (`builder`, `reviewer`, `manager`); a brief may grant scout a specific read-only git command the
  same way it grants any other read.
- **Mutating git inside a worker's own worktree is the worker's.** An agent working in a worktree
  of its own commits there as it goes — that branch is its. What is reserved to the orchestrating
  session is **pushing, merging, and any branch, worktree, or repo state outside the worker's
  own**, because integration is not a worker's job. This is prompt-level policy, not a tool-layer
  block, so it can be violated. Treat a push, a merge, or a commit on a shared branch from below
  the session as a protocol breach and check what else that agent did.
- **Verify what landed before merging.** Known trap, and the corrected rule above makes it more
  likely rather than less: a worker's commits on its own worktree branch are now expected, so a
  session that integrates carelessly is how those commits end up on the main branch unexamined.
  Integration hygiene belongs to the orchestrating session — read the log and the diff of the
  branch you are merging against the brief that produced it, before you merge it.
- **Config is read-only below the strategy layer** unless a brief explicitly hands ownership over.
  Gate, lint, typecheck, coverage thresholds, and CI belong to the strategist, because an agent
  that can edit its own acceptance criteria can satisfy any brief. An unsatisfiable gate is an
  escalation.

<!-- harness:claude-code -->
- **A `memory:` key in an agent definition writes to the tree at dispatch time** `[field]`. The
  runtime creates that directory before the agent takes its first action, so a definition produces
  tree state as a side effect of merely being dispatched — even if the agent then does nothing. No
  shipped agent here sets it; the trap is a definition adopted from elsewhere that does, landing a
  directory under a brief that demanded no scratch files. Read the frontmatter of any definition
  you did not write.

The tools behind the spawn-authority bullet: `manager` carries `Agent` and `SendMessage`, and
`scout`, `builder`, and `reviewer` do not. `scout` additionally lacks `Edit`, `Write`, and
`NotebookEdit`.
<!-- /harness -->

<!-- harness:claude-code -->
## Codex distribution

This block belongs to this repository's distribution, which serves Claude Code and Codex;
the opencode peer supplies its own procedures. In Codex, use this section for tool names,
model selection, setup, and routing wherever a workflow names Claude Code mechanics.
The role renderer includes this section after the neutral role contract and removes all other
distribution-specific blocks. Claude Code continues to use the procedures above.

**Set up before dispatch.** Locate the installed atelier package from this loaded skill's
absolute path: it is three directories above `references/dispatch-knobs.md`. Run
`python3 "<atelier-package>/skills/activation/scripts/activation.py" codex-setup
--project-dir "<project-root>"`, then run the same script with `check --harness codex
--project-dir "<project-root>"`. Full setup reconciles policy placement after creating `.codex`. Start a fresh Codex session after initial setup so project agent discovery sees the
profiles. Setup uses current managed global profiles when present; otherwise it generates
`.codex/agents/atelier-*.toml` from the installed package, and refreshes only files whose ownership
checksum still matches. An existing user file or an edited generated file is a visible error;
resolve it deliberately, never force an overwrite. Refresh stale globals only with explicit
`codex-setup --refresh-global`. Keep generated local profiles
profiles out of commits using the project's local git exclusion mechanism. No global agent or
config file is required. Repeat setup after a plugin update; `check --harness codex` reports stale profiles
and needed policy migration without writing. Setup is the strategist's job, never a worker's.

Use native role names `atelier-manager`, `atelier-builder`, `atelier-reviewer`,
`atelier-code-reviewer`, and `atelier-scout`. Profiles resolve their canonical `tier` through the
OpenAI column in `hooks/_lib/model_catalog.json`; Claude keywords stay on the Claude path.
The active parent model is unchanged. A deliberate model or reasoning override follows the
available native spawn schema; preserve the requested role, and verify the actual selected
model in the child's start evidence. Never replace a reviewer with a builder to buy a cheaper
model. The model catalog records API windows; use measured Codex session context limits for
context budgeting.

**Dispatch through the native tool the session exposes.** On `spawn_agent`, set `agent_type`
to the native role, `fork_context: false`, and supply the curated brief as `message`. On
`collaboration.spawn_agent`, set `agent_type` to the same role, a unique `task_name`,
`fork_turns: "none"`, and the curated brief as `message`. Do not hand-write encrypted hook
payloads. If the exposed tool has no role selector, stop and report that unsupported interface;
a role name mentioned only in the prompt is not registration. Each brief carries owned files,
acceptance commands, absolute context paths, and an escalation contact. Only a manager may
dispatch children; execution roles' spawn and message tools are denied by the worker guard.

**Isolation is a prerequisite to writing.** Arm atelier activation and verify the worker's
registered worktree, branch, and index before edits. The worker hook binds the actual native
agent identity to its tree and routes shell and patch operations there. A `cwd` or `isolation`
field injected into native spawn does not bind a worktree. A missing binding or removed tree
must stop worker writes, never fall back to the parent checkout. Use absolute owned paths in
the bound tree. Routing prevents worktree collisions; it is not an OS security sandbox.

**Completion and continuation.** Record the returned native ID or task name and which manager
owns it. Keep the manager turn open through fan-in. Use the available native wait with a bound
(`wait_agent`, or `wait` on explicit IDs); after it wakes, read the worker's actual final report
and status. A timeout is not completion. Send amendments to a running child with `send_message`;
resume an idle child with `followup_task` on the collaboration surface, or `send_input` on the
ID-based surface. Native `resume_agent` reopens a closed agent when available; it does not
replace sending the amendment. Do not close/remove a worker while another amendment is possible.
If a completion reaches the strategist instead, relay it verbatim to its owning manager and
resume that manager as needed. Never substitute a guessed report or inspect another worker's
private conversation to reconstruct it. Final integration into the project branch, pushing, merging PRs, and retiring
worktrees remain the strategist's work. A manager may cherry-pick its children's verified
commits into its own owned worktree branch to assemble and test the chain; it never
modifies the strategist's checkout or another worker's branch.

Companion skills are the installed sibling `skills/<name>/SKILL.md` paths in this package:
`delegation`, `waves`, `rubric-panel`, `deletion-pass`, `layer-cycle`, and `comment-hygiene`.
Use `atelier-reviewer` for independent verification and panel judges, `atelier-code-reviewer`
for simplification review, and `atelier-builder` for scoped edits. Reviewers return reports;
the dispatching layer writes any requested report artifact. The bundled scope counter is
`skills/delegation/scripts/scope.py`; pass absolute owned paths to it from the consumer tree.
<!-- /harness -->

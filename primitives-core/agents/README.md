# agents

Two families live here. The **atelier delegation roles** (`scout`, `builder`, `reviewer`,
`code-reviewer`, `manager`) are generic: any skill can dispatch them at any layer. `scout`,
`builder`, `reviewer`, and `code-reviewer` sit on the **execution layer**, each taking one
bounded brief and reporting back; `manager` sits on the **management layer**, owning a wave
or a coupled chain and driving it with its own workers. The **strategy layer** is the session
itself (`strategist`), which is never a spawned agent.

The **bundle-specific agents** (`rig-builder`, `pb-builder`, `pb-reviewer`,
`pocketbase-security-auditor`) are the opposite: each is bound to one bundle's subject matter
and its access model, and is dispatched by that bundle's skills rather than by the delegation
router.

Each role declares a **dispatch tier**, not a model. The tier below is that role's default;
the dispatcher overrides it per call when a slice's difficulty warrants a different one.

| Role | Tier | Dispatch override | Use for |
|---|---|---|---|
| `scout` | light | mid, for cross-file synthesis | Read-only recon — locate a definition, confirm presence/absence, inventory a scope, or reconcile evidence across files. |
| `builder` | mid | heavy, for coupled or expensive-to-unwind slices | Scoped implementation inside an owned file list against explicit acceptance criteria. |
| `reviewer` | heavy | always premium; no override | Adversarial, report-only verification that re-derives each claim from its cited source and re-runs its commands. |
| `code-reviewer` | mid | heavy, for a large or unfamiliar change | Report-only quality pass over code already written — names over-engineering, needless abstraction, and complexity, and shows the simpler form with a before/after. Distinct from `reviewer`, which verifies correctness rather than shape. |
| `manager` | heavy | always premium; no override | Owns a wave or a coupled chain end to end: briefs, sequences, and verifies its own workers, then reports one proof package upward. |
| `rig-builder` | mid | heavy, when the artifact has no compiler and the checker must be designed | Turning a written contract into one gate command, proving it green *and* red, and reporting a measured baseline. |
| `pb-builder` | mid | heavy, for a coupled schema-and-rules change | Scoped PocketBase backend implementation, carrying the migration, hook, and API-rule laws so a brief does not restate them. Boots its own clean-room server for every probe. |
| `pb-reviewer` | heavy | always premium; no override | Adversarial verification of a PocketBase claim, re-derived from its cited source and re-run in the reviewer's own clean room. Never edits. |
| `pocketbase-security-auditor` | heavy | always premium; no override | The PocketBase authorization surface — collection rules, custom routes, hooks, realtime subscriptions, relation scoping, role boundaries — audited with code evidence and live-server evidence kept apart. Never edits. |

## Tiers, and why no agent names a model

`light` / `mid` / `heavy` are semantic labels for how much capability a role's work needs —
deliberately not model-family names, so the same vocabulary survives a provider change.
The one place a tier becomes a concrete model is
[`../hooks/_lib/model_catalog.json`](../hooks/_lib/model_catalog.json):

```json
"heavy": { "claude_code_keyword": "opus", "models": { "anthropic": "claude-opus-5" } }
```

Every agent file here still carries a `model:` line, because Claude Code's frontmatter
accepts only `sonnet` / `opus` / `haiku` / `inherit` or a full model id — there is nowhere
else for a tier to be expressed to this harness. **That line is a rendering of the map, not
an authored choice**: `scripts/check_model_tiers.py` re-renders it from the declared tier
and fails on any difference, and the opencode generator resolves the same alias through the
same map (`keyword -> tier -> the active provider's id`). Switching provider is one edit to
`active_provider`; the nine agent files do not move.

`../hooks/_lib/model_tiers.py` is the runtime side of the same map — `model_for`,
`claude_code_keyword`, and `window_for`, which answers a model id's context window in tokens
(stripping the bracketed variant suffix the harness writes into transcripts, as in
`claude-opus-5[1m]`).

**Fallback, both halves.** A tier with no model for the active provider is `None` from
`model_for` — a hook fails open on it and keeps the session alive — and a RED failure in the
gate, naming the tier and the provider, so the hole is fixed at build time rather than
absorbed forever at runtime.

**Refresh path.** The `providers` block is a pinned, minimal projection of
`https://models.dev/api.json` (every model the provider lists, with its context window),
vendored in-tree because `make ci` is offline by design and an in-tree catalog is what makes
an invented id detectable with no network:

```sh
python3 scripts/check_model_tiers.py            # offline gate (make ci)
make models-drift                               # network: projection vs upstream, not in ci
python3 scripts/check_model_tiers.py --refresh  # network: rewrite the projection
```

`--refresh` rewrites only `providers`; re-pinning a tier to a newly released model stays a
deliberate hand edit.

**Never swap `builder` for `rig-builder`:** `builder` implements until the acceptance
criteria pass; `rig-builder` measures the baseline and must not fix it, because a baseline
taken after remediation is worthless.

## Install

The delegation roles ship in `atelier`; each bundle-specific agent ships in the bundle it
belongs to — `rig-builder` in `code-desk` and the three
PocketBase agents in `pocketbase`.

```
claude plugin install atelier@dotfiles-agents
claude plugin install code-desk@dotfiles-agents
claude plugin install pocketbase@dotfiles-agents
```

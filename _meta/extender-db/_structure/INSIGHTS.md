# Extender-DB — Insights & Observations

_A running log of insights, observations, and non-obvious learnings from the build — the raw
material for the eventual comprehensive documentation. Distinct from the sibling trackers:
[CHARTER](CHARTER.md) holds decisions, [PLAN](PLAN.md) holds milestones, [OPEN-ITEMS](OPEN-ITEMS.md)
holds tasks/findings; this holds the "what we learned, and what future docs must explain."_
Status: active · 2026-07-20

Conventions: newest insight first within each theme; each bullet stands alone (enough context
to lift into a doc without re-deriving it). `→ docs:<section>` tags where an insight clearly
belongs in a specific future doc (see the §6 outline).

## 1 · Domain landscape — the extender-evaluation ecosystem
_(from the 2026-07-20 research pass + reading SkillOpt & ClosedLoop at source)_

- **Two distinct eval paradigms exist, and we adopt one of each.** (a) LLM-as-judge + rubric
  (ClosedLoop `judges`: one prompt-file judge per quality dimension emitting a strict
  `CaseScore`) — fits *qualitative conformance*. (b) Scored-benchmark optimization (Microsoft
  SkillOpt: skill-as-trainable-state, machine-checkable reward, validation-gated edit) — fits
  *quantitative "how good / can we improve."* Complementary, not competing. → docs:evaluation
- **No publisher ships an objective cross-publisher benchmark leaderboard.** "Publishes evals"
  in the wild means eval *tooling*/methodology or self-authored/behavioral tests — never a
  neutral ranking of third-party extenders. So "why ours over the first hit" cannot be answered
  by citing someone's leaderboard; we must generate the comparison ourselves. → docs:why
- **The trust landscape splits cleanly:** first-party (Anthropic — the only publisher shipping
  first-party eval *tooling*, via skill-creator) · aggregators/marketplaces (skills.sh,
  tonsofskills — ranked by popularity + security scans, NOT functional evals; the "first search
  hit" baselines) · individual authors shipping real evals (obra/superpowers behavioral harness,
  vinnie357 methodology, daymade self-scored) · identity-trust registries (MCP Registry:
  reverse-DNS namespace auth, not code safety). → docs:trusted-sources
- **Marketplace "curation" ≠ quality vetting.** claude-plugins-official "curation" =
  submission-approval + automated security review, not per-plugin functional testing;
  skills.sh grades security risk only. The trust-tier vocabulary must encode this gap so a
  security-scanned popular plugin isn't mistaken for a functionally-vetted one. → docs:trust-model
- **Adjacent ecosystems carry transferable rigor.** microsoft/hve-core (GitHub Copilot, not
  Claude Code) ships a real CI/CD validation-standards process worth borrowing; karpathy/
  autoresearch is the canonical closed-loop self-improvement pattern (modify → evaluate →
  keep/discard → repeat). Neither publishes CC extenders, so they're references, not sources.

## 2 · Design rationale — non-obvious modeling choices

- **Doctrine as data, append-and-supersede.** Frameworks/elements are rows with provenance +
  status, never code constants to overwrite. Competing mental models (our archetypes vs a
  future Anthropic canonical set) coexist and are compared against the same catalog; a
  superseded framework keeps its text for provenance. This is the whole point of modeling
  doctrine as data rather than hardcoding a rubric. → docs:data-model
- **Publisher-level unit for `sources`, not extender-level.** The registry answers "which
  publishers can we trust to vendor / reference / compare from," so a row is a publisher and an
  extender links to its publisher via `extenders.source`. A third-party plugin merely *hosted*
  in Anthropic's marketplace is not thereby first-party — we linked by actual upstream path
  (`/plugins/` internal vs `/external_plugins/`). → docs:sources
- **Jobs at "deliverable altitude," all-work scope.** A job = one nameable deliverable you'd
  hand a single agent session (not a task, not a whole workflow); the taxonomy spans *all* of
  Henry's agent work so every extender maps. Deliberately Henry-authored — it encodes what his
  work needs done, which is *not* derivable from the corpus. → docs:jobs-taxonomy
- **`assessor` is the load-bearing discipline.** It's what lets mechanical (regenerable by
  ingest) and judged (never touched by ingest) verdicts coexist on the same
  (extender, framework, element) cell. Every eval paradigm we adopt writes under its own
  assessor value; the unique index enforces coexistence. → docs:assessments
- **Adopt-not-build flipped the roadmap, and applies at every layer.** The pivotal insight:
  mature, permissively-licensed eval machinery already targets Claude Code, so bespoke would
  duplicate it. It resolves into three reuse layers: *methodology* = adopt (SkillOpt MIT +
  ClosedLoop Apache-2.0); *execution/harness* = reuse Henry's existing meta-harness for
  opencode + other coding-agent harnesses (do NOT build an `opencode_exec` backend — EDB-19);
  *build* only the IP nobody else has (job taxonomy, coverage, curation decisions). "Don't
  author each extender from scratch" applied all the way up the stack. → docs:strategy

## 3 · Technical gotchas (must survive into the operations docs)

- **PocketBase drops-and-recreates a column if a field is PATCHed without its id** — silent
  data loss. `schema.py` merges by field name and preserves ids; never bypass it. → docs:ops
- **`data.db` is tracked; stop the server before committing** so the WAL checkpoints into the
  main file (else the committed DB misses recent writes), then restart. A plain `serve` does
  not dirty `data.db`; only writes do. → docs:ops
- **Stdlib-only, zero-install is an invariant** — no PyYAML even for one-off analysis; use the
  tailored line parsers already in `ingest.py` (`parse_externals`, frontmatter parser). → docs:ops
- **The roster + externals live at the REPO ROOT** (`primitives-core.yaml`, `externals.yaml`),
  not under `primitives-core/`, despite some prose implying otherwise. → docs:ops
- **SkillOpt has no generic "grade my skill."** It scores a skill against an *authored* task
  set with a machine-checkable reward — the scorer *is* the rubric. Every skill under eval
  needs a small authored benchmark; that authoring is the real cost, and the reason M5 starts
  with exactly one skill. → docs:evaluation
- **Cheap evals need free/local models, not a new harness.** SkillOpt reaches free/local
  models via its `openai_compatible` backend (target and optimizer roles configured
  independently, so a cheap target + stronger optimizer is possible). *Faithful agentic* eval
  of CC skills (they run in a tool-use loop, not single-shot chat) needs a driving harness —
  but Henry already has a meta-harness for opencode + other coding-agent harnesses, so that
  layer is **reused, not built** (EDB-19/EDB-14). → docs:evaluation
- **`skillopt_sleep` is the closest out-of-box "improve my CC skills"** — harvests real Claude
  Code / Codex transcripts, mines checkable tasks, gate-improves offline, human-adopts. Data
  boundary caveat: it sends transcript excerpts to the model provider. → docs:self-improvement

## 4 · Reusable patterns worth documenting (borrowed from the adopted frameworks)

- **`CaseScore` verdict with a first-class error state** — `{final_status: pass/fail/error,
  metrics:[{name, threshold, score, justification}]}`; the error state is excluded from
  aggregates, so a crashed judge doesn't tank a grade. Our judged passes should adopt this
  shape (EDB-21). → docs:evaluation
- **Lightweight eval-case format** — `{id, input, expected_outcome}` JSONL + a 1–5 rubric: the
  cheapest hand-authorable golden set; use for conformance before building infrastructure.
- **Judge-as-prompt with an embedded deterministic rubric** — severity table → numeric formula
  → threshold → worked pass/fail/error examples; one judge per quality dimension, reproducible.
- **Self-learning loop mechanics** — capture (decision-tree gated) → dedup/validate → persist
  with deterministic success rates from an outcomes log → inject top-N into future runs via a
  hook; citation-verified anti-gaming. The reference model for improving extenders over time.

## 5 · Open tensions the docs must not paper over

- **Per-job disposition storage undecided** — author / vendor / reference / compare per job; a
  `job_coverage` collection vs assessment metadata. Resolved during M1 (W9). → docs:jobs-taxonomy
- **No snapshot / time-series story** (EDB-7) — rows mutate in place; trend analysis would need
  a `snapshots` collection keyed by git ref. Deferred; docs should say so, not imply history.
- **`coleam00` is in the registry unvetted** (we vendor its excalidraw skill) — its trust tier
  is deliberately conservative pending a real vetting pass (EDB-16). Docs must not present it
  as vetted.
- **Promotion is undecided** — stay a `_meta` desk tool / graduate to `scripts/` + a make lane
  / extract to its own repo (gate 2/4). Comprehensive docs are a promotion-adjacent artifact;
  write them to survive whichever path is chosen.

## 6 · Seed outline for the comprehensive documentation

When we write the comprehensive docs, the likely spine (each section's feeder insights are
tagged `→ docs:<section>` above):

1. **why** — the extender-evaluation problem + the "no objective leaderboard" gap.
2. **data-model** — inventory ⋈ doctrine via `assessments`; the collections; assessor discipline.
3. **doctrine catalog** — the frameworks (archetypes, sections, roster schema, hook layout,
   job taxonomy, adopted eval methodologies), each with provenance.
4. **trusted-sources** — the registry, trust-tier semantics, how comparators are chosen.
5. **evaluation** — the two paradigms, SkillOpt adoption, the cheap-model substrate, the
   "author a benchmark" reality, the CaseScore/judge patterns.
6. **workflows** — create / curate / combine → evaluate → use; the self-improvement loop.
7. **operations (ops)** — run it, the gotchas, idempotence, the tracked-DB commit dance.
8. **strategy / roadmap** — adopt-not-build, the milestones, the promotion gate + options.

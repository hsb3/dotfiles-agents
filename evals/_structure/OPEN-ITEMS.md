# Extender-DB — Open Items

_The project's issue tracker: open items, catalog findings awaiting triage, and the resolved
log. One line per item; promote to a GitHub issue only if it outgrows this file._
Status: active · 2026-07-20

Conventions: `EDB-N` ids, newest first within each section. An item moves to **Resolved**
with a one-line outcome (and stays there — the log is the promotion-gate evidence for
"findings → actions").

**2026-07-20:** remaining development is mirrored on GitHub as **epic #154** (sub-issues
#155–#167) per Henry's decision batch. EDB ids stay the canonical fine-grained log; the
epic is the execution tracker — when a sub-issue closes, record the outcome here too.

## Open — tool

| Id | Item | Notes |
|---|---|---|
| EDB-23 | Description-only judging of externals is under-determined | M1 evidence: `typescript-lsp` (22-char description) got two disjoint single-job mappings from two competent judges (implement-change vs orient-codebase); the union was accepted at adjudication. Before the next coverage pass, extend externals' `description` fields (or ingest bodies alongside the EDB-16 vetting) so verdicts are derivable rather than guessed. |
| EDB-22 | Directed-composition planner + its testing infra (future direction) | The "use" surface: a grounded planner (a smart model — Fable/Opus — reasoning over the DB's coverage map + directional `relationships` + each tool's trigger/output) that assembles an ordered, branching set of extenders for a goal **and context**; the planner is itself an extender (its job is *pick the extenders*). Compositions are **living** — periodically tested against outcomes and updated (evaluate→improve, one level up from a single extender). **Deferred** until the M1 coverage substrate + M4–M6 evals are solid (Henry, 2026-07-20). Near-term enabler: M1 captures the substrate (directional hand-off links + per-tool trigger/output). |
| EDB-21 | Formalize our judge+rubric+CaseScore conformance pattern (M4) | Borrow the `closedloop-judges` shape onto our `assessments`: one judge prompt per quality dimension carrying a deterministic rubric (severity→formula→threshold→worked examples), emitting a CaseScore-like verdict with a first-class error state. W1 is a lighter version; formalize + document so future judged passes are reproducible. Folds in EDB-10 (judging-criteria v2). |
| EDB-20 | Author the first SkillOpt benchmark for one skill (M5) | Pick one skill under test; author a small task set with a machine-checkable reward + a config pointing `env.skill_init` at its SKILL.md; run `eval_only.py` with-skill vs without vs a registry baseline on a cheap `openai_compatible` model; store as `eval_runs`. The scorer IS the rubric — the real work is authoring it. |
| EDB-19 | Wire M5 execution to Henry's existing meta-harness (reuse, not build) | Henry already has a meta-harness for testing across opencode + other coding-agent harnesses (2026-07-20) — **do NOT build an `opencode_exec` SkillOpt backend.** Get the repo/path pointer (likely the same as EDB-14), understand its interface, and route M5's with-skill/without/baseline rollouts through it on cheap/free models. `opencode-expertise` covers the CC→opencode translation (hooks the main gap). |
| EDB-16 | Registry expansion — research follow-ups | From the EDB-15 research pass's open questions: (a) vet whether Microsoft / Firebase / Supabase (on skills.sh leaderboards) ship their own eval suites — **partially answered**: Microsoft ships SkillOpt (now framework `skillopt`) + hve-core (Copilot); (b) `coleam00` was added because we vendor from it but was NOT independently vetted — run a real vetting pass — **update 2026-07-20:** the M1 dup-check confirmed the vendored skill duplicates our authored `excalidraw` (M3 drop/fold candidate), which may moot the vetting; (c) no publisher ships an OBJECTIVE cross-publisher benchmark leaderboard — track if one emerges. |
| EDB-15 | Trusted-source (publisher) registry | **DONE 2026-07-20:** `sources` collection + `extenders.source` relation built (schema signed off by Henry); seeded **8 publishers** from an adversarially verified research pass (deep-research, 103 agents) — trusted: anthropic, mcp-registry; provisional: obra-superpowers, daymade, vinnie357, coleam00; watch (comparator baselines): skills-sh, tonsofskills. All 6 externals linked to their publisher (5 → anthropic, excalidraw → coleam00). Every row cited (`evidence_url`). Follow-ups → EDB-16. **Per-job disposition model resolved 2026-07-20:** stored in the new `job_coverage` collection (CHARTER decision 9); the vocabulary `author/vendor/reference/compare` is applied during the M1 build, gaps drawn from this registry rather than defaulting to author-from-scratch. |
| EDB-14 | Built-in agents / meta-harness from Henry's other repo | Henry has code elsewhere — a meta-harness for testing across opencode + other coding-agent harnesses (confirmed 2026-07-20) — that powers the eval EXECUTION layer (reuse, not build; see EDB-19). Capture the repo/path pointer here when provided; it likely subsumes EDB-19's execution need. |
| EDB-12 | Comparative-evaluation protocol (W8) | Design the benchmark-job / A-B-baseline trial protocol, incl. how skills.sh alternatives are selected and pinned. |
| EDB-10 | Judging-criteria v2 before any judged-v2 pass | Reviewer calibration flags from W1: (a) present/partial/absent boundary underspecified — 15/16 section disagreements were adjacent-step; (b) does "body" mean SKILL.md only or include references/? (changes primaries for reference-heavy skills); (c) frontmatter-only triggers score `absent` on trigger-when-to-use — penalizes well-placed frontmatter, maybe unintended; (d) `examples` bar for bare commands without expected output; (e) no rule for "prominent but not dominant" guardrail sections. Fold into the frameworks' `criteria` fields, then supersede per charter. **M1 additions (2026-07-20):** four adjudication boundary rules to fold in — consumes-the-handoff ≠ sustains-continuity; nudge-only hooks cap at `partial` (enforce/perform score `present`); house-standard reference skills cap at `partial` on consult-domain-expertise; judge hint DIRECTIONS are unreliable (~4 of 53 inverted vs their own notes — normalize by note semantics, never trust the arrow). |
| EDB-8 | Standalone distribution rows carry no version | `skill-catalog.yaml` wrappers get a generated version at assembly; decide whether to read it from `gen_standalone.py` output or leave blank. |
| EDB-7 | No snapshot/time-series story | Rows are mutate-in-place; trend analysis needs a `snapshots` collection keyed by git ref (see README expansion path). Decide at W4 whether it earns its cost. |
| EDB-6 | Frontmatter parser is flat-only | `parse_frontmatter` handles single-line `key: value` only. All 27 current extenders are flat; a future nested/multi-line frontmatter would be silently truncated to its flat keys. Guard or extend before W2 if hook configs need it. |

## Open — catalog findings (from the data, awaiting triage)

| Id | Item | Notes |
|---|---|---|
| EDB-25 | Promotion targets deep-research / dataviz / update-config are harness-shipped, not estate files | Found 2026-07-21 executing #155–#157: no on-disk source exists in the estate (searched `~/.claude`, `~/dotfiles`, plugins cache, `.agents`, npm-global, the desk census — the census itself notes retired hand-rolled versions were superseded because "the product now ships properly"). Per ADR 0015 (self-authored only) the promotions are delivered as **authored originals for the same jobs**, written from capability specs, not from the shipped bodies. Provenance: `origin: authored`, no upstream. |
| EDB-4 | Custom frontmatter keys with no spec | skill `metadata` (2), skill `version` (2), agent `memory` (1). Decide each: adopt into an internal spec framework (requirement != custom), or remove from the bodies. |
| EDB-3 | Two skills exceed the ≤500-line SKILL.md guideline | `diagrams` 653 lines, `obsidian-cli` 753 lines (framework `anthropic-agent-skills` / `concise-body`). Candidate fix: push depth into `references/`. |

## W1 adjudication log (2026-07-20)

W1 ran as 6 sonnet judges (23 skills) + 2 blind opus reviewers (stratified 8-skill sample).
Agreement on the sample: primaries 6/8 exact; sections 56/72 exact (78%), with 15 of the 16
disagreements adjacent-step (present↔partial or partial↔absent) and only one hard flip —
the fuzz lives in the `partial` boundary (→ EDB-10), not in contradictory readings.
Session rulings, re-derived from the skill sources:

| Dispute | Ruling | Why |
|---|---|---|
| handoff primary: deliverable-producer (judge) vs workflow-procedure (reviewer) | **workflow-procedure** | Body is dominated by protocol (precedence contract, 6-step update pass, init procedure, rules); the artifact skeleton is subordinate. |
| private-fork primary: scaffold-auditor (judge) vs domain-expertise (reviewer) | **domain-expertise** | SKILL.md body is doctrine (invariants, tier table, anti-patterns); ordered procedures live in references/ — the body-dominance tiebreak reads as reference knowledge. |
| private-fork integration-partners: present (judge) vs absent (reviewer) | **absent** | Criterion requires naming sibling components; the body's table lists the skill's own reference files. |

Adjacent-step section disagreements: judge verdicts stand as the `judged-v1` record;
reviewer verdicts preserved in-DB as `review-v1`. Result: 23/23 skills, exactly one primary
each, full 9-section coverage; distribution domain-expertise 11 · workflow-procedure 4 ·
deliverable-producer 4 · scaffold-auditor 3 · orchestration-delegation 1 ·
guardrail-override 0.

## M1 coverage adjudication log (2026-07-20)

M1 ran as 7 sonnet judges (37 extenders, batched by kind) + 2 blind opus reviewers
(stratified 8-extender sample chosen to include every session-flagged weak verdict) + 1
opus duplicative-check on the 3 contested pairs. Sample agreement: 1/8 extenders fully
agreed; 10 verdict cells disputed — 7 adjacent-step (the `partial` boundary again, → EDB-10),
2 full reassignments (both thin-description extenders → EDB-23), 1 reviewer-found addition
(readme-value-and-proof × operate-browser-ui — blind review ADDED coverage the fan-out
missed). Session rulings re-derived from the bodies; 10 rows patched to the adjudication
run (incl. one rule-extension outside the sample: owner-signoff × sustain-continuity).
Four boundary rules logged in the run's `adjudication-log` response (→ EDB-10). Dup-check:
pptx→pptx-themes and builder→lead are feeds-into (keep both); excalidraw ≡
excalidraw-diagram-coleam00 confirmed duplicative (→ M3, EDB-16b). Full detail:
eval_runs `m1-coverage-{judged,review,adjudication}-2026-07-20` in the DB.

## Resolved

| Id | Item | Outcome |
|---|---|---|
| EDB-9 | obsidian-cli SKILL.md cites nonexistent files | **Resolved 2026-07-21 (finding → action #1 for charter gate 3; issue #160).** "Additional Resources" rewritten to cite the five real files (`quick-reference.md`, `file-commands.md`, `setup-guide.md`, `daily-automation.sh`, `vault-reports.sh`); phantom `query-commands.md` / `plugin-commands.md` / `developer-commands.md` / `batch-operations.sh` citations removed. `make build` regenerated the obsidian-toolkit copy. Re-ingest proved the **update path** (charter gate 4): ingest logged `extender updated: skill/obsidian-cli`, row id `hbt6ac5r9sjkoji` unchanged, extender count 37→37, only `mechanical-v1` assessment rows touched (197), zero judgment rows. |
| EDB-24 | M1 coverage gaps/partials — owner decisions | Decided 2026-07-20 (issue #153 → closed): all five in-estate answers approved — promote deep-research (#155), dataviz (#156), update-config (#157); foreman-kit migration playbook (#158); operate-browser-ui stays `reference` (claude-in-chrome). Plus: coleam00 excalidraw drop approved (#159), vendor `improve-code` accepted, EDB-9 fix approved (#160), and the F-item `coverage_gaps` view REVERSED to build (#161). Remaining development consolidated as **epic #154** (sub-issues #155–#167). Meta-harness pointer (EDB-14/19) still outstanding — blocks #165/M5. |
| EDB-13 | Jobs-to-be-done coverage framework (W9/M1) | 2026-07-20 complete: taxonomy (24 jobs / 7 families) + the M1 body — 888 `coverage-v1` assessments (37×24 cross product, idempotent), 46 `relationships` (24 complementary · 1 duplicative · 21 directed hand-off links), 24 `job_coverage` rows (19 covered / 3 partial / 2 gap; dispositions 22 author · 1 vendor · 1 reference), `coverage-matrix.md` rendered via `render_matrix.py`. Provenance in 3 eval_runs. Findings → M1 adjudication log + EDB-23/24. |
| EDB-18 | Adopt SkillOpt + ClosedLoop judges as eval doctrine (M4) | 2026-07-20: both cloned (`~/developer/tmp`; re-housed 2026-07-21 at `~/Developer/EVAL_WORKBENCH/`), read at source by two subagents, and loaded as `evaluation-methodology` frameworks — `skillopt` (5 cited elements: scored-rollout, validation-gated-edit, authored-benchmark-required, cheap-model-substrate, transcript-mined-improvement) and `closedloop-judges` (4: judge-as-prompt-rubric, casescore-verdict, lightweight-eval-case, self-learning-loop). Charter decisions 6–8 record the adopt-not-build strategy. |
| EDB-17 | Add Henry's suggested publishers to the registry | 2026-07-20: researched all 5 suggestions; added `jeffallan` (individual, ~10.7k★, no evals → provisional) and `closedloop-ai` (research-lab, ships judges+self-learning evals → provisional) as `sources`. hve-core (Copilot, adjacent) + autoresearch (ML self-improvement pattern) recorded as charter references, not registry rows. SkillOpt → framework, not source (it's a methodology, not an extender publisher). |
| EDB-11 | `extenders.kind` vocabulary lacked `plugin` | Found verifying the W2/W3 builder (externals.yaml carries `kind: plugin`; the builder had patched only its throwaway instance and its handoff was cut off). Fixed durably in schema.py (EXTENDER_KINDS + dynamic applies_to maxSelect); live schema updated in place. Lesson: a builder "proof" on a held-out instance can mask a divergence from the tracked schema source — the session gate caught it. |
| EDB-5 | Judged assessments not yet run | W1 complete 2026-07-20: 345 `judged-v1` + 120 `review-v1` rows loaded via `load_assessments.py`; gates passed (exactly-one-primary 23/23, full section coverage, ingest re-run leaves judged rows untouched). See the W1 adjudication log below. W2/W3 same day: hooks + externals ingested (37 extenders; 197 mechanical rows incl. 16 hook checks, all present). |
| EDB-2 | PocketBase default 5000-char cap broke ingest of large bodies | Explicit `max` on `extenders.body` and `files.content` (2 MB); documented in schema.py. |
| EDB-1 | Collection PATCH without field ids drops-and-recreates columns (data loss) | schema.py merges by field name and preserves ids on update; noted as invariant in CHARTER.md. |

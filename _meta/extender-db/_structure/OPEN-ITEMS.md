# Extender-DB — Open Items

_The project's issue tracker: open items, catalog findings awaiting triage, and the resolved
log. One line per item; promote to a GitHub issue only if it outgrows this file._
Status: active · 2026-07-20

Conventions: `EDB-N` ids, newest first within each section. An item moves to **Resolved**
with a one-line outcome (and stays there — the log is the promotion-gate evidence for
"findings → actions").

## Open — tool

| Id | Item | Notes |
|---|---|---|
| EDB-21 | Formalize our judge+rubric+CaseScore conformance pattern (M4) | Borrow the `closedloop-judges` shape onto our `assessments`: one judge prompt per quality dimension carrying a deterministic rubric (severity→formula→threshold→worked examples), emitting a CaseScore-like verdict with a first-class error state. W1 is a lighter version; formalize + document so future judged passes are reproducible. Folds in EDB-10 (judging-criteria v2). |
| EDB-20 | Author the first SkillOpt benchmark for one skill (M5) | Pick one skill under test; author a small task set with a machine-checkable reward + a config pointing `env.skill_init` at its SKILL.md; run `eval_only.py` with-skill vs without vs a registry baseline on a cheap `openai_compatible` model; store as `eval_runs`. The scorer IS the rubric — the real work is authoring it. |
| EDB-19 | `opencode_exec` harness for SkillOpt (M5 optional) | ~4-step change in SkillOpt (`codex_harness.py run_target_exec` + `backend_config.py` allow-lists + config keys) mirroring `run_claude_code_exec`, so CC skills get faithful *agentic* eval on cheap/free models via opencode. Leans on `opencode-expertise` (hooks are the main CC→opencode translation gap). Not needed for chat-only cheap eval (that already works via `openai_compatible`). |
| EDB-16 | Registry expansion — research follow-ups | From the EDB-15 research pass's open questions: (a) vet whether Microsoft / Firebase / Supabase (on skills.sh leaderboards) ship their own eval suites — **partially answered**: Microsoft ships SkillOpt (now framework `skillopt`) + hve-core (Copilot); (b) `coleam00` was added because we vendor from it but was NOT independently vetted — run a real vetting pass; (c) no publisher ships an OBJECTIVE cross-publisher benchmark leaderboard — track if one emerges. |
| EDB-15 | Trusted-source (publisher) registry | **DONE 2026-07-20:** `sources` collection + `extenders.source` relation built (schema signed off by Henry); seeded **8 publishers** from an adversarially verified research pass (deep-research, 103 agents) — trusted: anthropic, mcp-registry; provisional: obra-superpowers, daymade, vinnie357, coleam00; watch (comparator baselines): skills-sh, tonsofskills. All 6 externals linked to their publisher (5 → anthropic, excalidraw → coleam00). Every row cited (`evidence_url`). Follow-ups → EDB-16. **Still pending: the per-job disposition model** (author/vendor/reference/compare) — decided during the W9 mapping build. |
| EDB-14 | Built-in agents from Henry's other repo | Henry has code elsewhere that could power built-in evaluation agents. Deliberately deferred until the retrofit is solid; capture the repo pointer here when provided. |
| EDB-13 | Jobs-to-be-done coverage framework (W9) | **Taxonomy DONE 2026-07-20:** `hsb3-jobs-to-be-done` loaded (24 jobs, 7 families, kind `job-taxonomy`, candidate), authored with Henry at deliverable altitude / all-work scope; idempotence + assessor discipline re-verified. **Remaining (W9 body):** map 37 extenders → jobs + pairwise relationships → coverage matrix, recording per-job dispositions from EDB-15. |
| EDB-12 | Comparative-evaluation protocol (W8) | Design the benchmark-job / A-B-baseline trial protocol, incl. how skills.sh alternatives are selected and pinned. |
| EDB-10 | Judging-criteria v2 before any judged-v2 pass | Reviewer calibration flags from W1: (a) present/partial/absent boundary underspecified — 15/16 section disagreements were adjacent-step; (b) does "body" mean SKILL.md only or include references/? (changes primaries for reference-heavy skills); (c) frontmatter-only triggers score `absent` on trigger-when-to-use — penalizes well-placed frontmatter, maybe unintended; (d) `examples` bar for bare commands without expected output; (e) no rule for "prominent but not dominant" guardrail sections. Fold into the frameworks' `criteria` fields, then supersede per charter. |
| EDB-8 | Standalone distribution rows carry no version | `skill-catalog.yaml` wrappers get a generated version at assembly; decide whether to read it from `gen_standalone.py` output or leave blank. |
| EDB-7 | No snapshot/time-series story | Rows are mutate-in-place; trend analysis needs a `snapshots` collection keyed by git ref (see README expansion path). Decide at W4 whether it earns its cost. |
| EDB-6 | Frontmatter parser is flat-only | `parse_frontmatter` handles single-line `key: value` only. All 27 current extenders are flat; a future nested/multi-line frontmatter would be silently truncated to its flat keys. Guard or extend before W2 if hook configs need it. |

## Open — catalog findings (from the data, awaiting triage)

| Id | Item | Notes |
|---|---|---|
| EDB-9 | obsidian-cli SKILL.md cites nonexistent files | **Confirmed by two independent agents** (a judge and a blind reviewer): "Additional Resources" names `references/query-commands.md`, `plugin-commands.md`, `developer-commands.md`, `examples/batch-operations.sh` — none exist; actual files are `file-commands.md`, `quick-reference.md`, `setup-guide.md`, `daily-automation.sh`, `vault-reports.sh`. Fix the skill body in `primitives-core/` (candidate promotion-gate "finding → action"). |
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

## Resolved

| Id | Item | Outcome |
|---|---|---|
| EDB-18 | Adopt SkillOpt + ClosedLoop judges as eval doctrine (M4) | 2026-07-20: both cloned (`~/developer/tmp`), read at source by two subagents, and loaded as `evaluation-methodology` frameworks — `skillopt` (5 cited elements: scored-rollout, validation-gated-edit, authored-benchmark-required, cheap-model-substrate, transcript-mined-improvement) and `closedloop-judges` (4: judge-as-prompt-rubric, casescore-verdict, lightweight-eval-case, self-learning-loop). Charter decisions 6–8 record the adopt-not-build strategy. |
| EDB-17 | Add Henry's suggested publishers to the registry | 2026-07-20: researched all 5 suggestions; added `jeffallan` (individual, ~10.7k★, no evals → provisional) and `closedloop-ai` (research-lab, ships judges+self-learning evals → provisional) as `sources`. hve-core (Copilot, adjacent) + autoresearch (ML self-improvement pattern) recorded as charter references, not registry rows. SkillOpt → framework, not source (it's a methodology, not an extender publisher). |
| EDB-11 | `extenders.kind` vocabulary lacked `plugin` | Found verifying the W2/W3 builder (externals.yaml carries `kind: plugin`; the builder had patched only its throwaway instance and its handoff was cut off). Fixed durably in schema.py (EXTENDER_KINDS + dynamic applies_to maxSelect); live schema updated in place. Lesson: a builder "proof" on a held-out instance can mask a divergence from the tracked schema source — the session gate caught it. |
| EDB-5 | Judged assessments not yet run | W1 complete 2026-07-20: 345 `judged-v1` + 120 `review-v1` rows loaded via `load_assessments.py`; gates passed (exactly-one-primary 23/23, full section coverage, ingest re-run leaves judged rows untouched). See the W1 adjudication log below. W2/W3 same day: hooks + externals ingested (37 extenders; 197 mechanical rows incl. 16 hook checks, all present). |
| EDB-2 | PocketBase default 5000-char cap broke ingest of large bodies | Explicit `max` on `extenders.body` and `files.content` (2 MB); documented in schema.py. |
| EDB-1 | Collection PATCH without field ids drops-and-recreates columns (data loss) | schema.py merges by field name and preserves ids on update; noted as invariant in CHARTER.md. |

# Extender-DB — Project Plan

_Deliverables, acceptance criteria, and parallelism for the extender-db mini-project.
Subordinate to [CHARTER.md](CHARTER.md); open items and findings tracked in
[OPEN-ITEMS.md](OPEN-ITEMS.md)._
Status: active · 2026-07-20

## Milestone map (roadmap 2026-07-20 → work items)

Two tracks from the [CHARTER roadmap](CHARTER.md#roadmap-2026-07-20). Track I is our IP;
Track II adopts external eval machinery (SkillOpt + ClosedLoop judges).

| Milestone | Work item(s) | State |
|---|---|---|
| **M1** Coverage mapping | W9 body | next |
| **M2** Analysis surface | W4 | queued |
| **M3** Combine/coalesce | (new, post-W9) | queued |
| **M4** Adopt eval doctrine | W5 | frameworks loaded; judge-pattern formalization pending (EDB-21) |
| **M5** First comparative eval | W8 | queued (author benchmark; optional `opencode_exec` harness EDB-19) |
| **M6** Self-improvement loop | W10 | staged, gated behind M4+M5 |

Foundations already done: W0 seed · W1 judged · W2 hooks · W3 externals · W7 eval
provenance · the W9 taxonomy (`hsb3-jobs-to-be-done`) · the EDB-15 sources registry.

## W0 — Seed (DONE)

**Delivered:** 7-collection schema (`schema.py`), repo ingest (`ingest.py`) covering 23
skills + 4 agents with full file inventories, 10 distributions, 14 frontmatter dimensions,
5 seeded frameworks / 35 elements, 181 mechanical assessments.

**Acceptance (met):** schema and ingest idempotent (re-run creates 0 records); `make ci`
clean; database answers analytic queries (concise-body violations, custom frontmatter keys)
with correct values verified against the tree.

## W1 — Judged assessment pass (DONE 2026-07-20)

**Deliverable:** archetype tagging (`hsb3-skill-archetypes`: one `present` primary + any
`partial` secondaries per skill) and section-taxonomy coverage (`skill-section-taxonomy`:
present/absent per section) for all 23 skills, written by review agents under a dedicated
assessor value (e.g. `judged-v1`), with per-verdict `evidence` quoting the body.

**Acceptance:**
- Every skill has exactly one primary archetype; every (skill × section) pair has a verdict.
- Spot verification: an independent agent re-derives a sample (≥5 skills) from source with
  ≥90% agreement; disagreements adjudicated and recorded in OPEN-ITEMS.md.
- Ingest re-run afterwards leaves judged rows untouched (assessor discipline proof).

**Execution architecture (set 2026-07-20, foreman `deep`):** flat fan-out of judge agents
(sonnet), each owning a batch of ~4 skills; they read the skill dirs + framework criteria
and return **structured JSON verdicts with evidence quotes — they never touch the database**
(credentials stay with the session; assessor discipline stays enforceable). Adversarial
layer: opus reviewers blind-re-derive a stratified ~8-skill sample; the session adjudicates
disagreements. A session-run `load_assessments.py` validates the JSON against element slugs
and writes rows as `judged-v1`.

## W2 — Kind expansion: hooks (DONE 2026-07-20)

**Deliverable:** ingest the 4 roster hooks as `kind: hook` extenders (hook.py + config file
inventory); seed a `hook-dir-layout` framework from the ratified layout
(`scripts/check_hook_layout.py` is the source); mechanical checks (hook.py present,
stdlib-only import scan, config shape).

**Acceptance:** roster↔DB parity — every roster entry of an ingested kind has exactly one
extenders row; hook mechanical assessments populated; idempotence holds.

## W3 — Externals by reference (DONE 2026-07-20)

**Deliverable:** `externals.yaml` entries as `origin: external` extender rows (upstream URL,
no file ingest), so curation queries cover the full curated surface, not just self-authored.

**Acceptance:** all 6 externals present; distributions/membership untouched; queries can
partition authored vs sourced vs external.

**Execution note:** W2 and W3 both edit `ingest.py` — shared-file ownership, so one builder
runs them as a serialized chain (W2 then W3), not two parallel workers.

## W4 — Analysis surface

**Deliverable:** a `report.py` producing a markdown catalog report from the DB — conformance
summary per framework, custom-dimension inventory, size outliers, distribution coverage —
plus a small set of documented canned queries in README.md.

**Acceptance:** report runs from a fresh ingest with no manual steps; at least 3 findings
flow into OPEN-ITEMS.md as candidate repo actions (feeds the promotion gate).

**Execution note:** consider PocketBase **view collections** (pocketbase-best-practices
`coll-view-collections`) for the canned aggregations so the admin UI serves them too, with
`report.py` rendering markdown on top.

## W5 — Doctrine enrichment

**Deliverable:** additional cited frameworks worth measuring against — e.g. Anthropic's
skill-authoring best practices (skill-creator guidance), the plugin/marketplace packaging
spec — added as framework rows with source URLs; mechanical checks where checkable.

**Acceptance:** each new framework has provenance (`source_org`, `source_url`), status, and
≥1 assessment pass over the applicable kinds; no existing framework overwritten (supersede
only).

**Status (2026-07-20):** two **evaluation-methodology** frameworks landed (adopted, not just
measured against) — `skillopt` (Microsoft, MIT) and `closedloop-judges` (ClosedLoop,
Apache-2.0), each with cited elements read from source. This is milestone **M4** doctrine.
Remaining M4: formalize our own judge+rubric+CaseScore conformance pattern (EDB-21).

## W6 — Update-path proof

**Deliverable:** after a real catalog change lands on `dev` (any new or edited skill),
re-ingest and verify the diff shows in the DB (changed sha256s, metrics, assessments) with
no duplicate rows.

**Acceptance:** documented in OPEN-ITEMS.md with before/after counts; closes the last
promotion-gate box that scripts can close.

## W7 — Evaluation provenance (DONE 2026-07-20)

**Delivered:** `eval_runs` + `eval_responses` collections and a manifest-driven
`load_eval_run.py`. The W1 pass is backfilled in full: campaign method + criteria text,
each judge/reviewer's exact dispatch prompt, verbatim final message, verdict JSON, and
token/duration stats; the session adjudication as its own run; `mechanical-v1` as a
code-assessor run. All 662 assessment rows link to their run.

**Acceptance (met):** the chain verdict → run → prompt/response resolves for every
assessor; zero unlinked assessments; unique (run, role) prevents duplicate responses.

## W8 — Comparative quality evidence (= milestone M5)

**Approach (revised 2026-07-20, charter decisions 6–8):** adopt **SkillOpt** (framework
`skillopt`) as the methodology rather than build a bespoke harness. SkillOpt scores a skill
as trainable state against an authored task set with a machine-checkable reward, on cheap
models via its `openai_compatible` backend. The catch (verified at source): there is no
generic "grade my skill" — we author a small benchmark (task set + scorer) per skill under
test. Conformance/adherence evidence uses the `closedloop-judges` pattern onto our existing
`assessments`.

**Deliverable:** first comparative data for "why use this skill over the first skills.sh
hit," on ONE skill: an authored SkillOpt benchmark; trials of (a) no skill, (b) our skill,
(c) an external alternative (drawn from the `sources` registry — e.g. a `skills-sh` /
`tonsofskills` baseline); outcomes stored as `eval_runs` kind `comparative`/`experiment`
with full prompts/responses; a written, rerunnable protocol. **Optional sub-task:** stand up
an `opencode_exec` SkillOpt harness for faithful *agentic* eval of CC skills on free models
(a ~4-step change mirroring `run_claude_code_exec`; leans on `opencode-expertise`) — EDB-19.

**Acceptance:** one skill has comparative data answering the question with numbers + stored
transcripts; the protocol is documented and rerunnable; negative results are kept, not discarded.

## W10 — Self-improvement loop prototype (= milestone M6, gated behind W8)

**Deliverable:** a create→evaluate→improve→use loop run on ONE skill — using SkillOpt's
validation-gated edit / `skillopt_sleep` (transcript-mined, gated) and ClosedLoop
`self-learning` as references. Propose an edit, re-evaluate on a held-out split, keep only on
a strict improvement, human-in-the-loop adopt.

**Acceptance:** one skill improved with a **measured before/after eval delta**, the improved
artifact + both eval runs stored, and the adopt step recorded. Negative/no-improvement runs
kept as evidence.

## W9 — Portfolio coverage & relationships

**Deliverable:** a jobs-to-be-done framework (elements = the job types Henry's work
needs), assessments mapping every extender to the jobs it serves, and pairwise
relationship data (duplicative / conflicting / complementary — e.g. the
mise-en-place-scaffold ↔ repo-compliance-audit fill/measure pair W1 already surfaced).
Output: a coverage matrix with named gaps and overlap candidates for the
combine/coalesce workflow.

**Acceptance:** every extender maps to ≥1 job or is explicitly flagged jobless; the
matrix names concrete gaps and dupes; findings land in OPEN-ITEMS as candidate actions.

**Status (2026-07-20):** the **taxonomy is authored + loaded** — `hsb3-jobs-to-be-done`
(kind `job-taxonomy`, candidate), 24 job elements across 7 families (`category` field),
authored with Henry per EDB-13 at deliverable altitude / all-work scope. **Remaining:**
map all 37 extenders → jobs (assessments) + pairwise relationships → coverage matrix.
The mapping should record a per-job **disposition** (author / vendor / reference /
compare) drawn from the sources registry (EDB-15), not default gaps to "author from
scratch" (Henry, 2026-07-20).

## Parallelism

- **W1 and W2+W3 run in parallel** — W1's judges are read-only (JSON out); the W2/W3
  builder owns `ingest.py`; disjoint scopes, no worktree isolation needed.
- **W4 needs W1** (report includes judged conformance) but only W1.
- **DB writes stay with the session** — workers never hold credentials; the session runs
  the loaders, the gates (idempotency re-run, count parity, spot queries), and the commits,
  including each `data.db` delta in the same commit as its cause.
- **W5 is independent** of all others.
- **W6 is event-driven** — runs whenever the next real catalog change lands; not blocked on
  W1–W5.

## Promotion

When the [CHARTER.md](CHARTER.md) promotion gate is fully checked, bring the decision
(stay desk tool / graduate to `scripts/` + make lane / own repo) back to Henry with the
gate evidence. Not a work item until then.

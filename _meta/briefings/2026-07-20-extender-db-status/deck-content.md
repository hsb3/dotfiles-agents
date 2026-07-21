# Extender-DB status briefing — deck content (2026-07-20)

_Source of truth for the deck build. Register: explanatory — every slide opens with a
full-sentence lede; references spelled out; more slides over denser slides. Theme
continuity with the 2026-07-20 extender-db briefing (carbon-white / Avenir Next)._

---

## Slide 1 — Title

**Extender-DB — Status Briefing**
Subtitle: The coverage milestone is complete: every extender is now mapped to the jobs it serves.
Footer: dotfiles-agents · branch feat/extender-db · 2026-07-20 · M1 delivered

---

## Slide 2 — What this project is

Lede: **Extender-db is a queryable database of the 37 agent extenders in the marketplace, joined to the mental models used to judge and compose them.**

- Two halves joined by assessments: the **inventory** (what each skill, agent, hook, and external IS — full file contents, packaging, frontmatter) and the **doctrine** (frameworks: archetypes, section taxonomies, authoring specs, the jobs taxonomy, adopted eval methodologies).
- The design bet is "doctrine as data": mental models live as rows with provenance and status, so curation questions — what's covered, what's duplicated, what's missing — are **queries instead of impressions**.
- The repo stays the source of truth. The database is a rebuildable projection; edits flow repo → database, never backward.
- It lives as a `_meta/` desk tool on its own branch. Promotion to anything more is an explicit, gated decision that has not been made.

---

## Slide 3 — Where it stands (milestone strip)

Lede: **Track I — our own IP — has its foundation complete as of today; Track II — adopted evaluation — is loaded but not yet exercised.**

Milestone strip (visual):
- DONE: W0 seed · W1 judged pass · W2 hooks · W3 externals · W7 eval provenance · W9 taxonomy · **M1 coverage body (today)**
- NEXT: M2 analysis surface · M3 combine/coalesce (Track I) — M4 eval doctrine · M5 first comparative eval · M6 self-improvement loop (Track II, staged)
- Charter promotion gate: **2 of 4 criteria ticked** (judged pass ✓, hooks end-to-end ✓; findings→actions and update-path proof remain).

---

## Slide 4 — What the database holds now

Lede: **One thousand five hundred fifty assessment rows now connect the 37-extender inventory to nine frameworks, and every verdict resolves to the exact prompt and response that produced it.**

Table:
| Layer | Contents |
|---|---|
| Inventory | 37 extenders (23 authored skills · 4 agents · 4 hooks · 6 externals), full file contents, packaging, 10-publisher trust registry |
| Doctrine | 9 frameworks, 72 elements — including the 24-job taxonomy and two adopted eval methodologies (SkillOpt, ClosedLoop judges) |
| Assessments | 1,550 rows across mechanical, judged, review, and coverage passes — all provenance-linked |
| Coverage (new) | 24 job_coverage rows: 19 covered · 3 partial · 2 gaps |
| Relationships (new) | 46 rows: 24 complementary · 1 duplicative · 21 directed hand-off links |

---

## Slide 5 — The coverage matrix headline

Lede: **Of the 24 jobs the estate needs done, 19 are covered by at least one extender whose primary purpose is that job; three are only partially served; two are open gaps.**

Visual: 24 jobs as a status grid grouped by the 7 families (understand-research, build-software, assure-quality, orchestrate-sustain, produce-deliverables, govern-estate, extend-tooling), colored covered / partial / gap.
- Gaps: `research-question`, `produce-dataviz`
- Partial: `migrate-at-scale`, `configure-harness`, `operate-browser-ui`
- Deepest coverage: sustain-continuity (3 present + 1 partial), produce-diagram (4 present), integrate-knowledge-system (4 present), manage-backlog and enforce-standards (3 present each).

---

## Slide 6 — Every hole has an in-estate answer

Lede: **The punchline of the coverage work: nothing missing needs to be authored from scratch — every gap and weak spot already has a candidate in the estate.**

Table:
| Job | Status | Candidate |
|---|---|---|
| research-question | gap | Promote the user-level deep-research skill |
| produce-dataviz | gap | Promote the user-level dataviz skill |
| configure-harness | partial | Promote the user-level update-config skill |
| migrate-at-scale | partial | Fold a migration playbook into foreman-kit (architecture C is the mechanism) |
| operate-browser-ui | partial | Reference Anthropic's claude-in-chrome at harness level |

Kicker: These five calls are yours — issue #153, each with a default so a bare thumbs-up accepts all.

---

## Slide 7 — How M1 was verified (the crew)

Lede: **The mapping was produced by a layered crew, not a single pass: cheap judges fanned out, blind reviewers re-derived a sample, and the session adjudicated every disagreement.**

Diagram (pipeline): 7 sonnet judges (batched by kind, JSON only, no database access) → merge + validate by script → 888 coverage assessments loaded → 2 blind opus reviewers (stratified 8-extender sample) + 1 opus duplicative-pair check → session adjudication (10 rows patched, 4 boundary rules logged) → synthesis (relationships + job_coverage) → generated coverage matrix.

- Full provenance: three eval_runs hold every exact prompt and verbatim response (W7 invariant).
- The 662 pre-existing assessment rows survived the live schema change checksum-identical.

---

## Slide 8 — What verification actually changed

Lede: **Blind review is recall, not just error-correction — it added coverage the fan-out missed, and produced boundary rules that become the next rubric.**

- 10 verdict cells disputed on the 8-extender sample; 7 were adjacent-step (the recurring `partial` boundary, same as W1).
- The reviewers found a real capability the judges missed: readme-value-and-proof's headless-Chromium screenshot capture turned `operate-browser-ui` from a hard gap into partial coverage.
- Two thin-description externals were reassigned outright — evidence that judging externals by a one-line description is under-determined (now tracked as EDB-23).
- Four boundary rules were logged (for example: consuming the handoff is not sustaining continuity; nudge-only hooks cap at partial). They feed the M4 rubric directly.

---

## Slide 9 — The one confirmed redundancy

Lede: **Only one duplicative pair survived adversarial checking, and the check produced a reusable test for duplication claims.**

- Confirmed: the vendored coleam00 excalidraw skill duplicates the authored excalidraw skill — same output format, the diagrams hub routes only to the authored one. Recommendation: drop or fold (also moots the pending coleam00 vetting).
- Refuted: pptx-themes over pptx (base + override layer — composition, not duplication) and builder under lead (orchestrator + worker — distinct triggers).
- The doctrine: "produces the same deliverable" is a weak duplication signal. The real test is "same job the SAME WAY" — check for base+override, orchestrator+worker, and hub-routing before believing a duplicative call.

---

## Slide 10 — Relationships: the composition substrate

Lede: **Beyond coverage, M1 recorded how the extenders hand off to each other — the raw material a future composition planner will reason over.**

- 46 relationship rows: 24 complementary pairs within shared jobs, 1 duplicative, and 21 directed links (X precedes Y, X feeds-into Y).
- Example chains now queryable: scout → builder → reviewer; context-watermark → handoff-freshness-guard → session-handoff-surfacer; repo-compliance-audit → mise-en-place-scaffold; handoff → comms.
- The long-game consumer (deferred as EDB-22): a grounded planner that reads coverage + directional links + triggers and assembles an ordered toolkit per goal at request time.

---

## Slide 11 — Roadmap: two tracks, six milestones

Lede: **The strategy is to build only what is uniquely ours — the taxonomy, coverage, and curation decisions — and adopt or reuse everything else.**

- Track I (our IP): ~~M1 coverage~~ done → M2 analysis surface (report.py; the matrix renderer is its seed) → M3 combine/coalesce (consumes the duplicative pair + the promotion decisions).
- Track II (adopted eval): M4 formalize the judge+rubric pattern (the M1 boundary rules are its inputs) → M5 first comparative benchmark on one skill → M6 the self-improvement loop, gated behind M4+M5.
- Execution principle (charter decisions 6–8): methodologies are adopted (SkillOpt, ClosedLoop judges), the eval harness is **reused** — M5 runs through Henry's existing meta-harness on cheap models. Nothing bespoke gets built.

---

## Slide 12 — What needs Henry

Lede: **Six decision groups are queued in issue #153, each with a stated default — and one of them is the hard blocker for the evaluation track.**

- A. The five roster promotions from slide 6 (defaults: yes to all).
- B. Drop/fold the duplicative coleam00 excalidraw skill (default: drop).
- C. Accept vendor-only coverage for improve-code via anthropic's code-simplifier (default: accept).
- D. Approve the obsidian-cli reference fix next session — one piece of work that satisfies BOTH remaining promotion-gate criteria (default: yes).
- E. **Blocker:** the repo/path pointer to the meta-harness — M5 cannot start without it, and nothing gets built in its place by design.
- F. Optional: a saved gaps view in the database (default: skip; the matrix and a filter suffice).

---

## Slide 13 — Health and invariants

Lede: **Everything the project asserts about itself was verified by gates this session, and the operating knowledge is now written down.**

- All definition-of-done gates green: idempotent loaders proven on the live database, ingest discipline checksum-verified, zero unlinked assessments, make ci at 120 tests, data.db committed WAL-checkpointed.
- Standing invariants: session-only database credentials (judge agents are structurally read-only); every verdict provenance-linked; generated artifacts have regen scripts; schema changes merge-by-name.
- New this session: PROCEDURES.md — the runbook with script run order, the evaluated-pass pattern, gates, and the commit discipline — so any cold session can operate the project.

---

## Slide 14 — Status in one line

Lede: **Foundation complete and verified; the database now earns its keep answering coverage questions; next moves are five promotion calls and the meta-harness pointer — then the evaluation track goes live.**

- Branch feat/extender-db pushed through fa84ecd · working tree clean · server restartable via serve.sh
- Decisions: issue #153 / DECISIONS-NEEDED.md · Runbook: PROCEDURES.md · Matrix: coverage-matrix.md

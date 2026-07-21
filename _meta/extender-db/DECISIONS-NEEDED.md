# Extender-DB — owner decisions needed

_Everything blocked on Henry after the M1 coverage build (2026-07-20). Decide here or on
the tracking issue; each item names its default so a bare 👍 works. Where the gaps live:
`coverage-matrix.md` § "Gaps and partial coverage" (regen: `python3 render_matrix.py`), or
admin UI → `job_coverage` filtered `status != "covered"`._
Status: active · 2026-07-20 · tracking issue: [#153](https://github.com/hsb3/dotfiles-agents/issues/153)

## A · Roster promotions (EDB-24 — gaps/partials, all have in-estate candidates)

Every non-covered job can be closed without from-scratch authoring. Which promotions do
you want rostered? (Feeds M3 combine/coalesce.)

- [ ] **A1 `research-question` (gap)** — promote your user-level **deep-research** skill
      into the roster. _Default: yes._
- [ ] **A2 `produce-dataviz` (gap)** — promote your user-level **dataviz** skill.
      _Default: yes._
- [ ] **A3 `configure-harness` (partial)** — promote your user-level **update-config**
      skill. _Default: yes._
- [ ] **A4 `migrate-at-scale` (partial)** — no new extender; fold an explicit migration
      playbook into **foreman-kit** (architecture C is the mechanism). _Default: yes._
- [ ] **A5 `operate-browser-ui` (partial)** — accept disposition **reference**: rely on
      Anthropic's claude-in-chrome MCP at harness level, no roster extender.
      _Default: accept._

## B · Duplicative pair (M3 candidate, opus-verified)

- [ ] **B1** Drop or fold **`excalidraw-diagram-coleam00`** — it duplicates your authored
      `excalidraw` (same .excalidraw JSON output; the `diagrams` hub routes only to the
      authored skill; its "visual arguments" angle is wired to no trigger). Dropping it
      also moots the EDB-16(b) coleam00 vetting pass. _Default: drop._

## C · Vendor-only coverage

- [ ] **C1 `improve-code`** is covered ONLY by the vendored anthropic **code-simplifier**
      plugin (disposition `vendor`). Accept vendor dependence, or want an authored
      equivalent eventually? _Default: accept vendor._

## D · Charter promotion gate (currently 2/4)

- [ ] **D1** Approve running the **EDB-9 fix** (obsidian-cli phantom reference paths) next
      session — it is a ready findings→action (criterion 3 material) AND the re-ingest
      after a real catalog change doubles as the **criterion 4** update-path proof.
      _Default: yes._

## E · Blockers you hold

- [ ] **E1 EDB-14/19** — provide the repo/path pointer to your **meta-harness** (opencode
      + other coding-agent harnesses). Hard blocker for M5 (first comparative eval);
      nothing gets built in its place per decision 8.

## F · Nice-to-have (no action unless wanted)

- [ ] **F1** Add a `coverage_gaps` PocketBase **view collection** via schema.py (SQL view
      over `job_coverage` where status != covered) so the gaps are a first-class saved
      view in the admin UI instead of a filter. _Default: skip — matrix + filter suffice._

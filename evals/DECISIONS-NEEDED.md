# Extender-DB — owner decisions (decided 2026-07-20)

_The M1 decision batch. **DECIDED by Henry 2026-07-20: A–E accepted as recommended; F
REVERSED (build the view). E's pointer is still outstanding and blocks M5.** All resulting
work is tracked as epic [#154](https://github.com/hsb3/dotfiles-agents/issues/154)
(sub-issues #155–#167); #153 closed with the outcome record. Checkboxes below reflect the
decisions; this file is now a record, not a queue._
Status: decided 2026-07-20 · epic [#154](https://github.com/hsb3/dotfiles-agents/issues/154) · originally tracked as [#153](https://github.com/hsb3/dotfiles-agents/issues/153)

## A · Roster promotions (EDB-24 — gaps/partials, all have in-estate candidates)

Every non-covered job can be closed without from-scratch authoring. Which promotions do
you want rostered? (Feeds M3 combine/coalesce.)

- [x] **A1 `research-question` (gap)** — promote your user-level **deep-research** skill
      into the roster. _Default: yes._
- [x] **A2 `produce-dataviz` (gap)** — promote your user-level **dataviz** skill.
      _Default: yes._
- [x] **A3 `configure-harness` (partial)** — promote your user-level **update-config**
      skill. _Default: yes._
- [x] **A4 `migrate-at-scale` (partial)** — no new extender; fold an explicit migration
      playbook into **foreman-kit** (architecture C is the mechanism). _Default: yes._
- [x] **A5 `operate-browser-ui` (partial)** — accept disposition **reference**: rely on
      Anthropic's claude-in-chrome MCP at harness level, no roster extender.
      _Default: accept._

## B · Duplicative pair (M3 candidate, opus-verified)

- [x] **B1** Drop or fold **`excalidraw-diagram-coleam00`** — it duplicates your authored
      `excalidraw` (same .excalidraw JSON output; the `diagrams` hub routes only to the
      authored skill; its "visual arguments" angle is wired to no trigger). Dropping it
      also moots the EDB-16(b) coleam00 vetting pass. _Default: drop._

## C · Vendor-only coverage

- [x] **C1 `improve-code`** is covered ONLY by the vendored anthropic **code-simplifier**
      plugin (disposition `vendor`). Accept vendor dependence, or want an authored
      equivalent eventually? _Default: accept vendor._

## D · Charter promotion gate (currently 2/4)

- [x] **D1** Approve running the **EDB-9 fix** (obsidian-cli phantom reference paths) next
      session — it is a ready findings→action (criterion 3 material) AND the re-ingest
      after a real catalog change doubles as the **criterion 4** update-path proof.
      _Default: yes._

## E · Blockers you hold

- [ ] **E1 EDB-14/19** — provide the repo/path pointer to your **meta-harness** (opencode
      + other coding-agent harnesses). Hard blocker for M5 (first comparative eval);
      nothing gets built in its place per decision 8.

## F · Nice-to-have (no action unless wanted)

- [x] **F1** Add a `coverage_gaps` PocketBase **view collection** via schema.py (SQL view
      over `job_coverage` where status != covered) so the gaps are a first-class saved
      view in the admin UI instead of a filter. _Default: skip — matrix + filter suffice._
      _**Outcome: REVERSED by Henry 2026-07-20 — BUILD the view** (see header line and
      issue #161); the checkbox above records the default as presented, not the ruling._

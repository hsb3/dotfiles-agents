---
title: "roster: no notes/provenance free-text field; no machine cross-ref to promotion records"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded build plan for the roster provenance-field decision — the exact schema touch-points (roster header, README table, check_roster, validate_primitives, tests), the nanobanana summary migration, and the numbered owner decision (notes vs record vs ratify-summary-as-carrier).
notes: Decide-first issue — no build until the owner rules on the field question (Open questions, decision 1). All source claims verified 2026-07-03 against primitives-core.yaml, commit eb8057d, the workbench promotions log, and the guard scripts.
---

# roster: no notes/provenance free-text field; no machine cross-ref to promotion records

_The first promotion and retirement runs left their provenance in the wrong places: the
nano-banana-2 merge pointer had to be folded into the `nanobanana` roster entry's `summary`
(the human-facing capability line now carries lifecycle bookkeeping), and the freshly promoted
`opencode-expertise` entry has no machine link at all to its promotion record in the workbench
promotions log — the cross-reference is prose in a commit message and a log line, in both
directions. The residual work is one owner decision (add an optional provenance field to the
roster schema, or ratify summary-as-carrier explicitly) and, if a field is added, a small
additive schema change: roster header + README schema table, optional-field validation in the
two guard scripts, tests, and migrating the nanobanana pointer out of its summary. The parser
already tolerates unknown keys and the translation service consumes no free-text roster
fields, so the change surface is validation and documentation, not the build._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #39 (`type:chore`, milestone `P2 — Pilot proven`).
- Origin: surfaced by the first promotion/retirement runs — workbench wb#6 (first end-to-end
  promotion: `opencode-expertise`, CLOSED) and wb#7 (nano-banana-2 merge + first retirement
  record, CLOSED), both 2026-07-02.
- Relations: workbench wb#8 "Lifecycle-doc gaps surfaced by the first promotion + retirement
  runs" (same wave, CLOSED — the issue's Refs line); the workbench promotions log
  (`dotfiles-agents-workbench/docs/promotions-log.md`, append-only, established 2026-07-02)
  is the other half of the cross-reference this issue wants.
- Contract impact: **roster schema change** — `primitives-core.yaml` entry schema (header
  comment lines 8-14 + `primitives-core/README.md:22-38` field table) plus the two drift/
  content guards that enforce it (`scripts/check_roster.py`, `scripts/validate_primitives.py`)
  and their tests. No API/DB surface; `targets/` provably unaffected (see gate section).

## The problem (grounded in source)

**The summary surface is carrying provenance.** The `nanobanana` entry
(`primitives-core.yaml:393`) has, at line 402:

> `summary: "Gemini-native Nano Banana image generation and editing ... Prompting guidance
> (references/prompting.md) folded from the retired nano-banana-2 RunComfy wrapper (dedup
> 2026-07-02; see workbench docs/promotions-log.md)."`

Verified against `git show eb8057d`: that commit ("feat(merge): fold nano-banana-2 prompting
into nanobanana", 2026-07-02) is a one-line roster diff appending the merge pointer to the
summary, and its message says outright "Roster summary carries the merge pointer." The schema
has nowhere else to put it — the entry fields are `id / type / source / shelf / origin /
disposition / vendor / targets / plugins / summary` plus optional `requires` and
conditionally-required `upstream`/`ref` (`check_roster.py:26-40`, `primitives-core/README.md`
table rows 22-38). No notes, no record, no provenance slot.

**The promotion cross-ref is prose-only, both directions.** The `opencode-expertise` entry
(`primitives-core.yaml:473`, `disposition: qualified` at :478) has a clean capability summary
at :482 and **no pointer of any kind** to its promotion record. That record exists at
`dotfiles-agents-workbench/docs/promotions-log.md:81` ("promoted: 2026-07-02 by henry
(Sprint 1 GO, issue wb#6)") — and note it also **lacks its template's `roster-update:` line**
(the promotion-record template at promotions-log.md defines one; the nano-banana-2 retirement
record at :89-93 has it, citing eb8057d; the opencode-expertise record does not). So neither
artifact can be machine-walked to the other.

**Where a field would wire in** (verified in the guards):

- `check_roster.py::parse_roster` (:52-79) is a tailored line parser that accepts any
  `    key: value` line — unknown keys already parse with **zero parser change**, proven by
  the existing test `ParserTolerance::test_new_keys_parse_without_parser_changes`
  (`tests/test_check_roster.py:132`).
- `check_roster.py::check_entry_schema` (:112-143) is where an optional field's validation
  goes (pattern to copy: the optional `requires` check at :132-138 and the conditional
  `upstream`/`ref` check at :139-143). `REQUIRED` (:31-40) stays untouched — the field is
  optional.
- `validate_primitives.py` does the roster content checks (`summary` non-empty at :115-116);
  a shape/non-empty check for the new field lands beside it.
- `scripts/translate.py` **never reads `summary`** (zero occurrences in the file; it consumes
  `id`, `type`, `source`, `shelf`, `targets`, `plugins` — e.g. :365-368, :447-450, :478-481).
  A new free-text field is equally inert to the build: no target output changes, the
  results lock only hashes built files.
- Schema documentation lives in two places that must move together: the roster header comment
  (`primitives-core.yaml:8-17`) and the field table in `primitives-core/README.md:22-38`.

## Deliverables

Deliverable A is the decision artifact; B-E execute **only under Option 1 or 2** (a field is
added). Under Option 3 (ratify summary-as-carrier), only A' applies.

**A — Owner decision recorded.**
Rule on Open questions decision 1 (and its sub-decisions 2-4). Record the ruling on issue
number 39 and in this plan's frontmatter `notes:`.
Acceptance: the issue carries the ruling; this plan's status advances past draft only with a
recorded ruling.

**A' — (Option 3 only) Ratify summary-as-carrier.**
Amend the roster header comment (`primitives-core.yaml:8-17`) and the
`primitives-core/README.md` `summary` row (:35) to state explicitly that lifecycle pointers
(merge/dedup/promotion records) are carried in `summary` as a trailing parenthetical citing
the workbench promotions log.
Acceptance: both docs state the convention; `make ci` green (docs/comment-only change);
grep for the stated convention text succeeds in both files.

**B — Schema + docs (Option 1/2).**
Add the optional field to the entry schema in both documentation homes: the roster header
comment and the README field table (new row mirroring the `requires` row's optional
phrasing). State what it holds — under the recommended Option 1, a pointer to the lifecycle
record (workbench promotions log entry, or a merge/dedup commit), e.g.
`record: "workbench docs/promotions-log.md (promoted 2026-07-02, wb#6)"`.
Acceptance: README table and roster header list the field with the same name, optionality,
and semantics; no other schema row touched.

**C — Guard wiring + tests (Option 1/2).**
`check_roster.py::check_entry_schema`: if the field is present, it must be non-empty and not
the literal `null` (copy the `upstream`/`ref` non-null pattern at :139-143).
`validate_primitives.py`: same presence rule beside the summary check (:115-116); under
Option 1 additionally assert the value names a record home (substring/regex on
`promotions-log.md` or a commit hash) so a bare "misc note" cannot masquerade as a record
pointer. Tests: extend `tests/test_check_roster.py` (valid-with-field clean, empty-field
flagged) and `tests/test_validate_primitives.py` (shape check both ways); the existing
`ParserTolerance` test already covers parse-without-change.
Acceptance: `make ci` green; the new tests fail if the field validation is removed; an
entry with an empty field value fails `make check` or `make validate` by name.

**D — Migrate the nanobanana pointer (Option 1/2).**
Move the merge pointer out of `primitives-core.yaml:402`'s summary into the new field on the
`nanobanana` entry, restoring the summary to capability-only text (the pre-eb8057d sentence
plus the `references/prompting.md` mention, which IS capability); the field value cites the
dedup date, the workbench promotions log, and commit eb8057d. Add the field to
`opencode-expertise` (:473) pointing at its promotion record (wb#6, 2026-07-02) — this is
the machine cross-ref the issue title asks for.
Acceptance: `nanobanana` summary contains no lifecycle text (grep for `dedup` and
`promotions-log` in the summary line returns nothing); both entries carry the field; the
two pointers resolve — `dotfiles-agents-workbench/docs/promotions-log.md` contains the
opencode-expertise promotion record (:81) and the nano-banana-2 retirement record (:89);
`git show eb8057d` resolves.

**E — Rebuild + full gate (Option 1/2).**
Run `make build` then `make ci`. Expected: `targets/` byte-identical (translate.py consumes
neither `summary` nor the new field), so `build-check` passes with no target churn; if any
target file changes, that falsifies the inertness claim and the plan stops for re-grounding.
Acceptance: `make ci` green (check + validate + names + build-check + test); `git status`
shows no `targets/` modifications after the build.

**Out of scope (flagged, not built here):** backfilling the missing `roster-update:` line on
the workbench opencode-expertise promotion record, and any promotions-log template change —
workbench-side edits belong to a workbench issue (note it on wb#8's trail when closing this).

## Gate & contract hygiene

| Gate | Fires | Why |
| ---- | ----- | --- |
| make ci aggregate, required | yes | always; runs check + validate + names + build-check + test per Makefile line 28 |
| Roster drift guard, make check | yes | the schema this guard enforces changes; check_roster.py itself is edited plus roster entries gain a field |
| Targets drift guard, make build-check | yes but expected no-op | fires on any primitives-core.yaml edit per the gate menu; translate.py reads no free-text roster field, verified zero summary occurrences, so targets/ must come back unchanged |
| Naming taxonomy | no | no new primitive or plugin named |
| yamllint | manual only | listed in the gate menu but not wired: ci.yml runs only make ci, and no lefthook.yml or yamllint config exists in this repo; run yamllint by hand on primitives-core.yaml if edited |

Contract notes: the field is **optional** — `REQUIRED` in `check_roster.py:31-40` does not
grow, so the 80+ existing entries stay valid with zero migration beyond the two entries in
deliverable D. The roster header comment and the README table are the schema's two
documentation homes and must land in the same change (they already cross-reference each
other at `primitives-core.yaml:8`).

## Parallelism + landing order

| Unit | Owner | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A decision | owner | none | blocks everything; decide-first issue |
| B schema docs | one builder | A ruled Option 1 or 2 | roster header comment + README table, one change |
| C guards and tests | one builder | A ruled; B naming fixed | can draft against B's staged diff; touches the two guard scripts + two test files |
| D migration | one builder | B and C local | two roster entries; serialize after C so the new validation exercises the real values |
| E rebuild and gate | foreman | B, C, D staged | foreman runs make build + make ci; verifies targets unchanged |
| A' ratify path | one builder | A ruled Option 3 | replaces B-E entirely; comment and README wording only |

Land as **one PR** (B+C+D+E, or A' alone) once A is ruled — the change is small and the
guards, schema docs, and migrated entries are only coherent together. No timelines.

## Open questions / owner decisions

The issue is decide-first; nothing builds until decision 1 is ruled.

1. **The field question** — pick one:
   - **Option 1 (recommended default): optional `record:` pointer field.** Single-purpose —
     "where is this entry's lifecycle record" — which keeps it machine-checkable
     (validate_primitives can assert it names the promotions log or a commit) and directly
     delivers the issue-title cross-ref. Cost: a second free-text-ish field is still not a
     hyperlink; cross-repo resolution can't run in this repo's CI (see unverifiables).
   - **Option 2: optional `notes:` free-text field.** More general (any provenance or
     caveat), but unlintable by design — it will accumulate mixed content, and the
     machine-cross-ref goal degrades back to prose-in-a-different-slot.
   - **Option 3: ratify summary-as-carrier.** Zero code; amend the header comment + README
     to bless the current eb8057d practice. Cheapest, but permanently taxes the
     human-facing capability surface and gives `opencode-expertise` its cross-ref only by
     also polluting ITS summary.
   Recommendation: **Option 1** — the promotions log side already has a `roster-update:`
   slot pointing back; `record:` completes the loop in the opposite direction.
2. **(If 1/2) Value shape.** Recommend a quoted one-liner of the form
   `"<record home> (<event> <date>, <ref>)"` — e.g.
   `"workbench docs/promotions-log.md (dedup 2026-07-02, eb8057d)"` — with validation only
   asserting non-empty + names a record home. Alternative: structured sub-keys (repo, path,
   date), rejected as over-modeling for a hand-parsed roster.
3. **(If 1/2) Does `opencode-expertise` get the field in this change?** Recommend yes
   (deliverable D) — it is the issue's second finding, and doing only nanobanana would fix
   the pollution but not the missing cross-ref. Alternative: nanobanana-only, and let future
   promotions adopt the field going forward.
4. **(If 1/2) Backfill breadth.** Recommend **only the two entries the issue names** — the
   80 pre-log core entries re-qualify via the workbench requalification flow and gain
   `record:` values as their records are written, not by bulk backfill now.
5. **Workbench-side symmetry.** The opencode-expertise promotion record is missing its
   template's `roster-update:` line. Recommend: file/annotate on the workbench (wb#8 trail),
   out of scope here — confirm.

### Unverifiables (flagged)

- **Cross-repo pointer resolution is not CI-checkable**: this repo's CI checks out only
  itself (ci.yml: single checkout + `make ci`), so "the wb#6/wb#7 pointers resolve" is
  verified at review time (deliverable D's acceptance greps, run locally where the sibling
  repo exists), not by a gate.
- Whether `primitives-core.yaml` currently passes yamllint at all is unverified (yamllint is
  not wired in this repo and was not run for this plan); treat the yamllint row as manual
  due diligence, not a regression gate.

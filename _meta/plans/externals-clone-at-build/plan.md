---
title: "Build plan — clone-at-build externals: research upstreams, pin refs, translate.py clone step"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded build plan for #36 — the last unbuilt translation capability. Upstream research fan-out, J5 pin discipline, the translate.py clone step, drift-guard mechanics, and the open owner decisions (network-at-build in CI, drop policy, pin format).
notes: Drafted 2026-07-03 from live source (externals.yaml, translate.py, ADR 0003, CANON 11/16, workbench promotion-gate amendment 1). Owner decisions 1-7 unresolved.
---

# Clone-at-build externals: research upstreams, pin refs, translate.py clone step

_`externals.yaml` tracks 36 third-party extenders; only the 4 `kind: mcp` connection specs
render today. The remaining 32 (8 skills + 24 marketplace plugins) sit with `upstream: null`
on 31 of them and render nothing — the roster's last unbuilt translation capability (ADR
0003). What remains: research each entry's upstream URL, clear a J5 human review per the
amended workbench gate, pin an immutable ref (branch names pin nothing), extend the
externals schema for monorepo subpaths, and implement the `translate.py` clone-at-build step
that renders pinned clones into `targets/` under the existing byte-diff drift guard — or
drop the entry with a note. Pinned refs + the results-lock sha256 + translate.py as the
fetch script together satisfy the project-protocol provenance rule._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #36 (milestone `P3 — Rollout and retire`; the issue body's acceptance criteria are
  the outer gate for this plan).
- Origin: CANON decision 11 ("externals are tracked-and-cloned, never vendored", ratified
  2026-06-28 — `~/Documents/Claude/Projects/dotfiles-agents-cowork/_structure/CANON.md:50`),
  refined by CANON 16 for mcp (`CANON.md:57`); vault decision
  `third-party-extenders-clone-from-source`; backfilled as ADR
  `docs/decisions/0003-externals-tracked-not-vendored.md` (Consequences names #36 as the
  last unbuilt capability, `0003:34-35`).
- Relations: workbench `docs/promotion-gate.md` amendment 1 (2026-07-02) — sourced
  candidates, `provenance.yaml`, and J5 land in `externals.yaml`, so this plan is the
  receiving end of that pipeline; the gate's own note flags the `ref: latest` mcp entries as
  non-conforming "re-pin when next touched" (`promotion-gate.md:113-115`).
- Contract impact: touches `externals.yaml` (the tracker schema — its header comment
  `externals.yaml:8-15` IS the schema doc), `scripts/translate.py` (parser + build), the
  results lock `primitives-core-translation-results.json`, and `targets/` — a GENERATED
  surface (never hand-edit; `make build` regenerates, `make build-check` drift-guards).
  `scripts/validate_primitives.py` gains the pin-discipline checks. No roster
  (`primitives-core.yaml`) change.

## The problem (grounded in source)

**What EXISTS:**

- **The tracker, fully enumerated.** `externals.yaml` holds 36 entries under `externals:`
  (`externals.yaml:26-253`): 4 `kind: mcp` (`:28-55`), 8 `kind: skill` (`:58-107`), 24
  `kind: plugin` (`:110-253`). Field census:
  - `upstream: null` on **31** entries — 7 skills (excalidraw-diagram-coleam00 `:60`,
    codex-imagegen `:74`, codex-spreadsheets `:80`, the 4 notion-* `:86,92,98,104`) + all
    24 plugins (`:112` through `:250`).
  - `ref: null` on all 8 skills and all 24 plugins; nano-banana-2 is the only skill with a
    known upstream (`:68`, the runcomfy-skills repo) but its ref is unpinned (`:69`,
    "pin a tag/sha once selected").
  - The 3 stdio/package mcp entries pin `ref: latest` (`:31,38,45`) — a moving ref;
    claude_design (remote URL) has `ref: null` (`:52`).
  - `provides: ""` is empty on all 24 plugin entries (e.g. `:114`).
- **Only `kind: mcp` renders.** The build loop skips everything else:
  `if ext.get("kind") != "mcp": continue` (`scripts/translate.py:549-550`); the section
  header says "skill/plugin externals are clone-at-build (not implemented yet)"
  (`translate.py:547-548`); same caveat in `parse_externals`'s docstring
  (`translate.py:92-93`) and the tracker header (`externals.yaml:21-22`).
- **The parser already generalizes.** `parse_externals` (`translate.py:91-115`) reads any
  flat `key: value` field per entry — a new `path:` or `sha:` field costs zero parser code.
- **Drift-guard mechanics.** `make build` runs `translate.py` in place; `make build-check`
  runs `translate.py --check` (`Makefile:16-20`), which rebuilds the full tree into a temp
  dir and **byte-diffs** it against committed `targets/` plus the results lock
  (`translate.py:643-682`, `diff_trees` at `:618-640`). Determinism is a stated contract:
  "stable ordering, no clocks/timestamps in output — so the --check drift guard never
  false-fails" (`translate.py:17-18`). Every rendered artifact is fingerprinted into the
  lock via `sha256_path` (`translate.py:180-197`). CI runs `make ci` (= check validate
  names build-check test, `Makefile:28`) on ubuntu-latest (`.github/workflows/ci.yml`).
- **The pin-discipline rules are ratified.** Workbench `docs/promotion-gate.md` amendment 1
  (2026-07-02): sourced candidates carry `provenance.yaml` with non-null
  `origin/kind/upstream/ref`, and "`ref` must not be a branch name — a moving ref pins
  nothing" (`promotion-gate.md:84-96`); **J5** is a per-ref, human-attested upstream review
  — "clone-at-build (G4, deferred) pins at build; J5 pins what the build is allowed to
  point at" (`promotion-gate.md:98-106`); a passing sourced candidate lands as an
  `externals.yaml` entry, never a copy in `primitives-core/` (`:107-111`).
- **Adjacent guards.** `validate_primitives.py` already validates externals mcp specs
  (`validate_primitives.py:14,155-156`); `check_naming.py` deliberately does NOT lint
  externals ids ("sourced items keep their upstream identity", `check_naming.py:14`);
  `check_roster.py` doesn't read externals at all. Test coverage of externals today is one
  parse assertion (`tests/test_translate.py:205-208`).
- **Supply-chain context (this machine).** npm is pinned `allow-git=none` and package
  managers carry 7-day install cooldowns — but those govern package-manager installs, not
  raw `git clone`. The clone step is git-clone-at-build **by design**; its equivalent
  protections are the gate's own: J5 review of the exact ref, immutable pins, and the
  provenance chain. Project-protocol section 6 requires "URL + sha256 + fetch script" for
  every acquired external artifact — satisfied here by `externals.yaml` (URL + pinned
  ref) + `scripts/translate.py` (the fetch script) + the results lock (per-artifact
  sha256), provided the ref is immutable.

**What is MISSING:**

- Upstream URL + ref for 31 entries; a ref for all 32 skill/plugin entries; `provides:`
  one-liners for the 24 plugins.
- Any schema support for monorepo subpaths — nano-banana-2's known upstream
  (`externals.yaml:68`) is a multi-skill repo, so "clone the repo" is not "get the skill";
  the same likely holds for the 24 marketplace plugins (plausibly 1-2 shared upstream
  monorepos — research hypothesis, unverified).
- The clone step itself: fetch-at-pin, strip `.git`, place the (sub)tree into `targets/`,
  record it in the results lock — and a story for how `--check` stays deterministic and
  CI-viable when the build needs the network.
- Machine enforcement of the issue's acceptance criterion "every entry has non-null
  upstream+ref or is removed" — nothing guards `upstream: null` or branch-name refs today.
- J5 attestations: zero of the 32 skill/plugin entries have been reviewed; the 3
  `ref: latest` mcp pins are explicitly non-conforming (`promotion-gate.md:113-115`).

## Deliverables

**A — Upstream research sheet (fan-out).**
One research row per non-mcp entry (32 rows): candidate upstream URL, exact commit sha (+
human-readable tag if one exists), subpath within the repo if monorepo, a `provides:`
one-liner, license note, and a keep/drop recommendation with rationale (usage signal: is it
in the installed plugin cache / actually invoked?). Staged as
`_meta/plans/externals-clone-at-build/research-sheet.md` (desk artifact, not repo contract).
Grouping hint: 4 notion-* skills, 2 codex-* skills, and the 24 marketplace plugins likely
collapse to a handful of upstream repos.
`Acceptance:` every one of the 32 entries appears exactly once on the sheet with either a
resolvable URL+sha (spot-check: `git ls-remote <url> <sha>` or a web permalink) or a drop
recommendation citing why; no row left "unknown" without a drop recommendation.

**B — Owner J5 ruling + tracker update.**
Henry reviews each keep-recommended upstream at its exact ref (install scripts, network
calls, prompt-injection surface — the J5 checklist, `promotion-gate.md:98-100`) and rules
keep/drop. `externals.yaml` is then edited: keeps get non-null `upstream` + immutable `ref`
(+ `path:`, `provides:`); drops are **removed** with a one-line note in the PR description
naming each dropped id and why (the issue's "dropped with a note").
`Acceptance:` `grep -c 'upstream: null' externals.yaml` returns 0; no `ref:` is
main/master/latest/HEAD or null on a skill/plugin entry; every id removed from the tracker
is named in the landing PR body; reviewed refs recorded per entry (comment or
`reviewed:` field — decision 2).

**C — Schema extension + pin guard.**
Extend the entry schema (header comment `externals.yaml:8-15`) with optional
`path: <subdir>` (monorepo subtree to place) and the pin convention from decision 2.
Extend `scripts/validate_primitives.py` (the `make validate` lane) to enforce, for every
`kind: skill|plugin` entry: non-null `upstream`, non-null `ref`, ref not a branch name
(main/master/latest/HEAD — mirror `promote_check.py`'s list). This makes the issue's
acceptance criterion a standing gate, not a one-time audit.
`Acceptance:` `make validate` fails on a fixture entry with `upstream: null` or
`ref: main` and passes on the landed tracker; the header comment documents every field the
parser consumes.

**D — translate.py clone-at-build step.**
In `build()`, after the mcp externals loop (`translate.py:549-576`): for each
`kind: skill|plugin` external, materialize the pinned upstream (clone/fetch at the sha into
a gitignored local cache keyed by url+sha — decision 1), strip `.git` and volatile files
(reuse `IGNORE`, `translate.py:40`), copy the `path:` subtree into a dedicated generated
namespace per target (proposed `targets/<target>/externals/<kind>/<id>/` — decision 4;
skills honor the entry's `targets:` list, plugins are claude-code only per their current
`targets:` values), and `rec()` it into the results lock with capability `clone` and the
tree sha256. `--check` must stay green offline when pins are unchanged (decision 1's
short-circuit) and must fail loudly when a pin changed but the cache/network can't supply
it. Cloned trees are committed under `targets/` like every other rendered artifact, so the
committed repo remains the usable artifact even if an upstream vanishes.
`Acceptance:` `make build` then `make build-check` green twice in a row (determinism);
editing a `ref:` without rebuilding fails `make build-check`; `git status` shows no litter
outside `targets/` + the lock; the cache dir is gitignored.

**E — Tests.**
`tests/test_translate.py`: parse coverage for `path:`/new fields; clone-step unit tests
against a **local fixture git repo built in tmp by the test** (no network in the test
suite — construct a repo, commit, pin the sha, render, assert placement + lock entry +
`.git` stripped). `tests/test_targets.py`: shape checks over the committed externals
namespace (every tracker skill/plugin entry has a rendered tree and a lock row; no orphan
trees for removed ids). Guard tests for C's validator (branch-name ref fails).
`Acceptance:` `make ci` green; deleting a rendered externals tree or its lock row fails the
suite; the suite passes with the network disabled.

**F — Re-pin the mcp `ref: latest` entries.**
Per the gate's "re-pin each when it is next touched" note (`promotion-gate.md:113-115`) and
decision 5: github (`ghcr.io` image digest), azure-tools + chrome-devtools (npm exact
versions), claude_design (`ref: n/a` or a documented remote-endpoint convention — it is a
URL, not a code ref).
`Acceptance:` no `ref: latest` remains in `externals.yaml`; `make validate` + rendered mcp
fragments unchanged in shape (`make build-check` green — specs themselves don't change,
only tracker provenance fields).

## Gate & contract hygiene

| Gate | Fires | Why |
| ---- | ----- | --- |
| CI aggregate (make ci, required) | yes | always; now includes the extended validate lane and the clone-aware build-check |
| Targets drift guard (make build-check) | yes | externals.yaml is a translate.py input (translate.py:36) and targets/ gains the cloned trees; never hand-edit targets/ |
| Content validation (make validate) | yes | validate_primitives.py extended with the pin guard (C); already reads externals mcp specs at :155-156 |
| Roster drift guard (make check) | no | primitives-core.yaml untouched; no primitive added, removed, or renamed |
| Naming taxonomy (make names) | no | externals ids are deliberately unlinted - sourced items keep upstream identity (check_naming.py:14) |
| yamllint | yes, advisory | externals.yaml is edited heavily; yamllint is in the gate menu but wired into neither make ci nor lefthook - run it manually before the PR |
| actionlint | only if decision 1 adds CI caching | ci.yml edit would trigger it; otherwise no workflow change |

Contract notes: `targets/` and the results lock are generated — all landed diffs there come
from `make build`. The drift guard gains a new failure mode (network/cache miss on changed
pins); its error message must say "run make build" vs "upstream unreachable" distinctly.
The `externals.yaml` header comment is the schema's documentation of record — C updates it
in the same change that extends the parser. Committing ~30 cloned trees will visibly grow
the repo; that is the design (committed targets are the artifact), not an accident to
"fix" with submodules.

## Parallelism + landing order

| Unit | Owner | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A research sheet | fan-out agents, batched by suspected upstream (notion, codex, marketplace-plugins, singles) | none | read-only; web research; agent claims are hypotheses - each URL+sha spot-checked before the sheet is final |
| C schema + pin guard | one builder | decisions 2, 4 | small; lands first so B's tracker edits are guarded from birth |
| D clone step | one builder | C landed; decision 1 | serializes: translate.py is one file, one owner; developable against nano-banana-2 (only entry with a known upstream) pinned as pilot |
| E tests | one builder | D staged locally | fixture-repo tests draftable against D's staged diff |
| B J5 ruling + tracker edit | Henry (attestation) then one builder (edit) | A final; C landed | J5 is human and per-ref - the hard serialization point; can land in batches (keeps in waves, drops in one sweep) |
| F mcp re-pins | one builder | C landed; decision 5 | independent of B/D; cheap |

Landing order: **PR1 = C + D + E + pilot pins** (nano-banana-2 + excalidraw-coleam00 once
J5-cleared — proves the machinery end-to-end with 2 entries), then **PR2..n = B batches +
F** as attestations clear, each batch running `make build` and landing its cloned trees.
Drops can land early (PR1 or their own small PR) — removing entries needs no clone
machinery. The issue closes when the tracker has zero null/branch pins and `make ci` is
green with externals rendered.

## Open questions / owner decisions

1. **Network-at-build in the required CI gate.** `--check` rebuilds everything
   (`translate.py:648-657`); naive cloning means every CI run re-clones ~30 repos on a cold
   runner — slow, flaky, and the required gate acquires 30 external availability
   dependencies. **Recommend:** pin-keyed short-circuit — `--check` verifies each committed
   externals tree's sha256 against the results lock and re-clones ONLY entries whose
   url+ref+path changed vs the lock (deterministic because pins are immutable). CI stays
   offline-capable on unchanged pins; a pin-changing PR needs network (acceptable — that PR
   just ran `make build` locally). Alternatives: actions/cache for the clone cache; or
   accept full re-clone.
2. **Pin format.** **Recommend:** `ref:` holds the full 40-char commit sha (the only truly
   immutable git pointer — tags can be re-pointed), with the human-readable tag and the J5
   review date in a trailing comment on the entry. Alternative: a separate
   `reviewed: <date> <by>` field if grep-ability matters more than schema minimalism.
3. **Drop policy for the 24 marketplace plugins.** They ship `provides: ""` and are
   plausibly installable directly from their public marketplace at any time. **Recommend:**
   drop-by-default any plugin with no usage signal (not in the installed plugin cache, no
   memory/handoff mention); keep only what is actually used — every keep costs a J5 review
   plus a committed tree forever. The issue explicitly allows "dropped with a note", and a
   dropped id can re-enter later via the normal sourced-candidate path.
4. **Landing namespace in targets/.** **Recommend:** `targets/<target>/externals/<kind>/<id>/`
   — separate from the roster surface, so cloned plugins do NOT join
   `marketplace.json` (the catalog stays homegrown-only, its version metadata stays
   meaningful) and cannot collide with roster plugin assembly. Alternative: merge into
   `targets/claude-code/plugins/` + catalog entries flagged external; defer to
   dotfiles-bootstrap's install ergonomics if that repo has an opinion.
5. **Re-pin the `ref: latest` mcp entries now (F) or defer?** The gate says re-pin "when
   next touched" and this change touches the file. **Recommend:** in scope — it is three
   version lookups plus one convention call for claude_design's remote URL (`ref: n/a`).
6. **Pin-update cadence.** **Recommend:** none — no scheduled bumps. A re-point is a
   deliberate `provenance`/tracker edit requiring J5 re-review per the gate
   (`promotion-gate.md:102-104`); staleness is a feature (drift protection), not a bug.
   Upstream-vanished is retirement criterion (c) in the gate — handle on discovery.
7. **Offline / upstream-gone behavior.** **Recommend:** committed `targets/` is the
   artifact of record — deploys never need the network; `make build` with unchanged pins
   uses the local cache or the committed tree and only a pin CHANGE requires reachability.
   If an upstream vanishes, the committed clone keeps working and the entry is retired or
   re-pointed at leisure. State this in the externals.yaml header so the failure mode is
   documented where the schema lives.

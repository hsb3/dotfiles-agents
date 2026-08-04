# Externals materialization — decisions memo (task-10)

_Decision-prep for the second owner sign-off. Drafted 2026-08-03. Author: session (Opus 4.8)._
_Feeds: backlog task-10 (AC#1 "decisions 1–7 ruled and recorded"). Sibling: task-11
(vendored-skill-quality) owns the quality-gate + feedback layer on top of whatever this settles._

---

## RULING (owner, 2026-08-03) — recorded as decision-6

All recommendations below **approved**: D1 = pinned-vendored-copy (supersedes clone-at-build),
D3 SHA-only, D4 sync-model drift checker (diverged = loud fail), D5 require-or-reclassify, D7
new `origin: vendored` class + narrow ADR 0015 amendment. Plus:

- **Drop the 4 plugin externals** (frontend-design, code-simplifier, typescript-lsp,
  skill-creator) — install-from-upstream, not re-hosted. Only `pptx` stays vendored.
- **Vendoring needs a minimum bar** — a narrow exception, not a default. Sanctioned scenarios:
  (1) *modification* of an external (pptx-themes = base + our layer); (2) a *bundle of homegrown
  + external* shipping as one unit. Rule drafted under **task-26**, cited by the ADR 0015
  amendment.

The analysis that follows is the pre-ruling memo, kept as the reasoning trail.

---

## TL;DR

The question task-10 was written to answer — "build clone-at-**build**" — was overtaken by
ADR 0017. There is no build step or tracked `dist/` anymore, so the only two live options are
**clone-at-install** or **pinned-vendored-copy**. The owner's sign-off note pointed straight at
the second: _"it might just be simpler to keep a pinned, vendored copy in the repo."_

**It is simpler, and there is already a working precedent in-tree** (`pptx-themes/base/` — a
verbatim, tracked, LICENSE-carrying copy of the Anthropic pptx skill). My recommendation is to
**pivot to pinned-vendored-copy with a first-class provenance class**, which supersedes the
clone-at-build design of GH #36 / ADR 0003 and requires a narrow amendment to ADR 0015. The
seven decisions below are framed around that fork: **D1 is the fork itself; D2–D7 mostly
*dissolve or simplify* if D1 goes to vendoring, and stay as real design work only if it goes to
clone-at-install.**

Note on "decisions 1–7": the phrase is used across #36 and the task but never enumerated in one
place. I reconstructed the canonical set below from the #36 body, the vault translation-service
TDD deltas (captured in #36 comments), and ADR 0017's reframe. If the owner had a different
seven in mind, say so and I'll re-map.

---

## Background you may not have paged in

- **ADR 0017 killed build-time.** `dist/` and the generators are retired; the source tree *is*
  the Claude Code install surface; the one irreducible transform (opencode) runs **at install**
  via `gen_opencode.py`. So "clone-at-build" has no build to hook into — it becomes
  "clone-at-install," a peer of the opencode laydown.
- **ADR 0015** forbids `origin: sourced` bodies under `primitives-core/`; third-party is
  recorded by reference in `externals.yaml` (upstream + pinned SHA) and materialized elsewhere.
  Enforced by `scripts/check_provenance.py` — **at roster-entry granularity** (it checks each
  roster id's `origin` field, not each file).
- **The precedent that matters:** `primitives-core/skills/pptx-themes/base/` is a **verbatim
  vendored copy** of `anthropics/skills@fa0fa64:skills/pptx` — tracked in git, with
  `LICENSE.txt` and README attribution. It escapes the 0015 check because the *roster entry*
  `pptx-themes` is `origin: authored`; the vendored `base/` rides inside it invisibly. So the
  repo already vendors third-party successfully — just informally, through a loophole rather
  than a sanctioned convention.
- **externals.yaml** currently records **5 kept externals** (frontend-design, code-simplifier,
  typescript-lsp, skill-creator, pptx), each with upstream + a frozen 2026-07-17 HEAD SHA. All
  five upstreams are Anthropic-official repos (`claude-plugins-official`, `skills`). Four are
  plugins; one (pptx) is the skill already vendored under pptx-themes.
- **Reference impl** (if we go clone-at-install): `functionform-asmbl`'s
  `services/github.py` + a `sync_status {up_to_date|behind|diverged|not_found}` drift model
  against a stored `source_commit_sha`/`ref`. Adaptable as a *freshness checker* either way.

---

## D1 — Materialization strategy (THE fork; gates D2–D7)

**Question:** how does third-party content reach an installed plugin?

| Option | What it means | Cost | Fit with ADR 0017 |
|---|---|---|---|
| **A. Clone-at-install** | Installer reads `externals.yaml`, clones each pinned upstream, materializes it into the plugin dir at install time | Network-at-install; integrity/drift/failure handling; a new mechanism to build + maintain; CI needs a network lane | Peer of opencode laydown, but *heaviest* new machinery in a repo whose whole ADR-0017 thesis is "less machinery" |
| **B. Pinned-vendored-copy** ⭐ | Third-party content is committed into the tree at a pinned SHA, with `LICENSE` + attribution + a provenance record; a freshness checker flags upstream drift as an *optional maintenance* step | Repo carries the bytes (~size); a periodic drift-check discipline; ADR 0015 must be amended | Source tree *is* the install surface — zero install-time moving parts, offline-deterministic, matches the pptx-base precedent already shipping |
| **C. Hybrid** | Vendor skills, clone-at-install for whole plugins | Both mechanisms' complexity | Worst of both for only 5 items |

**Recommendation: B (pinned-vendored-copy).** Rationale:

1. **ADR 0017's whole direction is minimize machinery / nothing generated.** Clone-at-install
   reintroduces exactly the install-time complexity 0017 spent effort removing — for 5 items,
   all from stable Anthropic repos, with near-zero churn.
2. **The precedent already works.** pptx-base proves vendoring-with-attribution is viable and
   invisible-cost at install. We'd be *formalizing an existing practice*, not inventing one.
3. **Determinism + offline.** No install-time network, no partial-clone failure mode, no CI
   network lane. A consumer `git clone` gets a complete, working marketplace.
4. **0015's actual intent is preserved.** 0015 exists to keep the **provenance line clean** and
   forbid *silent* drift / unattributed re-hosting. Vendoring with a first-class
   `origin: vendored` class + `LICENSE` + pin + a drift checker keeps provenance *explicit* —
   it changes the mechanism (vendor-with-record vs reference-only), not the principle.

**The cost to accept honestly:** B means the repo re-hosts other people's bytes, which is what
0015 was written to prevent. The mitigation is making it *sanctioned and legible* (D7) rather
than a loophole. If the owner weighs "never re-host" as inviolable, that's the case for A.

**If D1 = B, then D2, D3(partial), D6 dissolve; D4/D5/D7 simplify. If D1 = A, all seven are
live.** Each below is annotated accordingly.

---

## D2 — Network posture / CI lane

**Question:** does materialization touch the network, and if so how is CI kept deterministic?

- **If B (vendored):** *Dissolves.* No install-time network; offline lanes stay as-is. The
  optional drift checker is a manual/scheduled maintenance command that may hit the network,
  never part of `make ci`.
- **If A (clone-at-install):** Real. Keep all current offline lanes network-free and required;
  isolate clone-at-install in a **separate network CI lane** (per the vault TDD delta). Install
  itself must degrade gracefully offline (see D6).

**Recommendation:** N/A under B (preferred). Under A, separate network lane, non-blocking for
the offline gate.

---

## D3 — Ref-pin format

**Question:** what is a valid pin?

**Recommendation (applies to both A and B): immutable commit SHA only; never a branch or tag.**
This is already the `externals.yaml` schema rule and the frozen 2026-07-17 SHAs honor it. Under
B the SHA is recorded alongside the vendored copy as the "vendored-from" provenance; under A it
is the clone target. Settled; included for completeness. (Tags are mutable on many upstreams, so
excluded even though annotated tags feel immutable.)

---

## D4 — Integrity verification

**Question:** how do we detect that what we have ≠ what the pin says it should be?

- **If B:** The vendored bytes *are* the artifact; integrity = "does the tree match the recorded
  SHA's content." A **drift checker** (adapted from functionform's sync model) reports
  `up_to_date | behind | diverged` against the upstream at the pinned SHA. `diverged` (upstream
  rewrote history at that SHA, or our copy was hand-edited) is a **loud failure**, distinct from
  `behind` (a newer upstream exists — informational, not a failure).
- **If A:** Same loud-on-mismatch rule, enforced at clone time: a hash mismatch at the same ref
  = hard fail (upstream rewrote history), distinct from a missing/absent pin.

**Recommendation:** Adopt the `{up_to_date | behind | diverged | not_found}` model either way.
**diverged → loud failure; behind → informational.** Under B this is a maintenance command;
under A it's an install-time gate.

---

## D5 — null-upstream semantics

**Question:** what does a tracked third-party item with no resolvable upstream mean?

This is the one genuine tension in the sources: the vault TDD said "skip-and-record, don't
fail"; #36's framing said "non-null upstream+ref OR removed"; `externals.yaml`'s
`ENFORCE_EXTERNALS_INTENT` currently **requires** non-null. task-11 independently wants a
"no-upstream / locally authored disposition" for things like the PocketBase skill.

**Recommendation: require-or-reclassify (not require-or-remove).** An entry with no upstream
isn't an *external* — it's either (a) locally authored → move it to a proper `origin: authored`
primitive, or (b) a genuinely orphaned vendored copy → give it an explicit
`origin: vendored, upstream: null, disposition: orphaned` record so it's *tracked and visible*
rather than silently deleted. This satisfies both the "must be recorded" intent and task-11's
disposition need, and avoids the data-loss of require-or-remove. All 5 current externals have
non-null upstreams, so this bites only future entries.

---

## D6 — Drop / failure policy for un-pinnable or vanished upstreams

**Question:** what happens when an upstream 404s or a pin no longer resolves?

- **If B:** *Largely dissolves* — we already hold the bytes, so a vanished upstream never breaks
  an install; it only makes the drift checker report `not_found`, which downgrades that entry to
  `disposition: orphaned` (D5) and files a task-11 review. Install is never at the mercy of a
  third party's repo lifecycle.
- **If A:** Real and sharp — a vanished upstream **breaks every install** until fixed. Needs a
  fallback (cache/mirror) or install-time skip-with-loud-warning policy, which starts to
  reinvent vendoring anyway.

**Recommendation:** N/A under B (preferred) beyond the `not_found → orphaned` downgrade. D6's
sharpness under A is itself an argument for B.

---

## D7 — Provenance placement & ADR 0015 reconciliation

**Question:** where do vendored third-party bytes live, how are they attributed, and how does
the provenance check treat them — so it's sanctioned, not a loophole?

**Recommendation (the governance change B requires):**

1. **Add a third provenance class: `origin: vendored`** (distinct from `authored` and
   `sourced`). A `vendored` entry carries non-null `upstream` + pinned `ref` + a `LICENSE` in
   its dir + attribution in its README. This makes today's pptx-base loophole a *named, checked*
   status instead of an invisible rider on an `authored` entry.
2. **Amend ADR 0015** from "third-party is *never* copied in" to "third-party is copied in
   **only** as an `origin: vendored` entry meeting the attribution+pin contract; `origin:
   sourced` under `primitives-core/` remains forbidden." The *principle* (clean provenance line,
   no silent unattributed re-hosting) is unchanged; the *mechanism* widens.
3. **`check_provenance.py` grows a `vendored` arm:** every `vendored` roster entry must have
   `LICENSE` present + non-null upstream+ref; enforce at file granularity for vendored dirs so a
   third-party body can't hide inside an `authored` entry again (closes the pptx-base loophole by
   reclassifying pptx-themes's base as `vendored` provenance).
4. **Defer the quality gate + feedback-channel pointer to task-11** — that's its charter; this
   memo only fixes *placement + attribution + provenance class*.

Under A, D7 shrinks to "attribution/license shipped with the materialized clone" and no 0015
amendment is needed (0015 stays reference-only) — but then the pptx-base copy is still a
standing 0015 violation that must be resolved separately (re-clone it at install too, or
re-author it).

---

## What I recommend the owner rule

| # | Decision | Recommendation |
|---|---|---|
| **D1** | Materialization strategy | **Pinned-vendored-copy (B)** — supersede #36/ADR 0003 clone-at-build |
| D2 | Network / CI lane | Dissolves under B (no install-time network) |
| D3 | Ref-pin format | Immutable SHA only (settled) |
| D4 | Integrity | `up_to_date/behind/diverged/not_found`; **diverged = loud fail** — as a maintenance checker |
| D5 | null-upstream | **Require-or-reclassify** (`origin: vendored, disposition: orphaned`), not require-or-remove |
| D6 | Drop policy | Dissolves under B (`not_found → orphaned`, install never breaks) |
| D7 | Provenance placement | **New `origin: vendored` class + narrow ADR 0015 amendment**; check_provenance grows a vendored arm; quality → task-11 |

**If the owner picks B**, the build work is small: (1) ADR 0015 amendment + a short new ADR (or
0003 supersession) recording the vendored model; (2) reclassify pptx-themes/base + the 4 plugin
externals as `origin: vendored`, vendoring the 4 plugins at their pinned SHAs with LICENSE +
attribution; (3) `check_provenance.py` vendored arm; (4) an optional `make externals-drift`
checker adapted from functionform. No install-time mechanism, no network CI lane.

**If the owner picks A**, all seven stay live and the build is the heavier clone-at-install
mechanism + network lane + the pptx-base cleanup — the original #36 scope, minus the retired
build step.

---

## Open questions for the owner (beyond D1–D7)

1. **Do the 4 plugin externals even need to ship from here?** frontend-design, code-simplifier,
   typescript-lsp, skill-creator are all installable directly from
   `anthropics/claude-plugins-official`. If the value is only *cataloging* them (not
   re-distributing), a fifth-option "**reference-only, install-from-upstream**" beats both A and
   B for those four — vendor only what we actually compose against (pptx). Worth a yes/no.
2. **Attribution register** — is a `LICENSE` + README attribution line sufficient, or do you
   want a NOTICE/THIRD-PARTY manifest at repo root?
3. Confirm the "decisions 1–7" mapping above matches what you intended, or hand me your list.

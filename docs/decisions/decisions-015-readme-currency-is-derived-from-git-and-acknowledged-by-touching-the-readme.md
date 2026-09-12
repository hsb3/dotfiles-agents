---
id: "decision-015"
title: README currency is derived from git and acknowledged by touching the README
date: '2026-09-07'
status: accepted
---
## Context

Skills and plugins each own a README, but nothing signals whether a README still describes
the unit it sits next to. An earlier proposal — a hand-maintained registry mapping each unit
to its last-reviewed commit — was raised on kata card `9x2r` but never ruled.

## Decision

Owner ruling, 2026-09-07 (via the sign-off form on `9x2r`):

1. Currency is derived from git — `git log -1 --format=%H -- <path>` for the unit's body
   versus its README — with no new tracked registry file.
2. Any file inside the skill or plugin unit counts as a change, not only `SKILL.md` or its
   description.
3. The acknowledgement is the README being touched in the same change; no commit trailers
   (this repo squash-merges, so a trailer gate would have to parse what lands on `dev`,
   recorded on card `7sv8`). Restating already-true facts in the README counts as that
   acknowledgement — the touch is the review, not whether the edit changed the wording.
4. The gate runs under `make ci`, which has repo history and needs no network.
5. Scope is skills and plugins only, since those are the two surfaces that own a README.

## Consequences

Card `9x2r` converts from a decision to a build task with these five points as its
acceptance criteria. The gate itself is future work, not part of this decision.

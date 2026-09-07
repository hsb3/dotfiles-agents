---
id: decision-017
title: Dual-homed primitives bump the owning bundle minor and the carrying bundle patch
date: '2026-08-22'
status: accepted
---
## Context

Raised by the owner 2026-08-13 while the external-handoff-signal change was in flight. That
change edited primitives shipped by both `atelier` and `solo-skills`, so
`scripts/check_version_bump.py` demanded a bump on both — and nothing anywhere said which digit
each should move. Ruled on kata card `w68p`; filed here 2026-09-07, having lived only in that
card's comment thread until then.

`check_version_bump.py` enforces only that a plugin's version MOVED when its dereferenced bytes
changed. It has no semver semantics at all — no major/minor/patch distinction anywhere in its
logic. The choice was pure convention, and the convention was undocumented, so it got re-derived
from scratch on every dual-homed edit and would drift between sessions.

This matters because the version is the only signal a consumer gets. A bundle that silently takes
a minor bump for a change that gave it no new capability trains people to ignore the number.

The open question was how to grade: by INTENT (why the change was made) or from the CONSUMER's
view of that specific bundle (what changed for whoever installs it, regardless of which plugin
the work was filed under). Intent is invisible to whoever installs the carrying bundle; only the
delta in what their bundle does is visible. A flat "any content change moves the patch digit
everywhere" was offered as the alternative.

## Decision

Owner ruling, 2026-08-22 (owner-signoff form, item B — "Adopt the proposed rule as written", no
notes and no amendments). The flat alternative was declined.

Grade from the consumer's view of that specific bundle, never from which plugin the work was
filed under:

- **Owning bundle → minor.** It gained the capability.
- **Carrying bundle → patch.** The shared primitive improved; the bundle itself does nothing new.
- **Both minor** when the shared change is genuinely new capability in both bundles.
- **Never "incidental" for a breaking change** to a shared primitive — a break is a break in
  every bundle that ships it.

**`check_version_bump.py` stays deliberately dumb.** Encoding "which digit" in a gate would
require the gate to infer capability, which it cannot see. This rule is convention enforced by
review, and that is deliberate. The gate's own docstring says so, so that its green is not read
as digit coverage: a gate with zero real subjects stays green forever, and a deliberate
forward-guard must state what it does not check.

`make members` is how a session finds which bundles a given primitive edit implicates — it prints
each plugin's members derived live from the symlink assemblies, rather than bumping on faith.

## Consequences

- The rule is stated in the `publish-to-main` skill, at the step that bumps the version, because
  that is where a session reads before bumping and where "the bump IS the release step" already
  lives. A rule recorded only in a decision file is a rule nobody reads at the moment it binds.
- Nothing mechanical enforces the digit. A misgraded bump is caught in review or not at all, and
  it becomes a public artifact at the next release — release notes are the first place these
  digits are visible outside this repo (`r9x6`, decision-013, ruled the same day).
- Revisit if dual-homing stops being the common shape, or if a gate ever gains a way to see
  capability rather than bytes.

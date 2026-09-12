---
id: "decision-013"
title: Release history cuts at publish time with no tracked CHANGELOG
date: '2026-08-22'
status: accepted
---
## Context

A review on 2026-08-22 asked whether this repo has a sufficient process for tracking primitives
and plugins being added, updated, or deleted. It did not, and the gap was in the RECORD, not the
ENFORCEMENT: `scripts/check_version_bump.py` already guarantees a plugin's version moved whenever
its dereferenced bytes changed, which is the hard part. Ruled on kata card `r9x6`; filed here
2026-09-07, having lived only in that card until then.

Measured that day: `gh release list` returned empty with auth verified, the only tag was a
cutover marker; no CHANGELOG existed anywhere outside a test fixture; `README.md`, `AGENTS.md`,
`docs/`, and `.github/CONTRIBUTING.md` had zero hits for `changelog|release notes|what's
new|version history|deprecat`; deletions were waived by design (`check_version_bump.py`: "a
removal has no version to bump") and primitives had already vanished with no record outside
`git log --diff-filter=D`. A partial ledger did exist and nobody would find it — every publish
commit on `main` carries the full plugin-and-version manifest in its body.

**Correction, same day as the ruling.** The Context above flagged its CLI claims as not verified
hands-on. They were then measured with the real CLI and two were wrong. The decision stands; its
supporting reasoning and the build plan changed.

| Claim | Reality |
|---|---|
| Claude Code never displays a version | **False.** `claude plugin list` prints a version per install with scope and enabled status; `claude plugin details <p>` opens with `<name> <version>`. |
| `homepage`/`repository` are the change-history hook a user can follow | **False in the direction that matters.** Plugins that set `repository` render it nowhere — `details` prints the description verbatim, then `Source: <plugin>@<marketplace>`. |

The description is the only free-text field that reaches a user, and it is effectively free — a
plugin with no skills and no agents reports `Always-on: ~0 tok`. Field recognition, probed
directly: `homepage`, `repository`, `license`, `keywords` are recognized; **`changelog` is not**,
so a dedicated changelog field is inert.

Two native capabilities were found while checking, neither then in use: `claude plugin tag
[path]`, which creates a `{name}--v{version}` git tag AND validates that `plugin.json` and the
enclosing marketplace entry agree on the version; and `claude plugin validate <path> --strict`,
documented for CI use and verified by exit code.

## Decision

Owner-signoff form, 2026-08-22, items C, D, E and F. Every recommendation accepted as written,
no notes, no amendments.

1. **Cut the history at publish time; no external release tool.** `publish.yml` tags the publish
   commit, creates a GitHub Release with notes from the PRs merged since the previous release
   plus the plugin-and-version manifest, and every plugin manifest and marketplace entry gains a
   link field pointing at that history. `release-please` wants to own version bumping (overlaps
   `check_version_bump.py`), expects a tracked CHANGELOG (collides with ADR 0017), and is a real
   dependency; `changesets` is built around a `package.json` this repo does not have, against a
   hardened npm; `semantic-release` assumes a single package. `git-cliff` was offered as a
   middle option and not taken.
2. **No CHANGELOG file is tracked.** The releases page is the only history — ADR 0017 stays
   intact rather than carved out, and there is one place to look instead of two that can
   disagree.
3. **A deletion is a gated, commit-declared event.** A check compares the published surface on
   `origin/main` against `dev` and fails when a plugin or rostered primitive present on `main` is
   absent on `dev` without a declaration in the commit message. No tombstone list: a hand-kept
   list of things that no longer exist is precisely the artifact that rots unread, and this
   repo's law is to derive a set rather than record one.
4. **Mechanics before doctrine.** Release cutting first, the deletion gate second (card `7sv8`),
   the packaged release-mechanics skill (card `m8b7`) parked until both have survived several
   real publishes.

Post-ruling build corrections, not decision changes: tag with `claude plugin tag --push` rather
than hand-rolled `git tag`; add `claude plugin validate --strict` to CI; put the release-history
URL in the plugin **description**, the only mechanism measured to reach a user. Decision points
2, 3 and 4 are untouched by any of it.

## Consequences

- The releases page is load-bearing. A silently skipped release step would stop the entire
  consumer-facing history with nothing going red — hence the fail-not-warn requirement, which the
  shipped step honours.
- Version digits mean something specific per the semver rule ruled the same day
  (`w68p`, decision-017). Release notes are the first place those digits are visible outside this
  repo, so a misgraded bump becomes a public artifact.
- Declaring a removal in a commit message means the declaration is only as durable as the commit
  history, and squash-merging rewrites bodies — the gate's parser has to read what lands on
  `dev`, not what was written on the branch.
- No tracked CHANGELOG means someone browsing the source tree still sees no history. Accepted:
  the tree is for contributors, and contributors have git.

Implementation status, checked 2026-09-06 on `r9x6`: release cutting landed with both post-ruling
corrections — `publish.yml` tags each changed plugin with `claude plugin tag --push` and then cuts
one dated marketplace release, and its own comment records why per-plugin Releases were rejected
(GitHub's generated notes diff against the previous release regardless of which plugin it
belonged to, so per-plugin releases would each claim every commit). `claude plugin validate
--strict` is wired into CI via `scripts/check_manifests.py`. The deletion gate of point 3 has NOT
landed — that is `7sv8`, still open, and `check_version_bump.py` still disclaims removals.
`m8b7` correctly remains parked, per this ruling's own sequencing.

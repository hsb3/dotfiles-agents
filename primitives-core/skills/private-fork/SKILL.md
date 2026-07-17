---
name: private-fork
description: >-
  Stand up and operate a private fork (private mirror) of an upstream open-source repo —
  creating the mirror and remotes, choosing the branch model and governance tier, deciding
  delete-vs-disable for unwanted upstream content, recording divergences in a ledger or
  registry, and running the recurring upstream review/merge cycle. Use when the user wants
  to "set up a private fork", "mirror an upstream repo", "sync/merge upstream", "run an
  upstream review", "strip out upstream cruft", asks about delete-vs-disable or merge tax,
  or is working in a repo with an `upstream` remote and a FORK_CHANGES.md /
  fork-customizations.md file. Not for ordinary contribute-back GitHub forks where changes
  are destined for upstream PRs.
---

# Private Fork — setup and operation

Doctrine for maintaining a **private, deliberately-divergent fork** of an actively
developed upstream OSS project: keep the ability to pull upstream forever, keep your
divergence small and fully recorded, and keep every merge routine.

The enemy is **merge tax** — every divergence makes every future upstream merge more
expensive. Almost every rule below exists to minimize it or to make paying it deliberate.

## Reference files

| File | Read when |
|---|---|
| `references/setup.md` | Creating a new private fork, or retrofitting governance onto an existing one |
| `references/divergence-rubric.md` | Deciding what to delete/disable/hide, making any deliberate change to upstream code, neutralizing telemetry/phone-home |
| `references/upstream-sync.md` | Reviewing upstream changes, merging upstream in, resolving conflicts, the post-merge checklist |

Templates to copy into the fork are in `assets/templates/` (divergence ledger, full-tier
registry, review log, digest script, CI reminder workflow). Fill placeholders marked
`{{LIKE_THIS}}`.

## Invariants (every fork, every tier)

1. **Private mirror, not a GitHub fork.** GitHub forks of public repos can't be private.
   Create an empty private repo, push the full upstream history to it as `origin`, keep
   `upstream` as a fetch-only remote.
2. **Block accidental upstream pushes, day one:**
   `git remote set-url --push upstream DISABLED`.
3. **Merge upstream in; never rebase the published trunk.** Merges preserve the
   divergence record and never force-push.
4. **Every deliberate divergence is recorded** — in the ledger/registry, **in the same
   commit** that creates it. A file that differs from upstream and isn't recorded is a
   bug: either re-align it or add the row.
5. **Divergence commits are greppably marked** (`fork:` prefix, or the repo's existing
   `feat|fix|harden(scope):` scheme applied consistently) so
   `git log --grep='^fork:'` (or equivalent) inventories the divergence.
6. **Never hand-merge lockfiles or generated files.** Take upstream's wholesale, re-run
   the generator (`pnpm install`, `bun install`, codegen, …).
7. **A verify gate is defined per-project and a sync isn't done until it passes** — the
   fork's own build + smoke test, run by you, not asserted from green-looking diffs.
8. **Secrets never enter the fork.** `.env*` gitignored; only `.env.example` tracked.
9. **The delete-vs-disable rubric governs every removal** (see
   `references/divergence-rubric.md`). Rule of thumb: if upstream committed to that path
   in the last few months, disable it, don't delete it.
10. **Know your build reality.** If the running stack uses upstream's prebuilt images,
    fork source changes do nothing at runtime — and a `latest` image tag drifts
    independently of the checkout. Pin the tag to a release matching your merge-base, or
    build from source. Mixed mode is the confusing failure mode.

## Two governance tiers

Start light. Upgrade when the fork earns it.

| | **Light tier** | **Full tier** |
|---|---|---|
| Fits | Personal instance, few/no code modifications, deletions + config flags only | Many modifications in upstream-churned files, invariants to protect, agents/CI operating the fork |
| Branches | Single trunk `main`; optional short-lived `fork/<topic>` | Trunk + read-only `upstream-<branch>` mirror + throwaway `uat` staging per merge |
| Divergence record | `FORK_CHANGES.md` — one line per divergence: what, why, delete-vs-disable | `docs/fork-customizations.md` — registry with IDs (R-nn removals / M-nn modifications / A-nn additions) and a **Merge rule** column per row |
| Upstream review | On demand — before new fork work or when upstream ships something wanted | Fixed cadence (e.g. monthly or per release) + review ledger with verdicts and a watermark; optionally CI-automated reminder |
| Merge path | Merge `upstream/main` directly into trunk | `upstream/<branch>` → `uat` → trunk, promoted only after the post-merge checklist |
| Extra docs | — | Charter (goals/non-goals/governance map), merge SOP, ADRs |

**Upgrade triggers** (any one is enough): modifications (not just deletions) exceed a
handful of files upstream actively churns · an upstream sync broke the running app and a
staging gate would have caught it · review is backing up because "on demand" never
happens · more than one person or unattended agent operates the fork.

The tier decision and the branch model are recorded as the fork's first divergence entry.

## Lifecycle

1. **Setup** (once) — `references/setup.md`: mirror, remotes, push-block, branch model,
   governance scaffold from templates, build-mode decision.
2. **Divergence work** (ongoing) — `references/divergence-rubric.md`: every removal or
   modification goes through the rubric and lands with its ledger/registry row.
3. **Upstream sync** (recurring) — `references/upstream-sync.md`: review with verdicts,
   merge, resolve conflicts against the recorded merge rules, run the post-merge
   checklist and verify gate, record the outcome.

## Anti-patterns

- Deleting content because it *looks* unused — verify the import graph first (locale
  dirs, "marketing" assets, and vendored trees are often statically imported).
- Ripping out telemetry/analytics code that is already env-gated — leave the keys empty
  and record it; deletion of a churned tree is all tax, no benefit.
- Cherry-picking as the primary sync mechanism — fine sparingly (`git cherry-pick -x`),
  but picks resurface as duplicates in the next full merge.
- A "pristine mirror" long-lived local branch on the light tier — `upstream/<branch>`
  already is the pristine mirror; ceremony with no benefit. (The full tier's
  `upstream-<branch>` mirror earns its keep as the digest/diff baseline.)
- Doing feature work in the fork that isn't fork-specific — it belongs upstream.

# Setup — creating (or retrofitting) a private fork

One-time procedure. Works for a brand-new fork or for adding governance to an existing
clone that already has an `upstream` remote.

## 1. Create the private mirror

GitHub forks of public repos can't be made private, so mirror instead:

```bash
# Empty private repo first (no README/license — history comes from upstream)
gh repo create <you>/<name> --private

git clone https://github.com/<upstream-org>/<name>
cd <name>
git remote rename origin upstream
git remote add origin git@github.com:<you>/<name>.git
git push origin --all && git push origin --tags
```

Retrofit case (clone already exists): just confirm `git remote -v` shows `origin` =
private repo, `upstream` = the real project.

## 2. Harden the remotes

```bash
git remote set-url --push upstream DISABLED   # `git push upstream` now fails loudly
```

Optional belt-and-suspenders for agent-operated repos: a deny-list entry for
`git push upstream*` in `.claude/settings.json` permissions.

## 3. Choose the branch model (record the choice)

**Light tier** — single trunk:

| Branch | Role | Rule |
|---|---|---|
| `upstream/<branch>` | Pristine upstream reference | Fetch only; never push |
| `main` (origin) | Personal trunk = upstream + your changes | All fork work lands here; deploy from here |
| `fork/<topic>` | Optional short-lived features | Merge to `main`, delete |

**Full tier** — staged merges:

| Branch | Tracks | Purpose |
|---|---|---|
| trunk (match upstream's default branch name) | `origin/<trunk>` | The fork — active work |
| `upstream-<branch>` | `upstream/<branch>` | Read-only local mirror; advanced `--ff-only` after each merge; baseline for digests and post-merge diffs |
| `uat` | *(temporary)* | Merge staging, created fresh per merge, deleted after promotion |

Full-tier rule: **never merge upstream directly to trunk** — always
`upstream/<branch>` → `uat` → trunk.

Keeping the trunk name identical to upstream's default branch avoids a permanent
mental translation in every command and doc.

## 4. Scaffold the governance docs

Copy from `assets/templates/` and fill `{{PLACEHOLDERS}}`:

| Tier | Copy | To |
|---|---|---|
| Light | `FORK_CHANGES.md` | repo root |
| Full | `fork-customizations.md`, `upstream-review-log.md` | `docs/` |
| Full | `upstream-digest.sh` | `scripts/` (then edit the config block: refs, repo, skip/flag regexes) |
| Full (optional) | `upstream-check.yml` | `.github/workflows/` — monthly self-announcing review reminder; needs only the default `GITHUB_TOKEN` |

Full tier also gets: a charter section (goals / non-goals / governance table — where the
SOP, registry, ledger, and ADRs live) in the repo's canonical page or `docs/CHARTER.md`,
a `make upstream-review` target wrapping the digest script, and per-repo CLAUDE.md
pointers so agents find the SOP before touching a merge.

The first commit on the fork is the governance scaffold itself, and the ledger's first
entry records the SOP adoption + branch model + tier decision.

## 5. Decide the build/run mode (the reality check)

If the project ships prebuilt images/binaries and you run those, the fork is a **source
reference only** until you switch to source builds. Decide explicitly, record it in the
ledger:

- **Prebuilt images:** pin the tag to a release matching your merge-base. Never track
  `latest` — it drifts independently of the checkout, and "upstream image + fork
  expectations" is the confusing failure mode.
- **Source builds:** wire the compose/Make target that builds from the fork checkout,
  and make it part of the verify gate.

Switch to source builds when the first code change you actually want live lands; a
deploy-relevant surface (desktop app, mobile app) that needs its own signing/packaging
is a separate decision, not a default.

## 6. Define the verify gate

Write down (in the SOP or ledger) the minimal end-to-end proof the fork must pass after
any sync or divergence commit — build completes, stack starts, one real request round-trips,
plus any fork-specific assertions (e.g. "backend catch-all returns 404", "no telemetry
beacon in built assets"). If upstream's own e2e suite was removed or doesn't run in the
fork, this gate is the *only* end-to-end coverage — treat it accordingly.

If the fork's data store has one-way migrations, the gate runs against **throwaway
state** (separate compose project name / temp volumes), and live volumes are only
touched at promotion, after a backup.

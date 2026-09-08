# Upstream sync — review, merge, verify, record

## Step 0 — Review (full tier: reviewing is mandatory, merging is optional)

**Light tier:** on demand — before starting new fork work, or when upstream ships
something wanted. Skim `git log --oneline main..refs/remotes/upstream/main` and
`git diff --stat main...refs/remotes/upstream/main`; no ledger of verdicts required.

**Full tier:** fixed cadence (monthly, or when upstream tags a wanted release —
whichever comes first). Run the digest script (`make upstream-review`), which covers
everything from the review log's `Last-reviewed-upstream-commit:` watermark to upstream
HEAD, pre-triaged as SKIP / FLAG / REVIEW. Record a verdict per commit (or per release,
in summary mode):

| Verdict | Meaning |
|---|---|
| **adopt** | Take it — lands via the next merge (or a cherry-pick) |
| **adapt** | Take it, modified to fit the fork — note how |
| **pass** | Not applicable (upstream cloud/CI/platforms out of scope) — one clause why |
| **defer** | Undecided — goes in the log's *Open deferrals*, revisited next cycle |

Append the finished block to the review log and advance the watermark. **The watermark
only advances when every commit in range has a verdict.** Reviewing is not merging — a
session may verdict everything and merge nothing; if nothing warrants adoption, stop.

## Merge

Upstream refs are spelled in full (`refs/remotes/upstream/<branch>`) because
`refs/heads/<name>` resolves first: a local branch named `upstream/main` would
otherwise merge, and advance the mirror to, the wrong commits.

Light tier:

```bash
git fetch upstream
git merge refs/remotes/upstream/main   # merge, NOT rebase — trunk is published
# resolve conflicts (below), run verify gate, then:
git push origin main
```

Full tier:

```bash
git fetch upstream
git checkout <trunk> && git checkout -b uat
git merge refs/remotes/upstream/<branch>   # or cherry-pick the adopted subset
# resolve conflicts, run the FULL post-merge checklist, then promote:
git checkout <trunk> && git merge uat && git push origin <trunk>
git branch -d uat
git checkout upstream-<branch> && git merge --ff-only refs/remotes/upstream/<branch> && git checkout <trunk>
```

Merge-commit message records what was merged: `merge upstream v1.2.15 (eb64ce0..b4d0090)`.

Selective mirroring: `git cherry-pick -x <sha>` (the `-x` records the upstream sha).
Use sparingly — picks resurface as silent duplicates in the next full merge.

## Conflict policy

Resolve every conflict against the ledger/registry's merge rules. A conflict in a file
with **no** recorded row means either the divergence is accidental (take upstream) or
it's new and undocumented (add the row in the same commit). Defaults by shape:

| Conflict shape | Default resolution |
|---|---|
| Upstream modified a file we **deleted** (`deleted by us`) | Keep the deletion (`git rm`) — unless the change indicates the file became load-bearing; then restore and re-evaluate |
| Upstream modified a file we **disabled/flagged** | Take upstream's version, re-apply the disable flag |
| Upstream modified code we **customized** | Read the upstream change first; re-apply *our intent* (per the ledger row) on top of their version — not their change on top of ours |
| Lockfiles / generated files | Take upstream's wholesale, re-run the generator. Never hand-merge |

## Post-merge checklist (full tier; light tier runs the subset that applies)

1. **Resurrected files** — grep/ls for everything the removals rows cover. Search **by
   directory and pattern, not fixed filenames** — upstream regrows removed features
   under new names (a 2-file removal can come back as 4 files).
2. **Phone-home probe** — re-run the ledger's telemetry greps on source *and built
   artifacts*; judge new hits against the phone-home policy (live → remove; inert →
   allowlist row).
3. **New config surface** — new API routes needing proxy/nginx entries; new env
   vars/flags needing `.env.example` entries; new build steps.
4. **Build** — the fork's real build (Docker/compose/binary) completes clean.
5. **Verify gate** — the fork's end-to-end smoke test, against throwaway state if
   migrations are one-way (live volumes only at promotion, after a backup).

## Record the outcome (same session as the merge)

1. Review log: session block appended, watermark advanced (full tier).
2. Ledger/registry: new divergences added, retired ones removed.
3. SOP/digest filters: any newly conflict-prone file added to the FLAG patterns —
   keep the SOP's filter list and the digest script's regexes in sync.
4. Handoff/session notes updated if the project keeps them.

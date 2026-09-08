# Fork Changes — {{YOU}}/{{NAME}}

_The divergence ledger (light tier): one entry per deliberate difference from
`{{UPSTREAM_ORG}}/{{NAME}}`. If a file differs from upstream and isn't listed here,
that's a bug — re-align it or add the row. This file is the conflict-resolution cheat
sheet during upstream merges: when upstream touches something we changed, the entry
says what our intent was._

Status: active

## Ground rules

- Branch model: single trunk `main` (= upstream + our changes); `upstream/main` is the
  pristine reference, fetch-only, push-blocked (`push upstream` → DISABLED).
- Sync: `git merge refs/remotes/upstream/main` on demand — the full refname, because a
  local branch named `upstream/main` would resolve first and merge the wrong commits.
  Never rebase `main`. Lockfiles: take upstream's, re-run the generator.
- Every divergence commit is prefixed `fork:` and updates this ledger in the same commit.
- Verify gate after every sync or fork change: {{VERIFY_GATE — e.g. "make restart && make health; manual poke at http://localhost:PORT"}}

## Divergences

| Date | What | Why | Move (delete/disable/hide/modify) + merge rule |
|---|---|---|---|
| {{DATE}} | Adopted this SOP: push-block on upstream, `fork:` prefix, this ledger | Governance baseline | — |
| {{DATE}} | Build mode: {{prebuilt images pinned to TAG / source builds via ...}} | {{why}} | Revisit when the first live-wanted code change lands |

## Kept deliberately (rejections that must stay rejected)

| What | Why it stays |
|---|---|
| {{e.g. locale dirs}} | {{e.g. statically imported by a hot index file — delete breaks build + recurring conflicts}} |

## Phone-home allowlist (inert surfaces verified {{DATE}})

- {{e.g. `$schema` URL strings in config JSON — never fetched}}

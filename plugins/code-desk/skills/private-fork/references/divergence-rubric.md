# Divergence rubric — delete vs disable vs hide vs leave

Every removal makes future merges more expensive. Decide by **upstream churn**, not by
how useless the content looks. The one-line test: *if upstream's `git log` shows commits
to that path in the last few months, disable it; don't delete it.*

## The four moves

| Move | Use for | Cost profile |
|---|---|---|
| **Delete** | Leaf content upstream rarely touches AND nothing imports: non-English READMEs, community/issue templates, CONTRIBUTING, marketing assets, upstream CI that can't run in the fork (needs upstream secrets, publishes to upstream infra) | Cheap to keep deleted; re-delete if a merge resurrects it |
| **Disable / flag** | Anything wired into builds or actively churned: analytics (leave env keys empty; set the explicit `*_DISABLED` var too if one exists), CI workflows worth keeping in modified form (neuter the trigger, keep the file), i18n (config-default to your language rather than ripping the framework out), feature integrations (env vars unset) | Near-zero merge tax; the "off" state must be pinned in config and recorded so a future cleanup pass doesn't "fix" it |
| **Hide (`git sparse-checkout`)** | Bulk content unwanted locally but actively developed upstream and already excluded from your builds (a mobile app, a docs site). Files stay tracked → merges stay clean; the noise leaves searches and editors | Zero merge tax, but **per-clone state**: fresh clones and agent worktrees won't inherit it — record that caveat in the ledger |
| **Leave** | Load-bearing paths even if unused-looking (compose files, self-host scripts, server config plumbing), hot server trees, anything statically imported | Zero |

## Before any delete: verify the import graph

"Obviously safe" content is routinely load-bearing. Check before deleting:

```bash
rg -l '<dirname>|<module-name>' --type ts --type go ...   # who imports it?
```

Real examples that overturned a delete decision: locale directories statically imported
by an index file upstream refreshes on every translation pass (delete = broken build +
recurring conflicts on a hot file); an integrations tree imported from the router;
upstream's `ci.yml` that needs no secrets and gives free test coverage on every push.

When you *keep* something a future session would plausibly try to remove, record the
keep decision with its reason in the ledger — rejections must stay rejected.

## Modifications (changing upstream code you keep)

- Smallest possible patch. Prefer a one-file redirect/stub/env-gate over deleting forty
  actively-maintained files.
- Each modification gets a ledger/registry row **with a merge rule**: what to do when
  upstream touches that file ("keep our stub", "take theirs, re-apply the flag",
  "re-strip the URLs"). The merge rule is written when the change is made — that's when
  intent is clearest.
- Where feasible, pin the modification with a test that asserts the *fork's* behavior
  (404 instead of proxy, no referer header, no upsell URL). Tests are the merge rule
  that enforces itself.

## Phone-home / telemetry neutralization

For forks whose point is self-hosting or privacy, classify every outbound surface:

| Class | Policy |
|---|---|
| Live calls at runtime (telemetry SDKs, changelog fetches, remote assets, error reporting) | Remove or neutralize; prove absent in **built artifacts**, not just source |
| User-initiated only (doc links, explicit login to upstream's cloud, self-update on request) | Allow; gate with an env flag where one exists |
| Inert strings (schema URLs, doc-comments, display strings) | Allowlist in the ledger so the next audit doesn't re-litigate them |

Grep discipline: case-insensitive (`referer` vs `Referer`), and remember an
escaped-dot regex literal in source (`/example\.com/`) silently defeats a
`grep 'example\.com'` probe — grep with fixed strings or loosened patterns. Re-run the
probe every merge (it belongs in the post-merge checklist).

## Commit & ledger discipline

- One divergence (or one coherent batch) per commit, marked greppably (`fork:` prefix or
  the repo's typed-prefix scheme).
- The ledger/registry row lands **in the same commit** as the divergence.
- Never commit secrets; local config in gitignored `.env*`.

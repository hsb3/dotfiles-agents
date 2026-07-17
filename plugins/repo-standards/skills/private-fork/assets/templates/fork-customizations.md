# Fork Customizations Registry

_The authoritative list of every deliberate divergence from
`{{UPSTREAM_ORG}}/{{NAME}}`. If a file differs from upstream and isn't listed here,
that's a bug — either re-align the file or add the row._

Status: active

**Maintenance rule:** any commit that introduces or removes a deliberate divergence
updates this registry in the same commit. The merge SOP uses the **Merge rule** column
when resolving conflicts.

## Removals

| ID | What | Why | Merge rule |
|---|---|---|---|
| R-01 | {{packages/dirs/files removed}} | {{why}} | Re-delete whatever a merge resurrects — grep by directory/pattern, not fixed filenames (removed features regrow under new names) |

## Modifications

| ID | File(s) | Change | Why | Merge rule |
|---|---|---|---|---|
| M-01 | {{path}} | {{what changed}} | {{why}} | {{e.g. "always keep our stub" / "take upstream, re-apply the flag" / "re-strip the URLs"}} |

## Additions

| ID | What | Why |
|---|---|---|
| A-01 | {{e.g. Dockerfile, compose files, .env.example}} | {{why}} |
| A-02 | `docs/` governance set (this registry, merge SOP, review log), `scripts/upstream-digest.sh` | Fork governance |

## Phone-home policy

Live network calls to {{UPSTREAM_DOMAINS}} / telemetry hosts are removed or must be
strictly user-initiated. Allowed-but-inert surface (verified {{DATE}}; re-verify each
merge with the post-merge grep):

- {{inert item + why it's safe}}

**Probe (run on built artifacts, not just source):**

```bash
{{e.g. grep -ri "UPSTREAM_DOMAIN" dist/ ; grep -r "__SENTRY__" dist/}}
```

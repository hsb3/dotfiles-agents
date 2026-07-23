# Default rubric — self-hostable / open-source infrastructure evaluations

Use this when the evaluation involves self-hosting, open-source tooling, or free-tier boundaries. Adapt the specifics; keep the structure (hard filters → capability checklist → maturity bar). For evaluations where none of this applies (e.g., pure SaaS comparisons), reuse the *shape*: define eliminating filters, a per-feature verdict vocabulary, and an evidence-based health assessment.

## 1. Portability — the hard filter

A candidate is portable only if **all** of these hold:

1. Runs on infrastructure the user controls (self-hosted Docker/K8s/VM), not SaaS-only. Check whether self-hosting is *first-class* (docs, images, Helm charts) or grudging (dev-only, "contact sales" for production).
2. **OSI-approved license** (Apache-2.0, MIT, BSD, MPL, AGPL, PostgreSQL, etc.). Read the actual LICENSE file(s), per component — server vs SDKs vs dashboard vs `ee/` directories. A repo can be tri-licensed.
3. **No mandatory license key** to unlock core features.
4. **No vendor callback** required for licensing or usage reporting — air-gap-capable. Distinguish: no telemetry at all / opt-out telemetry (conditional pass, note the env var or toggle) / mandatory phone-home (fail).
5. **No usage restrictions** on deployment or commercialization (no user caps, no no-resale clauses on the artifact actually being used — watch for convenience Docker images that bundle proprietary code under extra terms even when the source is clean).

**The source-available trap — flag, don't silently fail.** BSL, SSPL, Elastic License 2.0, Commons Clause, "fair-code": these fail criteria 2 and 5, but mark the candidate **SOURCE-AVAILABLE (fails portability)** and state which license and what it restricts (often: offering the software as a service). Some grants explicitly permit self-hosting your own workloads — say so; the user may re-screen later with a softer policy.

**Verification tricks that work:**
- Search the codebase/docs for: "license key", "LICENSE_KEY", "telemetry", "phone home", "beacon", "usage reporting", "DO_NOT_TRACK", "update check".
- Check PyPI/npm metadata for the license classifier — a package claiming a license with no public source repo is an unverifiable claim, not open source.
- If a vendor claims "open source" but the org's public repos contain only examples/helm-charts/SDK stubs, the engine is closed. Say so.

## 2. Capability checklist pattern

Resolve each required capability to exactly one verdict, with a one-line note and a source URL:

| Verdict | Meaning |
|---|---|
| **Yes (free/OSS)** | Works in the free, self-hosted deployment; confirmed from docs/code |
| **Paywalled** | Exists, but gated to a paid tier or the vendor's cloud |
| **No** | Confirmed absent — docs state the limitation or the design excludes it |
| **Not documented** | Could not confirm either way; never assert absence from silence |

Partial fits get "Partial/◐" with the boundary stated (e.g., "OAuth login free up to 10 users; SAML paid").

Example checklist (from an agent-serving-layer evaluation — replace with the capabilities the decision needs, but keep the "what counts" column, which is where evaluations are won or lost):

| Capability | What counts (not just the name) |
|---|---|
| Auth | Pluggable third-party auth (JWT/OAuth2/OIDC) **and** resource-level access control. Auth only via vendor cloud = Paywalled |
| Streaming | Incremental output **with reconnection/resume** (event replay after drop), not a one-shot stream |
| Cron | Recurring schedules; timezone support; multi-instance safe (no duplicate fires when scaled) |
| Background | Async/deferred execution via a real queue; fire-and-forget long jobs |
| Persistence | Durable state, **bring-your-own datastore** (user owns DB + credentials) |
| Durability | Crash recovery, resumable/replayable runs, retry semantics, delivery guarantees (at-least-once vs exactly-once) |

## 3. Maturity bar (operationalized)

Judge from public signals over the **trailing 6 months**, each checkable in minutes on GitHub. Record the date checked and the numbers, so the verdict is reproducible.

### 3.1 Contributor breadth — bus factor
- Preference: ≥3 distinct people contributing merged code in the window.
- Weight **recurring contributors** (multiple PRs across multiple months) over drive-by authors; flag if one account authors/merges ~everything (bus factor ≈1 even with more names in the graph).
- Hard floor: ≥2 recurring contributors, **or** 1 plus real institutional backing (funded company or foundation).
- Failing the preference **down-ranks**; failing the floor disqualifies on maturity. Say which happened.

### 3.2 Sustained activity
- Merged PRs/commits in every month of the window (flag dead months).
- Issues being closed, not just opened.
- Tagged releases in the window — evidence they ship.

### 3.3 The "is it dying" test
- Last ~2 months vs prior ~4: a >~60% volume drop with no stated reason is a red flag.
- Backlog trend: open issues/PRs stable or shrinking, not growing unbounded.
- Recency floor: last commit within a few weeks; last release within ~3 months.
- Watch for regime changes: acquisitions, rewrites, deprecation notices, repo moves, "successor project" pointers — these override raw activity numbers.

### 3.4 Production evidence
- Named adopters, case studies, "in production" reports.
- Package download volume (PyPI/npm) as a use proxy — note when a number is structurally inflated (e.g., a client library imported by every job the platform runs).
- Governance surface: CONTRIBUTING, security policy, changelog, issue templates.

### 3.5 Verdict
**Strong / Adequate / Early / At-risk**, always with which of 3.1–3.4 passed or failed. Never a bare adjective.

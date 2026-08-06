---
title: "_meta/ is tracked by default; targeted ignores only"
type: decision
status: Superseded-by-decision-8 (2026-08-06 — _meta/ removed entirely; secrets home is .claude/operations/)
created: 2026-07-13
summary: Replace the _meta/ broad-ignore + negation gitignore policy with track-by-default; only operations/ content, caches, and OS litter stay ignored.
---

# 0006 · `_meta/` is tracked by default; targeted ignores only

_The working desk tracks like the rest of the repo; ignoring is the exception, reserved
for secrets (`operations/`), tool caches, and OS litter._

- **Provenance:** owner directive 2026-07-12 (#99); owner ruled option 2 on 2026-07-13
  (comment on #99). Decision 2 (relocating `operations/`) left to default: it stays inside.
- **Raised by:** #99 · `_meta/plans/meta-gitignore-policy/plan.md`

## Context

The prior policy ignored `_meta/*` and re-included tracked items via negation. The stanza
grew to 27 lines with paired `!dir/` + `!dir/**` lines per subtree, four duplicated
`.DS_Store` guards (each negation re-admits litter past the global rules), a hard ordering
dependency on the Python cache section, and the `_meta/*`-vs-`_meta/` form trap; 18
compliance rows (IGNORE-01..18) existed largely to police that fragility. Meanwhile
load-bearing content was silently local: `_meta/research/` was gitkeep-only (the 2026-07-12
ecosystem survey couldn't be linked from the owner's decision brief), `_meta/NOTE.md` held
the idea list that spawned #48/#49, and tracked-by-negation subtrees still needed manual
`git add` discipline (the governance brief sat untracked). Three options were compared in
the plan: (1) status quo, (2) track-by-default with targeted ignores, (3) option 2 plus
moving the secrets dir out of `_meta/` entirely.

## Decision

**Option 2 — track `_meta/` by default; ignore only what must never publish:**

- `_meta/operations/*` (secrets/live-ops; `.gitkeep` negated so the dir survives a clone)
- tool caches and OS litter — covered by the global `__pycache__/`, `*.pyc`, and
  `.DS_Store` rules, which apply again now that no negation re-includes them

**`operations/` stays inside `_meta/`, ignored** (decision 2 default; option 3 rejected —
it breaks the `_meta/` taxonomy everywhere it is documented for marginal gain).

**Secret-safety argument:** secrets have exactly one sanctioned home, `_meta/operations/`,
and that path stays ignored under this policy — the rule shifts from "everything is unsafe
until negated" to "one path is unsafe and stays ignored", concentrating discipline where
the audit can actually check it. `.env*` rules are unchanged. The one-time flip is guarded
by a secrets scan of everything newly tracked before it lands.

**Migration ruling (this repo):** every previously-ignored non-secret `_meta/` artifact is
committed, none ruled local — `NOTE.md`, `research/extender-distribution-ecosystem.md`,
`research/2026-07-05-vault-governance-routing-manifest.md`, and the
`briefings/2026-07-12-extender-governance-brief/` package. Desk content is
clone-survivable by default from here on; deliberately-local scratch belongs in
`_meta/operations/` or outside the repo.

## Consequences

- The repo stanza shrinks from 27 lines to 2; the negation machinery, ordering
  dependencies, and duplicated litter guards are deleted.
- The IGNORE checklist rows are rewritten to test this policy (track-by-default probes +
  the operations/cache/litter ignores); rows testing negation mechanics are retired.
- `git status` gets noisier: desk scratch shows as untracked until committed. That is the
  accepted trade — visible-until-decided beats invisible-by-default.
- Adopters (workbench, fleet-dashboard, the dotfiles `project-protocol.md` §2 stanza)
  migrate via the apply note; each flip repeats the pre-flip secrets scan.

## Affects

`.gitignore` · `_meta/README.md` · repo-meta-structure (`assets/gitignore.template`,
`references/checklist.md` IGNORE rows, `references/layout.md`, SKILL description) ·
mise-en-place-scaffold (`scripts/scaffold.py` stubs + `references/manifest.md`) ·
planning-desk SKILL setup step 2 · generated `targets/` via `make build` · adopter repos.

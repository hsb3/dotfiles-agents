# Contributing

*The process for developing and shipping a coding-agent extender in this marketplace.
Status: active. Graduated from the executive desk's extender-development SOP per decision
0016.*

This repo is a Claude Code marketplace: a curated set of coding-agent extenders — skills,
agent personas, hooks, MCP connection specs — assembled from `primitives-core/` into plugin
bundles. Contributing here means adding, changing, or retiring one of those.

## 1. Decide it's worth building

Apply the standing litmus before writing anything (Charter G1–G6): **does this reduce future
tooling time?** Capability-adds wait behind a named, real use-case pull — no speculative
extenders built ahead of need. If it clears the litmus and has a use-case pull, add an entry
to the candidate ledger (tracked on the executive desk) so the in-flight work is visible.
There is no separate incubation/workbench repo to develop against; the single control point
is the entry gate on the PR into `dev` (below).

## 2. Develop it — anywhere

A scratch dir, a feature branch, wherever is convenient. While building, hold the extender to
the standard the entry gate enforces, so entry is a formality rather than rework:

- **Edit primitives under `primitives-core/` only.** `plugins/<id>/` are thin symlink
  assemblies over it (ADR 0017): hand-authored `plugin.json`/`hooks.json`/bundle READMEs,
  symlinks for everything else, listed in the root `.claude-plugin/marketplace.json`. There
  is no build step — an edit at source is live everywhere the primitive ships; `make
  symlinks` lints the assemblies.
- **Every distributed plugin ships a README.** A standalone skill's README travels with the
  skill (`primitives-core/skills/<id>/README.md`, symlinked to its plugin root); a
  bundle/kit's README is hand-authored at `plugins/<id>/README.md`. `make ci` fails if a
  distributed plugin has no README.
- **`primitives-core.yaml` is the provenance manifest of record.** A primitive isn't real
  until it has a roster entry — see [`primitives-core/README.md`](../primitives-core/README.md)
  for the entry schema (`id · type · source · origin · disposition · targets · requires`).
  Plugin membership is the symlink assemblies, not a roster field.
- **Identity-neutral / project-agnostic.** No name, org, repo, or issue hardcoded into any
  shipped artifact. Personalization comes from **data surfaces** a generic extender reads
  (a profile / freeform background), never from a baked-in prompt. This is the single most
  common reason a candidate fails review.
- **Provenance recorded.** A primitive is `authored` (self-authored, including agent-generated
  work done under direction — usage decides its place, not who typed it), or third-party.
  Third-party ships **by reference** in `externals.yaml` (upstream URL + pinned ref, cloned at
  build time) — never vendored into `primitives-core/`, except a deliberately maintained fork
  with a recorded divergence rationale.
- **Composed, not passed through.** Never ship a third party's bundle wholesale — a bundle
  composes a mix of third-party + authored primitives.
- **Hooks use the ratified hook-dir layout** — `hooks/<name>/hook.py` (config + script per
  hook; never inline bash in `settings.json` — ADR
  [0002](decisions/0002-hooks-as-script-plus-config.md)).
- **Tests exercise the extender's real behavior**, not just its shape.
- Nothing generated is tracked (ADR 0017) — anything that must be generated (e.g. the
  opencode laydown) is produced at install/run time by a deterministic generator.

## 3. Enter distribution

`dev` is the integration branch; `main` is publish-only (ADR
[0007](decisions/0007-distribution-restructure-dev-main.md)):

- Branch off `dev`, open your PR **into `dev`** — never `main`. It's the CI-published
  marketplace surface, advanced only by the sanctioned `dev` → `main` promotion, never a
  direct commit.
- Keep changes surgical and scoped to one slice; match the repo's existing style.
- `make ci` is the task interface (`make help` lists every target): the entry-gate floor
  (identity · tests · provenance · hook-layout) + `check` (roster ↔ disk, provenance
  manifest) + `symlinks` (assembly lint) + `flow`. A PR that doesn't pass `make ci` locally
  won't pass it in CI either — run it before you push.

The PR then clears the **entry gate** — two tiers, captured here as the working contract
until it graduates into its own enforced CI lane:

**Tier 1 — machine floor** (required CI on every PR; a red floor is not mergeable):

1. **Identity-neutrality lint** — the check for the rule above.
2. **Tests pass.**
3. **Provenance / externals conformance** — no third-party copies in `primitives-core`; every
   `externals.yaml` entry carries non-null recorded intent (upstream + ref) or is dropped with
   a note.
4. **Hook-layout** — hooks use the hook-dir layout described above.

**Tier 2 — judgment review** (a reviewer attests on the PR; no separate promotion step):

- **Belongs** — fits the current bundle lineup, not a speculative addition.
- **Quality** — the primitive does what its description claims.
- **Non-duplicative** — doesn't re-implement what another shipped primitive already covers.
- **Use-case pull** — motivated by a real, named use.

Passing both tiers *is* graduation — there's no separate promotion ceremony.

## 4. After merge

If the extender had a candidate-ledger entry, update it to graduated/shipped. A candidate
that never earns its use-case pull gets closed as dropped instead — the candidate ledger is
a baton, not a permanent backlog.

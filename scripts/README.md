# scripts

The toolchain node of the repo flow (`flow.yaml: toolchain`): every gate checker `make ci`
runs, the install-time opencode lane, and the weekly harness-campaign runner. Checkers are
stdlib-only and deterministic — zero install is an invariant. Each prints a `✓`/`✗` summary
and exits 0/1; `make help` lists the wrapping targets. Run them via make from the repo root.

## Gate checkers (all in `make ci`)

| Script | Make target | Proves |
|---|---|---|
| `check_identity.py` | `identity` | no name/org/repo/issue hardcoded in any shipped body; frontmatter shape, secret and portability hygiene |
| `check_provenance.py` | `provenance` | `primitives-core/` is self-authored (ADR 0015); `origin: vendored` entries meet the vendoring-rule contract |
| `check_hook_layout.py` | `hook-layout` | hooks use the ratified `hooks/<name>/hook.py` dir layout |
| `check_roster.py` | `check` | roster ↔ disk drift: every primitive on disk has exactly one `primitives-core.yaml` entry (provenance-manifest schema, ADR 0017); also the translation-matrix completeness gate — every agent frontmatter key, tool, and model alias is named by `translation.yaml` (decision-009) |
| `check_symlinks.py` | `symlinks` | plugin assemblies: every `plugins/` symlink resolves in-repo; `marketplace.json` ↔ assemblies 1:1 |
| `check_flow.py` | `flow` | repo-flow DAG: every top-level path homed in `flow.yaml`, automated edges acyclic, the FLOW.md DAG block in sync (regenerate with `--write-doc`) |
| `check_readme_currency.py` | `readme-currency` (also in `check`) | README currency (decision-015): the last commit touching a skill or plugin also touched that unit's README. Derived from git history — needs a full clone, and a shallow one is a failure, not a skip |
| `check_harness_coupling.py` | `harness-coupling` | `harness/` stays extraction-clean: the shipped package never imports or references repo files outside `harness/` |

## CI-only gates (not in `make ci`)

Each of these needs network or a binary that `make ci`'s offline-and-zero-install contract
forbids, so they run in CI and by hand rather than under `make ci`. They ride the `drift
guards` CI job.

They agree on what an unreachable remote means: all four are red (decision-016 point 4), since
a step that exits 0 having measured nothing reads in the CI summary exactly like one that
measured and found the tree clean.

| Script | Make target | Proves |
|---|---|---|
| `check_version_bump.py` | none — CI step only | changed published bytes ship under a moved version (compares against `origin/main`) |
| `check_removals.py` | none — CI step only | a unit published on `origin/main` and absent here was declared by the commit that removed it (both sets derived from the two trees, never an inventory). `--notes` renders the removals as the release-page section |
| `check_vendored_drift.py` | `vendored-drift` | every `origin: vendored` `base/` still matches its pinned upstream ref |
| `check_manifests.py` | `manifests` | `claude plugin validate --strict` over the marketplace and every assembly (needs the `claude` binary) |
| `check_labels.py` | `labels` | the repo's live GitHub label set is exactly the closed vocabulary (decision-016); names the `gh label delete`/`create` fix for each difference |

## Install-time generation (ADR 0017 — nothing generated is tracked)

- `gen_opencode.py` — builds the opencode laydown from the roster's `targets:` membership
  and the `translation.yaml` capability matrix, at install time only.
- `install_opencode.sh` — the consumer entry point: builds the laydown to a tempdir via
  `gen_opencode.py`, then runs the generated installer (`--global` or `--project <dir>`).
  Re-run after pulling to update.
- `gen_claude_skills.py` — builds the Claude Code **skill** laydown: every roster skill
  targeting claude-code that a bare `.claude/skills/` tree can actually satisfy, copied
  verbatim, plus a generated `install.sh` and a README whose exclusions manifest names every
  primitive that stays behind and why. `--only <id>[,<id>]` builds a subset.
- `install_claude_skills.sh` — the consumer entry point for per-skill installs with no
  marketplace: builds to a tempdir via `gen_claude_skills.py`, then runs the generated
  installer (`--global` into `~/.claude/skills/`, or `--project <dir>`; `--only` forwards to
  the generator). Re-run after pulling to refresh; it only ever replaces its own laydowns
  (each carries a `.laydown` marker) and refuses any directory it did not install.

## Analysis (not in `make ci`)

| Script | What it measures |
|---|---|
| `agent_gaps.py` | Attributes every 60s+ quiet period in the local subagent transcripts (`~/.claude/projects`) to the tool call preceding it, splits self-commanded sleeps into poll vs unconditional, and states the unexplained remainder. `--json`, `--top N`, `--threshold`. |

## Harness campaign (not in `make ci`)

- `harness_campaign.sh` — the full eval grid over cased candidates
  (`run` / `install` / `uninstall` / `status`), wrapped by the `make harness-campaign*`
  targets; needs live CLIs plus keychain access.
- `launchd/` — the plist template `harness_campaign.sh install` renders for the weekly
  LaunchAgent.

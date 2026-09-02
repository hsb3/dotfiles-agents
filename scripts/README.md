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
| `check_roster.py` | `check` | roster ↔ disk drift: every primitive on disk has exactly one `primitives-core.yaml` entry (provenance-manifest schema, ADR 0017) |
| `check_symlinks.py` | `symlinks` | plugin assemblies: every `plugins/` symlink resolves in-repo; `marketplace.json` ↔ assemblies 1:1 |
| `check_flow.py` | `flow` | repo-flow DAG: every top-level path homed in `flow.yaml`, automated edges acyclic, the FLOW.md DAG block in sync (regenerate with `--write-doc`) |
| `check_harness_coupling.py` | `harness-coupling` | `harness/` stays extraction-clean: the shipped package never imports or references repo files outside `harness/` |

## Install-time generation (ADR 0017 — nothing generated is tracked)

- `gen_opencode.py` — builds the opencode laydown from the roster's `targets:` membership
  and the `translation.yaml` capability matrix, at install time only.
- `install_opencode.sh` — the consumer entry point: builds the laydown to a tempdir via
  `gen_opencode.py`, then runs the generated installer (`--global` or `--project <dir>`).
  Re-run after `git pull` to update.

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

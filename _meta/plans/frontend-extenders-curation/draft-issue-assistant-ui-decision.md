# decide: track assistant-ui in externals, or purge the dormant cache

> **Draft — staged, not filed.** Follow-on from #48 curation-plan.md (new find, not in the 2026-07-03 plan). Owner approves before filing.

## Problem

`assistant-ui` (marketplace `assistant-ui-skills`) is present in live config: cached at
`~/.claude/plugins/cache/assistant-ui-skills/assistant-ui/{0.0.1,0.0.2}`, listed in
`installed_plugins.json`, but **not enabled** (`enabledPlugins`, settings.json:48-56). It is a real
frontend plugin — "Skills for building AI chat interfaces with assistant-ui React library" — with
9 skills (assistant-ui, cloud, primitives, runtime, setup, streaming, thread-list, tools, update).
It is **not tracked in da `externals.yaml`**, so it is invisible to the dotfiles-agents provenance
convention: a frontend extender exists on the machine that no manifest records.

## Deliverables — pick ONE

- **Track it**: add an `externals.yaml` entry (kind: plugin, upstream: the assistant-ui-skills
  marketplace repo, pinned ref, provides: the 9 skills, targets: [claude-code]) so it is a
  provenance-recorded external. Enable/disable stays a separate decision.
- **Purge it**: if it is not wanted, remove the dormant cache and the installed_plugins entry so it
  stops shadowing the inventory.

## Acceptance

- [ ] Either: `rg "assistant-ui" externals.yaml` shows a complete provenance entry and `yamllint` passes;
- [ ] Or: the cache under `assistant-ui-skills/` is gone and installed_plugins.json no longer lists it.

## Gates

- yamllint lane (if tracked). None (if purged — machine-local cache).

## Out of scope

- Enabling assistant-ui (dormant-by-default is fine either way).
- Any da roster change (it is a third-party external, not a da primitive).

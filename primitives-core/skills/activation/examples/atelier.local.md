---
# Arms worker-context (injects the worker covenant into every subagent) and
# config-custody (denies subagent edits to the paths below).
enforce: strict            # off (default when absent) | advisory | strict

# fnmatch patterns, project-relative; `*` crosses `/`. Read by config-custody, and
# consulted only while `enforce` is armed. Keep this line bare: the hooks treat
# anything after the colon as the value, so a trailing comment here empties the list.
protected:
  - Makefile
  - .github/workflows/*
  - "*.config.js"

# worker-git-scope-guard: branch NAMES a subagent may not commit, merge, rebase or push
# onto. A different key from `protected` above (that one is file paths) and independent of
# `enforce`. Keep the key line bare, same trap as `protected`.
#
# Ships commented out on purpose: there is no sensible default. Name your own publish-only
# or release branches here — a built-in main/master guard protects the wrong branch in any
# project whose default branch is publish-only and whose real work happens elsewhere. The
# same hook's other half — refusing a stash from a worker sharing this checkout — is live
# regardless and needs no key at all.
# protected-branches:
#   - main

# worktree-isolation: a writing subagent gets its own checkout instead of sharing
# the strategist's working tree. Independent of `enforce`.
isolate: writers           # off (default when absent) | writers | [builder, my-writer]

# session-handoff-surfacer + handoff-freshness-guard read this instead of searching
# _meta/HANDOFF.md, HANDOFF.md, .claude/HANDOFF.md. A path outside the project root is
# rejected and the standard search runs as usual.
#
# Ships commented out on purpose. Uncomment it only once that file exists: an in-root
# path that does not exist reads as "no handoff" to both hooks, and they do NOT fall
# back to the standard search — setting this too early turns handoff surfacing off.
# handoff: .claude/HANDOFF.md
#
# Or, for a handoff that lives on a tracker/board outside the repo (external mode):
# `stamp` is a freshness signal /handoff touches instead of writing a file; `location`
# is free text describing where the real handoff lives. The same fail-open rule applies
# to `stamp` as to the scalar path above — missing, blank, or out-of-root leaves this
# inert and the standard search runs.
# handoff:
#   mode: external
#   stamp: .claude/handoff.stamp
#   location: Kaneo board task DFA-233

# Prose-only: no hook reads this. The delegation skill honours it when an agent
# reads this file, and `activation.py check` validates the spelling.
effort: standard           # standard | deep
---

Everything below the closing fence is ignored by every hook — they read the
frontmatter above and nothing else. Notes to your future self are free here.

Confirm what is actually live, rather than what is written — from the project root:

    python3 "${CLAUDE_PLUGIN_ROOT}/skills/activation/scripts/activation.py" check

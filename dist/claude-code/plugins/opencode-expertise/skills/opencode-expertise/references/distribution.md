# Distributing bundles to opencode

_How the `targets/opencode` output of a Claude Code → opencode translation pipeline should be
laid out and installed. ✅ = verified against https://opencode.ai/docs 2026-07-02._

## Generated bundle layout (proposal)

```
targets/opencode/
  bundles/<bundle-name>/
    agents/<name>.md            # translated agent personas
    skills/<name>/SKILL.md      # translated (or verbatim) skills
    opencode-fragment.jsonc     # mcp servers, permission.skill entries, instructions refs
    AGENTS.snippet.md           # rules content to append/reference
    INSTALL.md                  # laydown instructions (below)
  install.sh                    # optional: performs the laydown per bundle
```

No `plugins/` or `tools/` emitted while hook→opencode stays deferred (capability matrix);
primitives with `requires: [hooks]` are excluded from the bundle with a note, never broken.

## Install = laydown + merge

**Global install** (personal default):
```bash
cp -r bundles/<b>/agents/*  ~/.config/opencode/agents/       # ✅ path
cp -r bundles/<b>/skills/*  ~/.config/opencode/skills/       # ✅ path
# merge opencode-fragment.jsonc into ~/.config/opencode/opencode.jsonc
```

**Project install**: same into `.opencode/agents|skills/` + merge fragment into
`./opencode.jsonc` (or drop as `.opencode/opencode.jsonc` — it's a config level of its own ✅).

**Config merge is safe by design ✅:** arrays concatenate, objects deep-merge, project
overrides global — so a fragment adds `mcp` servers and `permission.skill` grants without
clobbering user config. The generator should still emit idempotent merges (check-before-add)
because *repeated* installs would duplicate array entries.

## The free ride (decide deliberately)

opencode natively reads `~/.claude/skills/` and `.claude/skills/` ✅ and falls back to
`CLAUDE.md`/`~/.claude/CLAUDE.md` for rules ✅. So a machine that already has the claude-code
bundle installed gets skills + rules in opencode **for free**. Options for the generator:

1. **Rely on the fallback** — emit only agents + config fragment. Smallest output; breaks if
   `OPENCODE_DISABLE_EXTERNAL_SKILLS` / `OPENCODE_DISABLE_CLAUDE_CODE` is set, and skill
   names that fail OC's stricter regex are silently invisible.
2. **Emit explicit copies** under `.opencode/skills/` — self-sufficient, survives the disable
   flags, regex enforced at build; costs duplication (mitigated: both copies are generated
   artifacts, never hand-edited).

Recommendation: option 2 for distribution (determinism over cleverness); the drift-guard
discipline already covers generated duplication.

## Gotchas

1. **Plural dirs** ✅ (`agents/`, `skills/`, `tools/`, `plugins/`, `commands/`) — older guides
   say `skill/`/`tool/`; a laydown into singular dirs silently does nothing.
2. **Model IDs need provider prefixes** ✅ (`anthropic/claude-...`) — CC agent frontmatter
   with bare `claude-*` ids fails; the agent translator must remap.
3. **Skill-name regex is stricter** ✅ — underscores/uppercase (e.g. `langsmith_tracing`)
   are invalid; build-time hard check, not install-time surprise.
4. **Hooks don't travel** — plugins are the only event surface and require TS ✅; hook-dependent
   primitives are excluded from OC bundles while translation is deferred.
5. **Permission model differs** — CC settings-allowlists vs OC per-pattern allow/ask/deny;
   ship sensible `permission.skill` grants in the fragment or every skill invocation prompts.
6. **Bun runtime** — any future tools/plugins run on Bun (not node/deno); `$` shell API
   available; keep to stdlib-equivalents per the hooks decision.
7. **opencode moves fast** — re-verify paths/fields against `https://opencode.ai/config.json`
   schema at generator-build time; treat this doc's ✅ marks as dated 2026-07-02.

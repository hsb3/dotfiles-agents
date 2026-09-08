# How a primitive takes a per-project override

Two mechanisms ship in this repo, and they are the whole vocabulary. A third one is a
defect unless it covers something neither of these can. Both were in production before
this page existed; the page names the rule they were already following.

## The rule

| The reader is | Use | Because |
|---|---|---|
| a **hook** | an environment variable with a shell-expanded default in the bundle's `hooks.json` | a hook is a one-shot subprocess with no project context but its env; reading a file to learn a threshold is work it does on every event |
| a **skill or its scripts** | a key in the project-local activation file `.claude/<id>.local.md` | the value is per-project, wants to be committed and shared across machines and worktrees, and the reader already knows the project root |
| **neither — the value is derivable from the tree** | nothing; detect it | an override key that only ever restates what is already on disk is a second source of truth for the same fact |

Naming: the `.local.md` file is named for the **owning bundle** when the setting is
bundle-wide (`.claude/atelier.local.md`) and for the
**skill** when it is one skill's business (`.claude/comms.local.md`,
`.claude/owner-signoff.local.md`). The key inside is named for what it configures.

Fail-open is the default: a key that is absent, blank, or resolves outside the project
root leaves the shipped default in force, and the primitive never errors on it. The one
deliberate exception is `handoff`'s file-mode path, where a stated-but-not-yet-created
override means "this project has no handoff yet" rather than "fall back to the standard
search" — because falling back there would silently guard a different file than the one
the project declared.

## Worked example 1 — hooks: `CONTEXT_WATERMARK_SOFT` / `_HARD`

The wiring supplies the default and the environment wins:

```jsonc
// plugins/atelier/hooks/hooks.json:153
"command": "CONTEXT_WATERMARK_HARD=\"${CONTEXT_WATERMARK_HARD:-160000}\" CONTEXT_WATERMARK_SOFT=\"${CONTEXT_WATERMARK_SOFT:-120000}\" python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/context-watermark/hook.py\""
```

A user overrides one by setting it in `.claude/settings.json` under `env` — documented in
`plugins/atelier/README.md` ("Session-wide settings — environment variables") and in
`primitives-core/hooks/context-watermark/README.md`. The hook itself
(`primitives-core/hooks/context-watermark/hook.py`) reads the variables through `_env_int`
with the same numbers hardcoded as its own fallback, so it behaves identically when it is
run outside the wiring.

## Worked example 2 — skills: the `handoff:` key

`primitives-core/skills/handoff/SKILL.md` ("File location") reads a `handoff:` key from
the project's activation file, `.claude/atelier.local.md`:

```markdown
---
handoff: docs/HANDOFF.md
---
```

The same key also takes a mapping (`{mode: file, path: …}`, or `{mode: external, stamp: …,
location: …}`) for a handoff that is not a file at all. Two hooks read the same key from
the same file — `handoff-freshness-guard` and `session-handoff-surfacer` — which is the
reason the mechanism is a file and not an env var: the skill and its
enforcement hooks have to agree on one project-level fact, and a shared committed file is
what makes them agree.

`owner-signoff` follows this shape for its batch root (`signoff:` in
`.claude/owner-signoff.local.md`, default `_meta/signoff`), and
`python3 scripts/build_signoff.py --batch-root` prints the resolved value so a session
asks instead of guessing. Its **port** deliberately gets no key: `serve_signoff.py` takes
one as an optional positional argument and walks forward when the default is busy, so the
value is per-run, not per-project.

## Decision — `comms` keeps its auto-detect, no key (2026-09-07)

`comms` picks its briefings dir by detection: `_meta/briefings/` when the repo already has
a `_meta/` tree, else `briefings/` at the repo root, and it never creates `_meta/`
(`primitives-core/skills/comms/SKILL.md:9-12`). **That is sufficient as shipped and gets no
override key.** Both candidates are derived from a fact already on disk, which is the third
row of the table above — a key here would let a project declare a `_meta/` layout it does
not have.

Adding one later is cheap and stays cheap, which is the other half of the reason not to add
it now: `.claude/comms.local.md` already exists with flat keys (`theme` / `voice` / `repo` /
`audio`) and `deliver.py` already parses it (`find_local_config` / `load_local_config`,
around `primitives-core/skills/comms/scripts/deliver.py:238`), so a `briefings` key is a few
lines against a reader that is already built. The trigger to add it is a real project that
wants a briefings dir neither candidate names — until then it would be a documented key with
no user, in three places (`SKILL.md`, `README.md`, `references/comm-package-standard.md`).

Parity with `handoff` and `owner-signoff` is not an argument for a key. Those two override a
path that **cannot** be detected: a handoff on a board leaves nothing on disk to find, and a
sign-off batch root has no on-disk tell at all.

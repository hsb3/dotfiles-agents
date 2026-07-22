# Authoring quality — frontmatter, triggering, disclosure, validation

Cross-surface authoring guidance. For the per-surface contract see `surfaces.md`; for subagents
specifically see `subagents.md`. This file is about doing any of them *well*.

## Frontmatter contracts (what each surface requires)

| Surface | Required frontmatter | Common optional fields |
|---|---|---|
| Skill (`SKILL.md`) | `name`, `description` | `allowed-tools`, `metadata` (e.g. `version`) |
| Subagent (`agents/<name>.md`) | `name`, `description` | `tools`, `model` |
| Command (`commands/<name>.md`) | — (body is the prompt) | `description`, `argument-hint`, `allowed-tools`, `model` |

Rules that hold across surfaces:

- `name` is lowercase-kebab and, for skills, **must equal the folder name**.
- `description` must be present for skills and subagents — it is not decoration, it is the
  trigger the model matches on.
- Keep the `description` free of angle-bracket/XML-style tags. A bracketed tag inside a skill
  `description` can make the skill fail to load; use a bracket-free placeholder instead.

## Description / triggering quality (the make-or-break)

For model-invoked surfaces (skills, subagents), the `description` decides whether the surface ever
fires. A good one:

1. **States what it does** — the capability, in one clause.
2. **States when to use it** — the concrete situations, actions, or user phrasings that should
   activate it. This is the part most often missing.
3. **Is specific, not generic.** "Helps with data" matches nothing crisply; "Use when the user
   asks to clean, join, or reshape a CSV/Parquet dataset" matches decisively.
4. **Third person, about the surface's job** — not "I will…", but "Does X. Use when Y."

Weak vs. strong:

- Weak: `description: Assists with releases.`
- Strong: `description: Cuts a release — bumps the version, updates the changelog, tags, and
  drafts notes. Use when the user asks to "cut a release", "publish version N", or "prepare
  release notes".`

## Progressive disclosure

Keep the entry file (`SKILL.md`, an agent body) lean and put depth in `references/*.md` that the
entry file **points to by name**. The model reads the entry first and pulls a reference only when
the task needs it — smaller context, higher relevance. Guidelines:

- Entry file = the map + the decision + pointers. Depth = the references.
- Point to references explicitly ("see `references/x.md` for …") so the model knows they exist.
- Keep every relative link **inside the folder** — no `../` escape, no dangling target. A
  self-contained folder is what lets a skill ship on its own.

## Validation checklist (run before shipping)

- [ ] Frontmatter present and parseable; `name` matches the folder (skills).
- [ ] `description` says what **and** when; no angle-bracket tags in it.
- [ ] Every relative markdown link resolves to a file **inside** the folder (no `../`, no dangling
      targets).
- [ ] No machine-specific content baked in: no absolute home paths, no personal
      names/repo/marketplace names, no secrets. Personalization comes from data/config, never the
      body.
- [ ] Tools/permissions scoped to least privilege (subagents, commands, settings).
- [ ] Hooks: handler reads stdin, signals via exit code/stdout, runs fast, dependency-light.
- [ ] The folder is self-contained (no reference to a sibling skill by path or wikilink) if it is
      meant to ship standalone.

## Common failure modes (and the fix)

- **Skill/subagent never activates** → description lacks the "when". Add concrete triggers.
- **Skill fails to load** → an angle-bracket tag in `description`. Remove it.
- **Wrong surface chosen** → re-check the decision table in `SKILL.md`; event→hook, user-typed→
  command, isolated sub-task→subagent, on-demand knowledge→skill.
- **Broken/escaping links** → keep references inside the folder; fix or inline the target.
- **Machine-tied body** → replace absolute paths with `.claude/`-relative or `~/` forms; move any
  identity/config out of the body into a data surface.

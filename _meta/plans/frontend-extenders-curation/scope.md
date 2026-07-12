---
title: "Scope — frontend skills/plugins"
type: scope
status: draft — awaiting owner need statements
created: 2026-07-12
purpose: The stated-need/scope document that must exist BEFORE any frontend extender is built or promoted (owner ruling 2026-07-12, da#48 D3). What we optimize for and evaluate against.
notes: Section 1 driving-use-case table awaits owner entries; the six draft-issue files in this folder stay held until then.
---

# Frontend extenders — scope

*Owner ruling (da#48, 2026-07-12): the creation-and-promotion process always starts with stated
need/scope. Existing frontend items are a **salvage pile** — available material, not candidates
with their own momentum. Nothing promotes untested, and nothing promotes that doesn't
demonstrably beat (a) no skill at all or (b) an off-the-shelf equivalent from a reputable
source — otherwise it's pure maintenance burden.*

## 1 · Driving use cases (owner input — the load-bearing section)

<!-- One entry per real, named frontend need. No entry here = nothing gets built.
     Format per the entry-form standard (planning-desk references/entry-forms-and-milestones.md):
     project/workflow that needs it · how soon the need is real · what "better than no skill" means for it. -->

| # | Named project / workflow | The frontend work it actually does | How soon | What a skill must beat |
|---|---|---|---|---|
| 1 | *(owner)* | | | |
| 2 | *(owner)* | | | |

Known signal so far (from the 2026-07-12 ruling): **assistant-ui** (React chat UI) is a library
the owner finds useful — tracked in `externals.yaml` with its official skills plugin pinned.
That is a *sourcing* fact, not yet a claimed use case.

## 2 · What already exists (the salvage pile — do not re-inventory)

Canonical catalog: [`inventory.md`](inventory.md) + [`overlap-map.md`](overlap-map.md) (PR #89).
Headlines: **no frontend plugin is enabled anywhere today** (the whole surface is dormant);
proposed-but-unratified core set was 5 skills (carbon-builder, shadcn, react-doctor, external
`frontend-design`, a `frontend-design-tokens` merge); six follow-on issue drafts sit beside this
file as raw material. All of it is claimable by a use case above — none of it self-promotes.

## 3 · Evaluation bar (fixed by ruling; restated once)

A frontend extender ships only when, for a claimed use case in §1:
1. **Tested in real use** on that use case (J1 discipline — citations, not assertions).
2. **Beats no-skill**: a session with it demonstrably outperforms a bare session on the same task.
3. **Beats off-the-shelf**: no reputable third-party equivalent does the job (if one does →
   `externals.yaml`, the assistant-ui path).

## 4 · Out of scope until §1 has entries

Filing the six drafted issues; renaming/merging salvage skills; enabling any frontend plugin;
building `frontend-design-tokens`.

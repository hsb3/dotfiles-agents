---
title: "Batch decision sheet — open owner decisions across the 9 plans (2026-07-03)"
type: reference
status: active
created: 2026-07-03
purpose: "One sitting's worth of rulings: every open owner decision from the 2026-07-03 plan wave, with recommended defaults, ordered by what each ruling unblocks"
notes: "Rule by exception: 'defaults everywhere except ...' is a complete answer. Full rationale lives in each plan's Open questions section; this sheet is the ballot, not the argument."
---

# Batch decision sheet — 2026-07-03 plan wave

_51 open decisions across 9 plans. Every one has a recommended default; approving the
defaults wholesale is a valid ruling and unblocks #39, #32, #27, #36, #37, #48, #49 and
the #33 close-out in one pass. Three items are information requests only Henry can
answer (marked ASK). Ruling format: reply "defaults, except ..." and this sheet gets
annotated + archived with the rulings recorded._

## How the decisions interact (read first)

- **#27 renames vs #37**: #37 deliberately defers the `planning-desk` id question to #27
  (decision 27.2 confirms `pw-plan`). Rule #27 before or with #37.
- **#32 and #27 both bump the plugin version** - coordinate: whichever lands second takes
  the higher bump (#27 is the minor, 0.3.0).
- **#48.2 (aggressive core set) shapes #48's follow-on issue count**; #49.2 keeps the
  board clean by graduating ideas only after ranking - the two together define how much
  new backlog this wave generates.
- Defaults everywhere = no new skill is authored except `pw-workflow` (#27) and possibly
  `python-project-standards` (#32.1).

## 1. #39 roster provenance (decide-first; smallest build after ruling)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 39.1 | Field choice: record pointer vs notes free-text vs ratify summary-as-carrier | Option 1: optional `record:` pointer field |
| 39.2 | Value shape (if field) | Quoted one-liner: record home + event + date + ref |
| 39.3 | opencode-expertise gets the field now | Yes |
| 39.4 | Backfill breadth | Only the two named entries; the 80 core entries adopt via requalification |
| 39.5 | Workbench-side missing roster-update line | File on the workbench (wb#8 trail); out of scope here |

## 2. #32 retire hsb3-custom-plugins (the only P1)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 32.1 | Python trio: fold or drop | Fold python-init/fix/validate into one `python-project-standards` skill carrying the 4 templates; drop the ty-* trio |
| 32.2 | dev-focus dangling session-summary call | Strip it; drop the capability with a note (stdlib-only hook rule) |
| 32.3 | `skills` CLI | Retire (delete script + doc rows) |
| 32.4 | Track auth0-cli + refresh find-skills ref in externals.yaml now | Yes, this wave |
| 32.5 | Issue body stale framing | Leave body; correct via close-out comment |
| 32.6 | Delete `settings copy.bak` | Delete after confirming nothing unrecovered |

## 3. #27 project-workflow v2 (rename wave; rules 37.2 implicitly)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 27.1 | Do the 4 standards skills take pw- too | No; keep the 10-rename set |
| 27.2 | Confirm the 10 names as tabled (pw-plan, pw-agent-md, pw-readme, ...) | As tabled |
| 27.3 | `pw-workflow` roster disposition | `qualified`, citing desk decision 0001 |
| 27.4 | Codify the membership-bump version rule in manifests/naming.md | Yes, this PR |
| 27.5 | Out-of-repo old-name references (dotfiles instructions, caches) | Separate follow-up sweep after merge; checklist item on #27 |
| 27.6 | Plugin README vs docs user guide | Keep both with a split: README = front door, guide = depth |

## 4. #36 externals clone-at-build (7 rulings; enables the research fan-out)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 36.1 | Network in the required CI gate | Pin-keyed short-circuit: re-clone only entries whose pin changed vs the lock |
| 36.2 | Pin format | Full 40-char commit sha in `ref:`; tag + J5 date in a comment |
| 36.3 | Drop policy for the 24 marketplace plugins | Drop-by-default anything with no usage signal |
| 36.4 | Landing namespace | `targets/<t>/externals/<kind>/<id>/`; NOT in marketplace.json |
| 36.5 | Re-pin the `ref: latest` mcp trio now | Yes, in scope |
| 36.6 | Pin-update cadence | None; re-point = deliberate J5 re-review |
| 36.7 | Offline / upstream-gone behavior | Committed targets/ is the artifact of record; document in externals.yaml header |

## 5. #37 ra-platform commands migration

| # | Decision | Recommended default |
|---|----------|---------------------|
| 37.1 | Reuse planning-desk vs author a new skill | Reuse (the redesign already shipped as planning-desk) |
| 37.2 | Skill id vs naming lane | Leave id untouched; #27 owns the pw-plan rename |
| 37.3 | How ra-platform consumes | Marketplace plugin; pin enabledPlugins in tracked settings if the field verifies |
| 37.4 | ra-platform's tracked _utils/ | Keep, resynced against the skill's copies |
| 37.5 | Migration record home | workbench docs/promotions-log.md, dated callout record |
| 37.6 | ASK: what did T-19 mean by "work-surface-hygiene automation"? | Interpreted as the desk governance toolkit + CLAUDE-07 row; confirm or name the extra automation |

## 6. #33 Gate-2 close-out (mostly confirms; raptorgpt tree also awaits your commit)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 33.1 | Author AGENTS.md + CHARTER now or defer | Defer to the brownfield epic (rgpt#578/#579 filed); carry as content-authoring rows in the gap ledger |
| 33.2 | In-flight PLANS docs + staged-*.md frontmatter | Justify as in-flight; file the staged-drafts exemption as a standards issue (extends #45) |
| 33.3 | CLAUDE-07 (opsx commands dir) | Migration debt gated on rgpt#544 openspec ruling |
| 33.4 | ASK: confirm the vault = Obsidian `hsb-2026` for TC-013/TC-010 records | High confidence; one-word confirm wanted before writing addenda |
| 33.5 | When #33 closes | After re-audit evidence + 100%-justified ledger + your TC ticks |
| 33.6 | Where the brownfield epic lives | rgpt-side, absorbing rgpt#542-554; cross-link only from da |

## 7. #48 frontend curation (report-only wave)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 48.1 | Where the inventory lands | The plan folder (desk); pointer in workbench if wanted |
| 48.2 | How aggressive the core set is | Aggressive: single-digit core; client-token plugins split per wb#25, not kept |
| 48.3 | obsidian-chat-ui in scope | Inventory yes, curation no (owned by the Obsidian domain) |
| 48.4 | Client-token bundles: genericize or split | Split per the wb#25 precedent (capability stays, tokens to client store) |
| 48.5 | frontend-design external provenance gap | Inventory row here + its own small follow-on issue |
| 48.6 | Missing frontend-extras install | Note-only; survival is a curation decision first |

## 8. #49 idea-backlog seed (capture wave)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 49.1 | Interim backlog home (blocks the wave) | Restructure cowork desk analyses/backlog.md in place, T-23 absorption flag in header |
| 49.2 | Per-idea GitHub issues now or after ranking | After ranking; near-term use cases (CMS data mart: ideas 5, 6, 7) graduate first |
| 49.3 | ASK: where are the ra-platform API-doc notes (idea 3)? | Land entry with explicit ask-marker; checkbox 3 waits on your answer |
| 49.4 | Idea 2 (claude-code add-on) with no use case | Enter as unranked wishlist line, not declined |

## 9. #59 agnostic base format (deepest; survey resolves the rest)

| # | Decision | Recommended default |
|---|----------|---------------------|
| 59.1 | Adopt vs adapt vs build | Working hypothesis: build thin in-repo schema, adopt conventions where they exist; survey A tests it |
| 59.2 | Skills stay SKILL.md-shaped | Yes |
| 59.3 | Unsupported-feature policy | Surfaced-unsupported first-class (lock + build summary + smoke); never hard-fail |
| 59.4 | Agent carrier format | Keep .md + constrained frontmatter dialect, enforced by validate |
| 59.5 | Neutral env-placeholder syntax | Keep `${VAR}` as source form; renderers translate out |

## The three ASK items (information, not preference)

1. **37.6** - what "work-surface-hygiene automation" meant in T-19 (or confirm the toolkit reading).
2. **33.4** - confirm the vault for TC records is the `hsb-2026` Obsidian vault.
3. **49.3** - the location of the ra-platform API-documentation notes (idea 3's source material).

# Decision brief — 2026-07-12 execution wave

*Purpose: everything from the 2026-07-12 wave that needs an owner ruling, with background and a recommendation per item. Write your answer under each **Your ruling:** line; the next session reads this doc and executes.*
*Status: **EXECUTED 2026-07-12** (all rulings transcribed + executed: 11 PRs merged — 9 wave + wb#42 hook retirements + da#94 assistant-ui/scope-doc; ruling comments on da#33/#48/#82/#83/#32, wb#35/#40; handoff PRs da#96 + wb#43). Superseded by the repo handoffs. Was: awaiting owner rulings · Written 2026-07-12 · Location is `_meta/briefings/` (untracked working desk) — rulings get transcribed to the issues/PRs when executed.*

**What happened today (one paragraph):** the session executed the P0/P1 stack across both repos with agent crews. Nine PRs are open, all CI-green, none merged: dotfiles-agents [#90](https://github.com/hsb3/dotfiles-agents/pull/90) (roster re-triage, issue #81), [#88](https://github.com/hsb3/dotfiles-agents/pull/88) (entry-form + milestone standard, issue #84), [#89](https://github.com/hsb3/dotfiles-agents/pull/89) (frontend curation report, issue #48), [#91](https://github.com/hsb3/dotfiles-agents/pull/91) (plan folders for #68/#69/#70/#82/#83), [#92](https://github.com/hsb3/dotfiles-agents/pull/92) (handoff + records, merge last); workbench [#39](https://github.com/hsb3/dotfiles-agents-workbench/pull/39) (python-standards skill, wb#37), [#40](https://github.com/hsb3/dotfiles-agents-workbench/pull/40) (receives 14 demotions), [#38](https://github.com/hsb3/dotfiles-agents-workbench/pull/38) (lifecycle cites the entry form), [#41](https://github.com/hsb3/dotfiles-agents-workbench/pull/41) (handoff). Two records were posted to issues: the Gate-2 baseline on da#33 and the hook-evaluation dossier on wb#35. The decisions below are the judgment calls that surfaced; everything else is mechanical review-and-merge (checklist in the appendix).

---

## Decision 1 — Gate-2 pilot (#33): what does "pilot proven" mean now?

**Background.** The Gate-2 pilot was re-pointed to `hsb3/fleet-dashboard` on 2026-07-05, with the proof sequence: baseline audit → `mise-en-place.yml` → scaffold apply → re-audit. The baseline ran today (foreman-verified with two independent runs): **69 pass / 1 gap** at commit `3d81a48`. The only gap is `DOCS-02 — docs/CHARTER.md missing`, which is authored content the scaffold deliberately never creates (the same class of gap as wb#30 on the workbench). Because fleet-dashboard was already brought near-conformance by earlier work, the remaining pilot steps can only demonstrate **idempotence on an already-clean repo** (a `--plan` run showing ~0 creations), not the gap-filling the pilot was designed to showcase. Meanwhile the *prior* pilot on raptorgpt-agents (rgpt#541, kept as a "complete prior" record) DID demonstrate gap-filling: 36/22 → 56/3.

**Options.**
- **(a) Accept the two pilots jointly as the Gate-2 proof** — raptorgpt proved gap-filling, fleet-dashboard proves idempotence/no-false-positives on a conformant repo. Remaining work: run the scaffold `--plan` idempotence check, author fleet-dashboard's `CHARTER.md` (owner content, small), refresh the stale plan.md prose (it still narrates the raptorgpt sequence), close #33.
- **(b) Re-point Gate-2 a second time** at a repo with real gaps, and run the full sequence there. Cleaner single-repo story; costs another pilot cycle and a third re-point record.

**Recommendation: (a).** The evidence for both halves of the promise already exists; a second re-point buys narrative tidiness, not proof. If you take (a), say whether you want the session to author a draft CHARTER.md for fleet-dashboard or you'll write it yourself.

**Your ruling:** agree with recommendation.

---

## Decision 2 — wb#35: attest the 10 hook evaluations

**Background.** The 10 dotfiles hooks entered the workbench incubator via wb#36 and the J1–J4 evaluation dossier is posted on [wb#35](https://github.com/hsb3/dotfiles-agents-workbench/issues/35#issuecomment-4950162020) (evidence spot-verified before posting). J-checks are human-attested — the dossier recommends, you rule. Headline evidence: none of the 10 has citable J1 (≥2 real uses); two are **confirmed duplicates** (`post-write-format` is a strict functional subset of the `python-standards` hook — verified by diffing the handlers; `multiplexer-task-completion-ping` implements the identical DONE-ping protocol as the hook bundled inside the `multiplex-agent-manager` candidate); and the two hooks with checkable on-machine state (`session-end`'s own log: 2 smoke entries in 4 months; `speak-summary`'s state dirs: absent) show they sat live and unused.

Mark each row: **retire** (delete from incubator, record in promotions-log) / **keep incubating** (gather J1 evidence) / **re-scope** (per the dossier's options).

| Hook | Dossier recommendation | Your ruling |
|---|---|---|
| post-write-format | retire — subset of the python-standards hook | |
| post-lint | retire (or re-scope to shellcheck-only) | |
| notify-memory-write | retire — thin value, macOS-only | |
| curate-memories | **promote-track** — strongest J2; needs J1 evidence | |
| inject-context | re-scope or retire — unresolved J4 vs built-in context | |
| session-end | retire — its own log disproves use | |
| notify-on-stop | retire — content-free duplicate of the other Stop notifiers | |
| speak-summary | re-scope — sole-survivor Stop notifier IF the speak_gemini wiring is confirmed working | |
| multiplexer-task-completion-ping | retire — consolidate into multiplex-agent-manager | |
| web-setup | re-scope to **check-and-notify** (dossier option 2), or retire if harness-native remote setup suffices | |

**Recommendation:** accept the dossier as written — 7 retire, keep `curate-memories` incubating with a deliberate J1 plan (enable it for a few weeks), re-scope `speak-summary` and `web-setup`. If you want fewer decisions: retiring all except `curate-memories` and `web-setup` loses little.

**Your ruling (blanket or per-row above):** agree with the above.  i think we should never have hooks that aren't associated with a plug-in.  even if this means we have a plug-in with just hook(s).  If we find that there is a substantial number of hooks that are useful on their own (don't also require agents/mcp servers/skills) we create create a hook bundle.

---

## Decision 3 — #48 frontend curation: file the six drafted issues?

**Background.** The curation report (PR #89, report-only) landed the inventory, overlap map, and curation plan in `_meta/plans/frontend-extenders-curation/`, honoring your 2026-07-03 rulings (aggressive single-digit core; split client-token bundles per the wb#25 precedent). Proposed core set: 5 skills — carbon-builder, shadcn, react-doctor, the Anthropic `frontend-design` external, and a new `frontend-design-tokens` merge. Six follow-on issues are **drafted as files, not filed**: frontend-extras-retire · client-token-bundles-split · webapp-designer-decompose · frontend-design-provenance · assistant-ui-decision · core-rename. Two findings you should know: **no frontend plugin is currently enabled anywhere** (the whole surface is dormant), and **`assistant-ui`** (a 9-skill React chat plugin) is installed/cached but tracked by no manifest — a real extender that exists outside the system of record.

**Options.** (a) File all six as issues after PR #89 merges; (b) file a subset (name them); (c) amend drafts first.

**Recommendation: (a)** — file all six; they're small and each traces to a ruling or a verified finding. Separately, give a direction on `assistant-ui` now (its draft issue offers: track in `externals.yaml` vs purge the installation) — **recommend track**, since it's in live use as an installed plugin and untracked state is the actual hazard.

**Your ruling:** We need to create create a scope document for frontend skills/plug-ins.  Let's just assume existing items are available for salvage.  our process for creating and promoting extenders/plugins always needs to start with stated need/scope.  this will help us know what we're optimizing for and thus evaluate.  we shouldn't promote skills that haven't been tested, don't perform better than no skill or off-the-shelf from reputable source (why create the maintance burden) Also, assistant-ui should be added to curated list of externals as i find the assistant-ui library useful. 

---

## Decision 4 — da#88 standard: ratify the "unranked wishlist" rule?

**Background.** The entry-forms standard (planning-desk `references/entry-forms-and-milestones.md`) is grounded in ratified practice except one genuinely new rule, marked **Proposed**: *an idea with no driving use case yet enters the backlog as a one-line unranked wishlist entry, and is promoted to a full backlog issue only when a named near-term use case claims it.* It operationalizes the ratified `use-case-driven-backlog` decision and the #49 owner-default, but as a standing rule it's new text.

**Recommendation: ratify.** It's the natural completion of use-case-driven-backlog; without it the standard is silent on what happens to unclaimed ideas. If ratified, the next session flips the "Proposed" marker in a follow-up commit (can ride the #89/#91 merge window).

**Your ruling:** ratified.

---

## Decision 5 — Plan-wave contradictions (recorded in the #91 plans, need rulings before those issues build)

**5a — #82/#83 ordering.** #83's issue body literally says the both-artifacts gate lands "after the rename" (#82). The plans recommend the reverse — #68 → #83 → #82 — because the rename touches every desk consumer and is safest last, with the gate already protecting folder shape during it. **Recommendation: rule the plans' order (#83 before #82)** and treat the issue-body clause as stale text, corrected via issue comment.

**5b — #82 standard-vs-instance.** Renaming `_meta/plans` → `_meta/issues` collides with the repo-meta-structure standard, whose checklist rows define `_meta/plans/` for **all** repos. Options: rename the standard itself + migrate adopting repos [plans' recommendation]; tolerate either path in the checklist; or declare a per-repo variance here. **Recommendation: rename the standard + adopter migrations** — either-path tolerance erodes the point of a standard, and a variance makes the flagship repo the deviant.

**5c — #83 filename grammar.** The #83 issue text uses `issue_body.md` (underscore); every existing artifact on disk uses `issue-body.md` (hyphen). The plan treats the underscore as a typo and standardizes on the hyphen. **Recommendation: confirm hyphen.**

**Your ruling (5a / 5b / 5c):**  i agree with all recommndations

---

## Decision 6 — Bench-side dispositions from the #81 demotions (low urgency)

**Background.** Per #81 all 14 items were demoted to the incubator now, with judgment deferred bench-side. Two carried explicit "decide" flags: **setup/update-project-dashboard** (disambiguate vs the proven `board-reporting` skill — the REGISTRY rows carry the J4 blocker) and the **cms-* trio** (genericize before any re-promotion). Nothing blocks on these today; they surface whenever the bench evaluation happens.

**Recommendation:** no ruling needed now — but if you already know you want the dashboards pair merged into `board-reporting` or simply retired, saying so here saves the bench evaluation a cycle.

**Your ruling (optional):**. like with all the frontend stuff. let's put these in a pile for salvage.  let's pivot to using business case to drive what we build.

---

## Appendix — merge checklist (mechanical, no rulings needed)

Order matters because #90, #88, #92 rebuild `targets/` + the lock:

1. da **#90** (re-triage) — merge first
2. da **#88** (standard) — rebase + `make build`, then merge
3. da **#89** and **#91** (docs-only) — any order; trivial `_meta/plans/README.md` row rebases
4. da **#92** (handoff/records) — merge **last**, rebase + `make build`
5. wb **#39** and **#40** — either first; rebase the second (`REGISTRY.md`, promotions-log)
6. wb **#38**, **#41** — any time
7. After all merges: `git worktree prune` in both repos (9 wave worktrees are listed in the da handoff), pull both mains, run `make ci` (da) + `make promote-check-all` (wb) once green-on-main.

Also queued for the next session, no ruling needed: **#32 close-out** (unblocks when wb#39 merges — cite it as the decision-1 fold path), and the carried owner TODO to record the wb#32 gate-ratification decision in the vault registry.

**RULING ON APPENDIX:**  Please coordinate all merges.  

---



**NEW APPENDIX**

- As this matures, we will evolve the testing infrastructure.  Some things are already built or under development in other repos that we can borrow from.
  - /Users/henry/Documents/DEVELOPER/fable-optimization
  - /Users/henry/Developer/_SANDBOX/zInactive/ralph-harness
  - we can also configure experiments using the multica app and drive with the cli.  /Users/henry/Desktop/Multica-Setup/




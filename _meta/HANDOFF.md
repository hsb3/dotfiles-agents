# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked). Not a journal — shipped work lives in git/PR history; this holds current state, in-flight work, decisions, and the gotchas that bite.*

## 0 · Orientation

Source of truth for **proven** coding-agent extenders (created 2026-06-26; built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays frozen as the migration source). Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (the unproven bench — promotes one-way INTO here), `dotfiles-bootstrap` (deploy/orchestrator). Governance on the strategy desk (`~/Documents/Claude/Projects/dotfiles-agents-cowork/`): `_structure/{CANON.md, repository-technical-plan.md}` is the design constitution; `analyses/` is historical. The promotion gate + lifecycle live in `dotfiles-agents-workbench/docs/`. **Planning desk** at `_meta/plans/` — run the `planning-desk` skill; `_config.md` has the gate menu.

## 1 · Current state

- **Translation service is feature-complete** across all four primitive types (skills · agents · CMA payloads · mcp) plus internal + externals-mcp inputs: `scripts/translate.py` renders `primitives-core/` + `externals.yaml` → `targets/{claude-code,opencode,claude-agents}/` + a content-hash lock. **Roster/build/test counts are live — run `make ci`** (5 lanes: `check` roster↔disk · `validate` primitive content · `names` id grammar · `build-check` targets drift · `test`). Green on main; roster at 65 ids (agent=18, skill=47) + 8 plugin ids after the merged #90 re-triage (project-workflow now 0.3.1).
- **Roster schema:** `origin: authored|sourced` (internal is dead), required `disposition:`, optional `requires:` capability flags, sourced ⇒ `upstream`+`ref` guard-enforced.
- **Promotion gate RATIFIED** (CANON 12; J1 = ≥2 real uses). **Branch protection** live: required check is the `make ci` aggregate; force-push/deletion blocked; admin bypass retained — agents PR.

## 2 · In flight / next up

- **The 2026-07-12 wave is FULLY EXECUTED (merged same day):** all 9 wave PRs landed (da #90 #88
  #89 #91 #92 · wb #39 #40 #38 #41) plus the two ruling-execution PRs (wb#42 hook retirements,
  da#94 assistant-ui + frontend scope doc). Owner rulings (verbatim in
  `_meta/briefings/2026-07-12-wave-decisions/brief.md`, untracked) are all transcribed to the
  issues: #33 joint-proof + idempotence record, wb#35 dispositions, #48 scope-first pivot,
  #82/#83 ordering + hyphen, wb#40 salvage-pile note. Worktrees pruned, both mains green
  (`make ci` / `make promote-check-all`). The unranked-wishlist rule is ratified in the shipped
  entry-form standard (#88).
- **NEW STANDING POLICIES from the rulings (both recorded in repo docs, CANON recording = owner TODO):**
  (1) *no standalone hooks* — every hook promotion names its owning plugin (hook-only plugins fine;
  hook-bundle plugin if enough accumulate) — promotion-gate H4 amendment, wb#42.
  (2) *scope-first extenders* — creation/promotion always starts from a stated-need/scope doc
  (business case); never promote untested skills or ones that don't beat no-skill / reputable
  off-the-shelf. Encoded in `_meta/plans/frontend-extenders-curation/scope.md`; demoted/frontend
  items are a **salvage pile** claimed by use cases, never self-promoting.
- **Next build waves, in order:**
  1. **#32 close-out** (the only P1) — unblocked; decision-1 fold path = wb#39's `python-standards`
     skill (cited on the issue). Residuals: 16-command disposition record, python-standards
     `templates/` + dev-focus `session-summary.py` rescue, retire the dead `skills` CLI, three
     dotfiles doc surfaces, archive the frozen repo. **Machine-state gotcha (recorded on #32):**
     `~/.claude/skills/` currently has 8 symlinks into the frozen repo — more than the plan's
     2026-07-03 verification found; re-verify before archiving.
  2. **#33 close-out** — joint proof complete (raptorgpt gap-filling + fleet-dashboard idempotence
     `0 create / 3 conflict / 1 manual / 66 ok`, both on the issue). Remaining: draft
     fleet-dashboard `docs/CHARTER.md` for owner review, refresh the pilot plan.md's stale
     raptorgpt prose, then close.
  3. **#27** (pw- rename, plugin 0.3.x→0.4.0?) and the planned wave **#68 → #83 → #82** (ruled
     order; #82 renames the repo-meta-structure STANDARD + migrates adopters).
- **Frontend (#48): paused on owner input** — `scope.md` §1 driving-use-case table awaits owner
  entries; the six drafted issues stay held; `assistant-ui` now tracked in `externals.yaml`
  (pinned to the installed clone's ref).
- **Workbench follow-ups:** enable `curate-memories` live for its J1 evidence window; confirm
  `speak-summary`'s speak_gemini wiring (condition of its sole-survivor re-scope); rework
  `web-setup` to check-and-notify.
- **Owner TODOs (vault/CANON):** record the wb#32 gate-ratification, the raptorgpt-GO
  supersession in `DECISIONS.md`, and the two new standing policies above.
- **Testing-infrastructure note (owner, 2026-07-12):** as this matures, evolve testing by
  borrowing from `~/Documents/DEVELOPER/fable-optimization`,
  `~/Developer/_SANDBOX/zInactive/ralph-harness`, and Multica-app experiments driven via CLI
  (`~/Desktop/Multica-Setup/`) — machine-local references, keep them out of primitives. Unranked
  wishlist until a use case claims it (per the ratified rule).
- **fleet-dashboard is the plugin test bed** (owner decision 2026-07-03) and the Gate-2 pilot.
- **J1 upgrades (post-Q-13):** items upgrade to `qualified` on ≥2 cited real uses
  (re-qualification record in the workbench promotions log) or demote on failure-in-use. #37's
  ra-platform adoption is use-citation #1 for `planning-desk`. **Promoting a parked item**
  (CANON 12) needs ≥2 cited real uses + H1–H5; `opencode-expert` is the strongest candidate.
- **PR #86 (fable-foreman skill) is still open** — predates the wave, not part of it; review/merge
  separately.

## 3 · Conventions & gotchas

- **Never hand-edit generated `targets/` or the results lock** — they're drift-guarded. Edit `primitives-core/` then `make build`.
- **Tests are stdlib `unittest` only** — keep `make ci` zero-install (no pytest/uv in the required lane). **Fixtures live under `tests/` temp dirs, never `primitives-core/`** — `check_roster.py` flags on-disk orphans. Drift guards prove *consistency*; the tests + `validate_primitives.py` prove *correctness*.
- **SKILL.md `description` must not contain XML/angle-bracket tags** — Claude Cowork refuses to load such skills. Skill-specific: agent `.md` descriptions may use `<example>`. Enforced by `validate_primitives.py`.
- **Primitives must be machine-agnostic (#79, enforced in `make ci`):** no `/Users/...`, personal
  vault names, `~/Documents|Desktop` paths, or `--break-system-packages`; `~/dotfiles`,
  `/Applications/`, and machine-local tools (cc-project-memory, speak_gemini, …) are legal only
  with a covering roster `requires:` (`cli:<name>` / `env:dotfiles`); stdio mcp specs need an
  `install: {upstream, command}` block; hook configs are handler references only, inline prose
  ≤ 20 words. The workbench gate mirrors these (H5/H6/H4, wb#32). Gotcha: the scanners are literal
  substring matches — even *quoting* a forbidden token in prose flags (hit twice this wave).
- **Naming grammar is shared with the workbench:** `tests/test_check_naming.py` imports the sibling `../dotfiles-agents-workbench/scripts/promote_check.py` constants and asserts no drift — but it **silently skips when the sibling checkout is absent**, including from INSIDE a da worktree (the relative path breaks); run it once from the main tree after worktree-based waves. Keep the two repos side-by-side; don't rename the grammar constants on either side.
- **Board scripts are authoritative HERE** (`primitives-core/skills/github-project-board/scripts/`) — deliberately diverged from frozen hsb3-custom-plugins; never re-copy from the frozen repo.
- **Archived plans:** `_meta/_archive/<issue>-<slug>.md` (tracked via gitignore negation). On close, `git mv` the `plan.md` there and move its README row ACTIVE→ARCHIVED so `reconcile.py` stays clean. Run `_meta/plans/_utils/` scripts from the **main tree** (they read live `gh` + disk; `coverage.py`/`reconcile.py` resolve the desk via `__file__`, so a worktree copy reads the worktree's desk). ACTIVE README rows use the **bare slug**, not a markdown link.
- **`gh` token gotcha:** env `GITHUB_TOKEN` can't resolve project-board owner — use `env -u GITHUB_TOKEN gh …` for `gh project` / `gh repo create`.
- **Conflicting PRs get NO CI:** GitHub skips `pull_request` workflows when the merge ref won't build — "no checks reported" means rebase onto main first, not that CI failed.
- **Deploy targets (verified, opencode 1.16.2):** opencode agents → `.opencode/agent(s)/` or `~/.config/opencode/agent(s)/`; opencode skills auto-scanned from `~/.claude/skills/` + `~/.agents/skills/` (config loaded once — restart opencode to pick up new skills). CC marketplace = two generated catalogs: `claude plugin marketplace add hsb3/dotfiles-agents` reads the repo-root `.claude-plugin/marketplace.json`; a local-path add of `targets/claude-code` reads that dir's own marketplace.json (what `dotfiles-bootstrap` uses). Both drift-guarded in `make ci`.
- `bgIsolation:none` in `.claude/settings.json` — this repo isn't parallel-mutated by default; when a session DOES run parallel da builders, give each its own `git worktree` + branch (this wave's pattern).
- Trunk-based, remote is SSH: branch `<type>/<name>`, squash-merge, commits end with the `Claude-Session:` footer; agents PR (don't push main).

## 4 · Incident log

- **2026-07-04 — `gh issue edit` cross-repo clobber (recovered).** While filing the wave
  issues, `gh issue edit 32 --body-file <workbench-body>` ran from the dotfiles-agents cwd
  and overwrote **da#32**'s body (retire-hsb3-custom-plugins) instead of workbench#32.
  Restored within minutes from GitHub's edit history (GraphQL `userContentEdits` — the
  `diff` field holds full body snapshots). Lesson: **always pass `-R <owner>/<repo>` to
  `gh issue edit`/`view` when the target repo isn't the cwd** — issue numbers collide
  across sibling repos, and da/wb numbering is close enough to bite again.
- **2026-07-12 — stale local wb main nearly clobbered REGISTRY rows (caught pre-PR).** Two
  agents branched worktrees off the LOCAL workbench main, which was 2 commits behind
  origin/main (missing the wb#36 intake merge); their REGISTRY.md edits would have dropped
  the 10 hook rows. Caught by a read-only evaluator noticing the discrepancy; both branches
  rebased onto origin/main before opening PRs. Lesson: **fetch + branch worktrees from
  `origin/main`, not local main**, in repos other sessions merge to.

# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked). Not a journal — shipped work lives in git/PR history; this holds current state, in-flight work, decisions, and the gotchas that bite.*

## 0 · Orientation

Source of truth for **proven** coding-agent extenders (created 2026-06-26; built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays frozen as the migration source). Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (the unproven bench — promotes one-way INTO here), `dotfiles-bootstrap` (deploy/orchestrator). Governance on the strategy desk (`~/Documents/Claude/Projects/dotfiles-agents-cowork/`): `_structure/{CANON.md, repository-technical-plan.md}` is the design constitution; `analyses/` is historical. The promotion gate + lifecycle live in `dotfiles-agents-workbench/docs/`. **Planning desk** at `_meta/plans/` — run the `planning-desk` skill; `_config.md` has the gate menu.

## 1 · Current state

- **Translation service is feature-complete** across all four primitive types (skills · agents · CMA payloads · mcp) plus internal + externals-mcp inputs: `scripts/translate.py` renders `primitives-core/` + `externals.yaml` → `targets/{claude-code,opencode,claude-agents}/` + a content-hash lock. **Roster/build/test counts are live — run `make ci`** (5 lanes: `check` roster↔disk · `validate` primitive content · `names` id grammar · `build-check` targets drift · `test`). Green on main; note da#90 shrinks the roster 80→64 ids when it merges (14 demotions + hook removal).
- **Roster schema:** `origin: authored|sourced` (internal is dead), required `disposition:`, optional `requires:` capability flags, sourced ⇒ `upstream`+`ref` guard-enforced.
- **Promotion gate RATIFIED** (CANON 12; J1 = ≥2 real uses). **Branch protection** live: required check is the `make ci` aggregate; force-push/deletion blocked; admin bypass retained — agents PR.

## 2 · In flight / next up

- **2026-07-12 execution wave — 9 PRs open, all CI-green; owner has AUTHORIZED coordinated merging (ruling above) — merging them in order is the next session's FIRST task.**
  Merge order matters because three PRs rebuild `targets/` + the lock:
  1. **da#90** — #81 roster re-triage: 14 demotions moved to the workbench (incl. the `python-standards` hook as `python-standards-hook`), `framework-selection` + 4 `openspec-*` flipped to `origin: sourced` with pinned refs; follows the #79/#80 entry-removal mechanic (the issue's literal `disposition: demoted` is vestigial); empties + removes 3 plugins (`dev-focus`, `project-dashboard`, `python-standards`), `obsidian-plugin-dev` survives at 0.1.2.
  2. **da#88** — #84 entry-form + milestone-set standard (planning-desk reference + plugin 0.2.5): rebase + `make build` after #90.
  3. **da#89** (#48 curation report, docs-only) and **da#91** (plans for #68/#69/#70/#82/#83, docs-only) — any order; trivial `_meta/plans/README.md` row rebases.
  4. **da#92** — this handoff + pptx-henry narrative learning + #33 baseline record: merge LAST (rebase + `make build`).
  wb: **#40** (receives the 14 da#81 demotions) and **#39** (wb#37 `python-standards` SKILL, spec-first, hard checks green) — either first, second rebases `REGISTRY.md`; **#38** (lifecycle cites the entry form at intake) and **#41** (wb handoff) independent. wb#39 and wb#40 both note the skill-vs-hook name distinction. After all merges: `git worktree prune` both repos, pull both mains, re-run `make ci` (da) + `make promote-check-all` (wb).
- **OWNER RULINGS received 2026-07-12** (verbatim answers in `_meta/briefings/2026-07-12-wave-decisions/brief.md` — untracked, main tree only; this summary is authoritative for execution):
  1. **#33 Gate-2 — option (a) accepted:** the two pilots jointly are the Gate-2 proof (raptorgpt = gap-filling 36/22→56/3; fleet-dashboard = idempotence, baseline 69/1 at `3d81a48`). Remaining: scaffold `--plan` idempotence run, draft fleet-dashboard `CHARTER.md` for owner review (author not specified — draft it, don't finalize), refresh the stale pilot plan.md, close #33.
  2. **wb#35 — dossier accepted as written:** 7 retire · `curate-memories` promote-track (enable it, gather J1) · re-scope `speak-summary` + `web-setup` (check-and-notify variant). **NEW STANDING POLICY from this ruling: hooks are never standalone — every hook ships inside a plugin** (hook-only plugins are fine; if useful independent hooks accumulate, create a hook-bundle plugin). Record this in the gate/CANON when executing the retirements.
  3. **#48 — PIVOT, do NOT file the six drafts as-is:** author a **frontend scope document first**; treat ALL existing frontend items as a **salvage pile** (available for parts, not presumed keepers). Standing process rule: extender creation/promotion always starts from stated need/scope (business case); never promote untested skills or ones that don't beat no-skill or a reputable off-the-shelf alternative (maintenance burden). Exception executed directly: **`assistant-ui` → add to the curated externals list** (`externals.yaml`) — owner finds the library useful.
  4. **da#88 unranked-wishlist rule — RATIFIED:** flip the *Proposed* marker in a follow-up commit.
  5. **Plan contradictions — all plan recommendations accepted:** #83 lands before the #82 rename (correct #83's body clause as stale via comment); #82 renames the repo-meta-structure STANDARD + migrates adopters (no either-path tolerance); `issue-body.md` hyphen confirmed (underscore in #83 body = typo).
  6. **#81 bench dispositions — salvage pile:** dashboards pair + cms-* trio (and by extension the demoted candidates generally) sit as salvage; **business case drives what gets built/revived** — same pivot as ruling 3.
  - **MERGE AUTHORIZATION:** owner ruled "coordinate all merges" — execute the merge queue below without further approval, then transcribe rulings to the issues (comment #33, attest wb#35 rows, #48 pivot comment, #82/#83 corrections).
  - **Testing-infrastructure note (owner):** as this matures, evolve testing by borrowing from `~/Documents/DEVELOPER/fable-optimization`, `~/Developer/_SANDBOX/zInactive/ralph-harness`, and Multica-app experiments driven via CLI (`~/Desktop/Multica-Setup/`) — machine-local references, keep them out of primitives.
- **#32 close-out is unblocked once wb#39 merges:** cite wb#37/wb#39 as the decision-1 fold path (python content ported, templates byte-match, ty-* trio dropped per ruling 32.1; naming supersession `python-project-standards`→`python-standards` recorded in the scope doc). Residuals: 16-command disposition record, the three dotfiles doc surfaces, archive the frozen repo.
- **Plan-folder coverage complete after merges** — #68–#83 folders land via da#91; #81/#84 folders ride da#90/da#88; `coverage.py` then reports zero unplanned.
- **fleet-dashboard is the plugin test bed** (owner decision 2026-07-03) and the Gate-2 pilot — see decision (a) above.
- **J1 upgrades (post-Q-13):** items upgrade to `qualified` on ≥2 cited real uses (re-qualification record in the workbench promotions log) or demote on failure-in-use. #37's ra-platform adoption is use-citation #1 for `planning-desk`. **Promoting a parked item** (CANON 12) needs ≥2 cited real uses + H1–H5; `opencode-expert` is the strongest candidate.
- **Worktrees left in place for PR review** (prune after merges): da `.claude/worktrees/{retriage-81,entry-form-84,frontend-48,plans-wave,recon-12}`; wb `.claude/worktrees/{receive-81,python-standards-37,lifecycle-ref-84}`.
- One owner TODO carried from #79: record the gate-ratification decision in the vault registry.

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

# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked). Not a journal — shipped work lives in git/PR history; this holds current state, in-flight work, decisions, and the gotchas that bite.*

## 0 · Orientation

Source of truth for **proven** coding-agent extenders (created 2026-06-26; built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays frozen as the migration source). Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (the unproven bench — promotes one-way INTO here), `dotfiles-bootstrap` (deploy/orchestrator). Governance on the strategy desk (`~/Documents/Claude/Projects/dotfiles-agents-cowork/`): `_structure/{CANON.md, repository-technical-plan.md}` is the design constitution; `analyses/` is historical. The promotion gate + lifecycle live in `dotfiles-agents-workbench/docs/`. **Planning desk** at `_meta/plans/` — run the `planning-desk` skill; `_config.md` has the gate menu.

## 1 · Current state

- **Translation service is feature-complete** across all four primitive types (skills · agents · CMA payloads · mcp) plus internal + externals-mcp inputs: `scripts/translate.py` renders `primitives-core/` + `externals.yaml` → `targets/{claude-code,opencode,claude-agents}/` + a content-hash lock. **Roster/build/test counts are live — run `make ci`** (5 lanes: `check` roster↔disk · `validate` primitive content · `names` id grammar · `build-check` targets drift · `test`). Green on main; note da#90 shrinks the roster 80→64 ids when it merges (14 demotions + hook removal).
- **Roster schema:** `origin: authored|sourced` (internal is dead), required `disposition:`, optional `requires:` capability flags, sourced ⇒ `upstream`+`ref` guard-enforced.
- **Promotion gate RATIFIED** (CANON 12; J1 = ≥2 real uses). **Branch protection** live: required check is the `make ci` aggregate; force-push/deletion blocked; admin bypass retained — agents PR.

## 2 · In flight / next up

- **2026-07-12 execution wave — 8 PRs open awaiting owner review; none merged (agents PR only).**
  Merge order matters because three PRs rebuild `targets/` + the lock:
  1. **da#90** — #81 roster re-triage: 14 demotions moved to the workbench (incl. the `python-standards` hook as `python-standards-hook`), `framework-selection` + 4 `openspec-*` flipped to `origin: sourced` with pinned refs; follows the #79/#80 entry-removal mechanic (the issue's literal `disposition: demoted` is vestigial); empties + removes 3 plugins (`dev-focus`, `project-dashboard`, `python-standards`), `obsidian-plugin-dev` survives at 0.1.2.
  2. **da#88** — #84 entry-form + milestone-set standard (planning-desk reference + plugin 0.2.5): rebase + `make build` after #90.
  3. **da#89** (#48 curation report, docs-only) and **da#91** (plans for #68/#69/#70/#82/#83, docs-only) — any order; trivial `_meta/plans/README.md` row rebases.
  4. **da#92** — this handoff + pptx-henry narrative learning + #33 baseline record: merge LAST (rebase + `make build`).
  wb: **#40** (receives the 14 da#81 demotions) and **#39** (wb#37 `python-standards` SKILL, spec-first, hard checks green) — either first, second rebases `REGISTRY.md`; **#38** (lifecycle cites the entry form at intake) independent. wb#39 and wb#40 both note the skill-vs-hook name distinction.
- **Owner decisions surfaced this wave:** (a) **#33 Gate-2:** baseline ran 2026-07-12 — **69 pass / 1 gap** (only `docs/CHARTER.md`, authored content) at fleet-dashboard `3d81a48`; the remaining scaffold steps would prove idempotence, not gap-filling — accept that as pilot completion or re-point Gate-2 (comment on #33; verbatim table in `_meta/plans/fleet-dashboard-pilot/baseline-audit-2026-07-12.md`; plan.md prose still narrates raptorgpt and needs a refresh). (b) **wb#35:** attest the J1–J4 hook dossier (posted on the issue; 0/10 clear today — `curate-memories` promote-track, `speak-summary`/`web-setup` re-scope decisions, 7 retire-leaning, two confirmed duplicates). (c) **#48:** review the curation report + 6 draft follow-on issues staged in `_meta/plans/frontend-extenders-curation/` (headline findings: NO frontend plugin is enabled anywhere; `assistant-ui` is installed but untracked by any manifest). (d) **da#88 standard:** the "unranked-wishlist" rule is marked *Proposed* — ratify or strike. (e) **da#91 plans:** recorded contradictions needing rulings — #82/#83 ordering (plans recommend #83 before the #82 rename, against #83's literal body text) and #82's standard-vs-instance question (renaming `_meta/plans`→`_meta/issues` forces a repo-meta-structure standard change or a declared variance).
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

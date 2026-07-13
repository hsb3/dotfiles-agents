# HANDOFF — dotfiles-agents

*Cold-start bridge. Secret-free (secrets live in `_meta/operations/`, never tracked). Not a journal — shipped work lives in git/PR history; this holds current state, in-flight work, decisions, and the gotchas that bite.*

## 0 · Orientation

Source of truth for **proven** coding-agent extenders (created 2026-06-26; built from scratch — NOT a rename of `hsb3-custom-plugins`, which stays frozen as the migration source). Siblings: `dotfiles` (tooling), `dotfiles-agents-workbench` (the unproven bench — promotes one-way INTO here), `dotfiles-bootstrap` (deploy/orchestrator). Governance on the strategy desk (`~/Documents/Claude/Projects/dotfiles-agents-cowork/`): `_structure/{CANON.md, repository-technical-plan.md}` is the design constitution; `analyses/` is historical. The promotion gate + lifecycle live in `dotfiles-agents-workbench/docs/`. **Planning desk** at `_meta/plans/` — run the `planning-desk` skill; `_config.md` has the gate menu.

## 1 · Current state

- **Translation service is feature-complete** across all four primitive types (skills · agents · CMA payloads · mcp) plus internal + externals-mcp inputs: `scripts/translate.py` renders `primitives-core/` + `externals.yaml` → `targets/{claude-code,opencode,claude-agents}/` + a content-hash lock. **Roster/build/test counts are live — run `make ci`** (5 lanes: `check` roster↔disk · `validate` primitive content · `names` id grammar · `build-check` targets drift · `test`). Green on main; roster at 65 ids (agent=18, skill=47) + 8 plugin ids after the merged #90 re-triage (project-workflow now 0.3.1). fable-foreman is live on core (PR #86 closed in favor of merged PR #95).
- **Both desks audit clean (2026-07-12 pass):** compliance 70/0 here · 69/1 workbench (gap = wb#30 charter); all open issues template-conformant, plan-covered, milestoned; evidence audit + reconcile + sync-bodies all exit 0 (PR #97). **Provenance audit ran over all 65 items:** roster labels honest (all 22 `sourced` carry upstream+ref), BUT 22 items are third-party content vendored in `primitives-core/` and the charter is SILENT on the sourced-vs-external boundary (the "tracked, not vendored" rule exists only in CLAUDE.md) — remediation staged, below.
- **Roster schema:** `origin: authored|sourced` (internal is dead), required `disposition:`, optional `requires:` capability flags, sourced ⇒ `upstream`+`ref` guard-enforced.
- **Promotion gate RATIFIED** (CANON 12; J1 = ≥2 real uses). **Branch protection** live: required check is the `make ci` aggregate; force-push/deletion blocked; admin bypass retained — agents PR.

## 2 · In flight / next up

- **#99 SHIPPED 2026-07-13 (ADR-0006):** `_meta/` is now tracked by default everywhere — this
  repo + the packaged standard via PR #102, workbench via wb PR #45, fleet-dashboard via its
  PR #14 (all squash-merged, audits 69/1 with only the known charter gaps). Plan archived at
  `_meta/_archive/99-meta-gitignore-policy.md` (+ adopter notes alongside). Residuals resolved
  2026-07-13: dotfiles rules/instructions reworded (dotfiles PR #77) — but the dotfiles repo's
  OWN `_meta/*` stanza was deliberately left (flipping it would newly track machine-local
  scratch; owner call, procedure in the archived adopter note; the dotfiles-expert skill's
  repo-and-stow line stays accurate until then). The #82 sequencing constraint is cleared:
  #99 landed first.
- **Owner-approved close-outs, queued not started (2026-07-12):** #32 first (residuals + the
  8-symlink machine-state gotcha are on the issue), then #33 (draft fleet-dashboard CHARTER for
  owner review + refresh the plan's stale raptorgpt prose, then close).
- **Two staged proposals await owner approval to FILE** (`_meta/plans/inbox/`, merged via PR #98):
  (1) *third-party disposition* — boundary ADR + per-item disposition for the 22 vendored sourced
  items (depends on #36 for any move-to-externals); (2) *plugin business-case retrofit* — entry-form
  core applied to each of the 8 plugins, retire/merge proposal where no credible case exists.
  Decision brief with all links: https://claude.ai/code/artifact/7356f208-9e49-44ef-a928-a43dfdd55226
  (source tracked at `_meta/briefings/2026-07-12-extender-governance-brief/` since #99/PR #102).
- **Ecosystem survey done** (owner request, incl. his links ECC + gsd-core):
  `_meta/research/extender-distribution-ecosystem.md` — tracked since PR #102.
  Net: ruler/rulesync are the peers, ECC the closest at scale, agentskills standardization
  pushes translation value toward agents/hooks/mcp/plugins; recommendation = fold into #59, no new issue.
- **The 2026-07-12 wave** (9 wave PRs + 2 ruling-execution PRs, both repos) is fully merged and
  transcribed; details live in the PRs and `_meta/briefings/2026-07-12-wave-decisions/`. The
  unranked-wishlist rule is ratified in the shipped entry-form standard (#88).
- **NEW STANDING POLICIES from the rulings (both recorded in repo docs, CANON recording = owner TODO):**
  (1) *no standalone hooks* — every hook promotion names its owning plugin (hook-only plugins fine;
  hook-bundle plugin if enough accumulate) — promotion-gate H4 amendment, wb#42.
  (2) *scope-first extenders* — creation/promotion always starts from a stated-need/scope doc
  (business case); never promote untested skills or ones that don't beat no-skill / reputable
  off-the-shelf. Encoded in `_meta/plans/frontend-extenders-curation/scope.md`; demoted/frontend
  items are a **salvage pile** claimed by use cases, never self-promoting.
- **After those:** #27 (pw- rename, plugin 0.3.x→0.4.0?) and the ruled wave **#68 → #83 → #82**
  (#82 renames the repo-meta-structure STANDARD + migrates adopters; #99 landed first, so the
  no-interleave constraint is satisfied).
- **Watch-item:** fable-foreman entered core via PR review, without bench J1 evidence — cite real
  uses as they occur or expect it to surface at the next re-triage (the #81 precedent demoted 14).
- **Frontend (#48): paused on owner input** — `scope.md` §1 driving-use-case table awaits owner
  entries; the six drafted issues stay held; `assistant-ui` now tracked in `externals.yaml`
  (pinned to the installed clone's ref).
- **Workbench follow-ups:** enable `curate-memories` live for its J1 evidence window; confirm
  `speak-summary`'s speak_gemini wiring (condition of its sole-survivor re-scope); rework
  `web-setup` to check-and-notify. (The stray `_meta/archive/` dup dir is gone — wb PR #46.)
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
- **Archived plans:** `_meta/_archive/<issue>-<slug>.md` (tracked — `_meta/` is track-by-default per ADR-0006). On close, `git mv` the `plan.md` there and move its README row ACTIVE→ARCHIVED so `reconcile.py` stays clean. Run `_meta/plans/_utils/` scripts from the **main tree** (they read live `gh` + disk; `coverage.py`/`reconcile.py` resolve the desk via `__file__`, so a worktree copy reads the worktree's desk). ACTIVE README rows use the **bare slug**, not a markdown link.
- **`gh` token gotcha:** env `GITHUB_TOKEN` can't resolve project-board owner — use `env -u GITHUB_TOKEN gh …` for `gh project` / `gh repo create`.
- **Conflicting PRs get NO CI:** GitHub skips `pull_request` workflows when the merge ref won't build — "no checks reported" means rebase onto main first, not that CI failed. (On a FRESH branch it can also just be a registration race — wait ~10s and re-run `gh pr checks`.)
- **`audit.py` outside the harness needs `--plugin-root`** — `$CLAUDE_PLUGIN_ROOT` is unset in plain Bash; pass the plugin cache dir (see the repo-compliance-audit skill's run instructions).
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

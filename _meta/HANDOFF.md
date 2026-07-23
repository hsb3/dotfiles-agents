# HANDOFF — dotfiles-agents

_Cold-start bridge. Last updated: 2026-07-22. Refresh at session boundaries (/handoff). Secret-free._

## 0 · Orientation

dotfiles-agents is a Claude Code marketplace of coding-agent extenders, assembled from
`primitives-core/` into plugin bundles by `scripts/gen_marketplace.py`. `dev` = source, `main` =
CI-published (publish-only, ADR 0014). Task interface + source-of-truth rules: see CLAUDE.md (hot-loaded).

## 1 · Current standing

Both build epics are **DONE and CLOSED**; `make ci` is green (38 primitives: agent=4, hook=4,
skill=30). `dev` carries the extender-db merge (#176), the harness (#169), the #174 telemetry
lane (PR #177), the campaign runner (PR #178, §2c), and — as of the 2026-07-22 `/waves` run
below — 4 more merged PRs (#205, #206, #209, #210). **`main` published 2026-07-22 at
`dev@0cdca55`** (commit `098e1b7`) — **now lags `dev` by those 4 PRs**; next publish should pick
them up (see `publish-to-main` skill).
- **#111** clean-room rebuild and **#134** desk-set restructure — both merged + CLOSED (era detail: git/issues).
- **Open PRs: 0.**

Live marketplace lineup (post ADR 0016 recomposition, 2026-07-22): **code-desk (0.3.0)** — the
sole desk bundle, now including planning-desk, comms, board-triage, pptx-themes (former
exec-desk, retired) — · foreman-kit (0.6.0) · diagrams · obsidian-toolkit · 11 standalones:
github-project-board · opencode-expertise · pptx-themes · private-fork · **project-memory**
(absorbed memory-taxonomy) · owner-signoff · claude-code-expertise · dataviz · deep-research ·
**claude-code-config** (renamed from update-config) · **tech-eval-research** (new). `main` lags
`dev` until next publish.

**Also live: the extender-db mini-project** (§2b) — separate effort from the rebuild epics; do
not fold it into dev without Henry's promotion decision (already taken 2026-07-21, see §2b).

## 2 · Recent deliveries (era pointers — blow-by-blow lives in issues/git)

- 2026-07-20/21: rebuild epics closed, extender-db epic #154 Waves 0–3 executed, harness
  follow-ups (#177/#178) delivered. Full detail in git/issue history.
- 2026-07-22 (early session): ADR 0008 executed (filtered parented publish + `dist/` lift lanes,
  PRs #180–184); main-checkout guard + memory curation + `project-memory` skill migration
  (PRs #200–202); published dev → main (`098e1b7`); triage issue **#192** created.
- 2026-07-22 (owner's court session): D1/D2/D4/D5 + O1/O2/O3 all ruled and executed — memory
  folder rename (PR #194), bundles→top-level (PR #195), extender-db children reviewed/closed,
  meta-harness pointer confirmed (PR #198), forward-skill-wave split (#139 approved standalone,
  #137/#138 held on estate review). Full record: triage #192 + issue comments, not repeated here.
- **2026-07-22 (this session) — `/waves` run, 4 of 5 planned waves executed:**
  PR #205 (#139 claude-code-expertise skill) · PR #206 (#149 `_meta/reference/` taxonomy gap +
  #151 CONTRIBUTING.md + #203 ADR 0015 backfill) · PR #209 (#32 retirement: `dev-focus` skill
  migrated, python-project-standards dropped per ruling, hsb3-custom-plugins unblocked) · PR #210
  (#37 planning-desk skill confirmed to subsume ra-platform's commands — **ra-platform's own
  adoption is staged uncommitted in that separate repo, pending Henry's review/commit + a live
  smoke test**). W5 (#152 visual-planning) **not shipped** — see §3. Follow-ups filed: #207, #208,
  #211. Triage #192 refreshed to "Delivery plan v2."
- **2026-07-22 (estate-restructure session, branch `feat/estate-restructure`):**
  (a) **ADR 0016 lineup recomposition** — exec-desk folded into code-desk (0.3.0);
  opencode-expertise + private-fork standalone-only; memory-taxonomy + project-memory merged
  into one `project-memory` skill; update-config renamed `claude-code-config`;
  `tech-eval-research` skill added (authored, standalone). (b) **GitHub issues reboot** —
  all 99 issues archived to `_meta/_archive/issues-reboot-2026-07-22/`; 18 open issues
  rewritten to the What/Why/Done-when structure; labels cut 30 → 5 (`type:feat` / `type:fix` /
  `type:chore` / `decision` / `epic`, ≤3 per issue, declared in `_meta/mise-en-place.yml`);
  #122 closed as dup of #36; #191 kept open as a standing decision record; issue-form
  templates added under `.github/ISSUE_TEMPLATE/`. (c) **_meta compliance** — `_archive/` +
  `plans/` created; briefing decks + signoff package moved to the exec desk (copied
  uncommitted into `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk`, deleted here);
  agent-harness wave handoffs archived; HOOK-01 inline-hook gap fixed. (d) **`.claude/plugins/`
  workbench** — Anthropic's plugin-dev, skill-creator, mcp-server-dev vendored as in-repo
  file-based plugins via a local `workbench` marketplace in `.claude/settings.json`
  (local-dev-tooling, never distributed).

## 2b · Extender-db mini-project (merged to dev 2026-07-21)

PocketBase DB of all agent extenders + the mental models used to compose/evaluate them. **Self-
describing — read `evals/_structure/CHARTER.md`, `PLAN.md`, `OPEN-ITEMS.md`, `evals/README.md`,
`evals/PROCEDURES.md` first**; below is only what they don't carry.

- **State:** epic #154 Waves 0–3 DONE; O1 (2026-07-22) closed all 9 functionally-complete
  children (#155–162, #167) with outcome notes. Epic stays open for #163 (M3) · #164 (M4) · #165
  (M5, unblocked per O2/PR #198) · #166 (M6) · #168.
- **Operational:** server `evals/serve.sh` (admin UI 127.0.0.1:8090/_/); creds in untracked
  `_meta/operations/extender-db.env`. `pb_data/data.db` is TRACKED — stop the server before
  committing (WAL checkpoint) or switching branches (a live server had its tracked data.db
  checked out from under it once; `pgrep -fl pocketbase` → kill → checkout → restart).
  `pb_migrations/` is gitignored on purpose: `schema.py` is the ONE schema source.
- Gotcha list (idless-PATCH column drops, 5000-char text cap, live-proof mandate, scoped deltas,
  json first-byte coercion, file fields need `create_multipart`) lives in `evals/PROCEDURES.md`.

## 2c · Agent-harness (delivered 2026-07-21, PR #169 → dev)

Reusable extender-eval harness at root `harness/` (self-contained uv project): drives Claude Code
or opencode headlessly, grades two-tier, appends to `harness/results.jsonl`. **Self-describing —
read `_meta/research/agent-harness/DESIGN.md`, `harness/README.md` first.** Owner intent:
battle-test here, later extract to its own repo.
- **Auth for live runs:** `export ANTHROPIC_API_KEY="$(secret get ANTHROPIC_API_KEY)"` (per-run
  apiKeyHelper + fresh CLAUDE_CONFIG_DIR — Option Z; `--bare` strips the Skill tool, don't use it).
- **Campaign runner** (PR #178): `make harness-campaign` + weekly LaunchAgent live on this machine
  (Mon 09:00). **Never auto-ingests** — after each run, ingest deliberately
  (`load_harness_runs.py --campaign weekly-YYYYMMDD`) and commit data.db+storage with cause.
- Open follow-ups: #172 (hermeticity/env-pinning), #173 (candidate-quality findings).

## 3 · Next up (dotfiles-agents proper)

**Source of truth is the pinned triage issue #192** ("Delivery plan v2", refreshed 2026-07-22) —
ranked backlog + owner decision queue live there, not duplicated here. Prior planning-round
detail (D1–D5, O1–O3, the NOTE.md fold-in) is fully executed; see triage #192 history / issue
comments for the record, not repeated here.

**What's actionable right now: nothing dotfiles-agents-proper is unblocked-and-unbuilt** — this
session's waves run cleared #139/#149/#151/#203/#32/#37. Remaining work is all owner-gated:

- **#36/#122/#193 — decisions 1-7** (network-at-build in CI, drop policy, ref-pin format) for the
  externals clone-at-build mechanism. Unresolved across two sessions now.
- **#152 visual-planning — deferred, not just gated.** A crew found (Henry independently
  re-verified) the 3 candidate skills (`hsb3/agent-native-sandbox` `.claude/skills/{visual-plan,
  visual-recap,visualize-repo}/`) are installed-from-upstream (`agent-native-skill.json` sidecars
  are the proof), not authored originals — shipping `origin: authored` would violate ADR 0015.
  `ghcr.io/hsb3/plan-app` also fails the identity lint unconditionally (no container-image
  exemption). **Henry: "will revisit later, they still need to be tested."** Path forward when
  revisited: (A) via #36's mechanism once built, (B) genuinely re-author as first-party originals,
  or (C) an explicit ADR 0015 exception — see the comment trail on #152.
- **#137/#138** (decision-loop/release-loop skills) — HELD on the desk-platform estate-cohesion
  IA review (§4), not a same-session call.
- **ra-platform's `.claude/commands` → planning-desk adoption** — the repo-side is merged (PR
  #210), but `~/Developer/ra-platform` itself has an **uncommitted** working-tree diff (deletes
  `.claude/commands/{plan-issue,issue-body}.md`, adds `_meta/plans/_config.md`, enables
  `exec-desk@dotfiles-agents` in `.claude/settings.json`) staged by the crew and left for Henry to
  review/commit in that repo's own session, plus a live smoke test.
- New small follow-ups filed this session: #207 (universal `reference/` taxonomy slot), #208
  (project-local primitive-authoring skill), #211 (confirm board-reporting coverage).
- **Board repopulation DONE** (2026-07-22, after owner granted `project` scope): DEV-TOOLING
  project #11 now carries exactly #36, #152, #154 from this repo; other repos' 30 items
  untouched. Gotcha: the project has an **auto-add-sub-issues workflow** — adding epic #154
  pulled in 14 children (removed again); new sub-issues of #154 will reappear unless that
  workflow is toggled off in the project settings UI. Desk-side: the four folders copied into
  the dotfiles-agents-desk repo are still left **uncommitted** there for owner review/commit.

## 4 · CROSS-REPO — desk-platform design effort (lives on the desk, NOT here)

A separate product design effort on the exec desk (NOT dotfiles-agents): a toolkit integrating AI
agents against one data model across three planes (input · activity · output), PocketBase-backed.
**R3 (element model) drafted + both adversarial reviews done — awaiting Henry's IA approval.**
State lives at `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/
desk-platform/` (`plan.md` = round index; `spec-element-model.md` = the proposal + review
findings). No change this session — still waiting on Henry to approve/adjust/veto the 5 major IA
changes + 4 open questions named in `spec-element-model.md`. Nothing folds into the canonical
model until he signs off (standing directive, §5).

## 5 · Conventions & gotchas

- Source-of-truth rules are in CLAUDE.md (hot-loaded) — not duplicated here.
- **`main` is publish-only** — never hand-commit/merge there; a CI guard fails PRs into main.
  Branch off `dev`, PR into `dev`. `main` is a **filtered parented assembly** (never a dev
  snapshot — verify with tree hashes per the `publish-to-main` skill runbook).
- **dev's branch-protection required checks are pinned by CI JOB NAME** — renaming a job in
  `ci.yml` strands every PR on a check that never reports. Update the protection setting first.
- **PRs into `dev` do NOT auto-close their `Closes #N` issues** — auto-close only fires on the
  *default* branch (`main`). **Close issues by hand after every merge into dev.**
- **`flow.yaml` is load-bearing**: `make flow` (in `make ci`) fails any PR that adds a top-level
  path without a declared home. Regenerate the FLOW.md DAG with `scripts/check_flow.py --write-doc`.
- **ADR 0015 (self-authored-only) is now on disk and mechanically enforced**
  (`scripts/check_provenance.py`) — no `origin: sourced` body may live under `primitives-core/`,
  full stop; third-party content must go through `externals.yaml` + the clone-at-build mechanism
  (#36, still unbuilt). This blocked #152 this session — check any future "package an upstream
  skill" ask against this before scoping a wave.
- **`isolation: worktree` Agent calls in this repo have repeatedly checked out from a *published*
  commit instead of `dev`** (5/5 crews this session) — see project memory
  `worktree-agents-check-out-published-commit`. Every worktree-crew brief must include the
  self-check (`primitives-core/` missing → `git reset --hard origin/dev`) until root-caused.
- **Cross-repo crew pattern (new, proven this session):** when a wave's work spans dotfiles-agents
  + a separate consumer repo (e.g. ra-platform), the crew may read/draft in the other repo but
  must leave its changes **uncommitted** there — mutating a second repo's git history is reserved
  to the human, same as `main`. Confirmed working via git worktree isolation; see PR #210.
- Worker agents can drop `.claude/agent-memory/` into whatever directory they worked in — sweep
  stray nested `.claude/` dirs before committing (never whole-dir `git rm` the root `.claude/`).
  Tracked store is `.claude/memory/` (repo root) since #194.
- **Never check out `main` locally** — a PreToolUse hook denies it in agent sessions; a
  machine-local `post-checkout` hook warns on manual checkouts.
- **Henry signs off on major IA changes before they are finalized/built** (standing directive;
  memory `approve-major-ia-changes`). Present IA changes as an approval gate, not a done deal.
- Machine-local leftover: `evals/pb_data/data.db.local-backup-2026-07-21` (gitignored) —
  reconcile or delete next time a session works in `evals/`.

## 6 · Map

- **Pinned triage issue #192** — `meta: triaged open-issue backlog (living list)`: the in-repo
  ranked backlog view + delivery plan + owner decision queue. Refresh it (edit the body, never
  commit) at session boundaries alongside `/handoff`. Three tracks: dotfiles-agents-proper
  (waves) · extender-db epic #154 (self-manages via `evals/_structure/`) · agent-harness
  #172/#173.
- CLAUDE.md — task interface + rules · `.github/CONTRIBUTING.md` (new) — human-facing
  contribution loop · `docs/decisions/` — ADR mirrors (now includes 0015).
- **Exec desks:** this repo's desk is `~/Documents/EXECUTIVE_DESK/Projects/dotfiles-agents-desk/`;
  desk-standard work is `.../desk-standard-desk/`; the former dev-tooling-desk (desk-platform
  design) is archived at `.../ARCHIVE/dev-tooling-desk-old/`.

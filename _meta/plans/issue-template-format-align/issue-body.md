## What happened

`mhi-raptorxai/raptorxai-infra`, 2026-07-03: planning-desk setup mode seeded issue templates from its assets — `feature.md`, `bug.md`, `epic.md` (markdown templates). Immediately afterwards, repo-compliance-audit flagged:

```
GH-01 | GAP | missing file: .github/ISSUE_TEMPLATE/config.yml
GH-02 | GAP | missing file: .github/ISSUE_TEMPLATE/bug.yml
GH-03 | GAP | missing file: .github/ISSUE_TEMPLATE/feature.yml
GH-04 | GAP | missing file: .github/ISSUE_TEMPLATE/epic.yml
```

So a repo that adopts the plugin's own planning-desk defaults audits as non-conformant against the plugin's own repo-meta-structure standard: one skill ships `.md` issue forms, the sibling standard's checklist requires the `.yml` issue-forms set plus `config.yml`.

Also, planning-desk's conformance gate (`conformance.py`) reads required sections from `.github/ISSUE_TEMPLATE/*.md` — if a repo carries the standard's `.yml` forms instead, it's unclear the desk's conformance checking still works, so the two skills may be unsatisfiable simultaneously rather than just inconsistent.

## Suggested direction

Pick one template format for the plugin (issue-forms `.yml` seems to be where the standard is) and make planning-desk seed it and parse it; or teach the checklist to accept either format. Either way, the audit -> scaffold -> desk loop shouldn't fight itself.

Version caveat: planning-desk executed from plugin cache 0.1.0, repo-compliance-audit from 0.2.1. If planning-desk 0.2.x already seeds yml forms, the remaining bug is just the stale-cache/mixed-version behavior (see also: the marketplace cache served two different plugin versions for sibling skills in one session).

---

## Corrected scope (verified against plugin source 0.2.4)

This issue was filed against cache 0.1.0. Re-verifying against current source narrows it: **one half is live, one half is invalid.**

- **LIVE — the template-format conflict is real.** `primitives-core/skills/planning-desk/assets/ISSUE_TEMPLATE/` ships `bug.md` / `feature.md` / `epic.md` (markdown templates, no `config.yml`), while `repo-meta-structure/references/checklist.md:53-56` GH-01..04 require `config.yml` + `bug.yml` + `feature.yml` + `epic.yml`. `SKILL.md:104-106` and `_config.template.md:18-20` still seed/point at the `.md` set, so a repo adopting planning-desk defaults fails the sibling audit GH-01..04.
- **INVALID — the `conformance.py` sub-claim does not hold.** `conformance.py:42-59` reads live issue **bodies** via `gh issue list ... --json body`; it reads no files from `.github/ISSUE_TEMPLATE/`. It is format-agnostic and does NOT break on `.yml` forms. No change needed there.

## Acceptance criteria

- planning-desk seeds the `.yml` issue-forms set (`config.yml` + `bug.yml` + `feature.yml` + `epic.yml`) that GH-01..04 expect, OR the checklist is taught to accept either format; a fresh `planning-desk` setup then passes `repo-compliance-audit` GH-01..04.
- `SKILL.md` setup section and `_config.template.md` no longer point only at `.md` template paths.
- `conformance.py` is left unchanged (confirmed already format-agnostic).

**Owner decision:** which format wins — ship `.yml` forms in planning-desk (align to the standard) [recommended default], or teach the checklist to also accept `.md`?

## Dependencies & gates

- **Blocks on:** the format decision above.
- **Gates:** `make ci` green + `targets/` regenerated via `make build` when planning-desk assets change; `project-workflow` version bump. Relates to `repo-meta-structure` GH-01..04.


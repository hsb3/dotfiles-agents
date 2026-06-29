# Focus Validation Checklists

Machine-readable pass/fail criteria. Evaluate every item and compute score as: `(passed / total) * 100`.

---

## Task Decomposition Checklist

| # | Check | Weight | Fail Condition |
|---|-------|--------|----------------|
| 1 | Task restated in one clear sentence | required | Vague or compound goal |
| 2 | Concrete steps listed (not phases) | required | "Phase 1: do stuff" |
| 3 | Each step has clear done criteria | required | No way to know when step is finished |
| 4 | Complexity estimated (small/medium/large) | required | No size awareness |
| 5 | Large tasks split into independent chunks | required | Monolithic 9+ file change |
| 6 | Items explicitly deferred or cut | recommended | Everything marked essential |
| 7 | No step depends on unbuilt infrastructure | recommended | Hidden blockers |

---

## Scope Review Checklist

| # | Check | Weight | Fail Condition |
|---|-------|--------|----------------|
| 1 | Not everything is "must have" | required | No real prioritization |
| 2 | Each item has effort awareness | required | Can't assess feasibility |
| 3 | Total must-have effort fits session/sprint | required | Committed to more than fits |
| 4 | No item depends on something unbuilt | recommended | Hidden dependency chain |
| 5 | Each item traces to the core goal | required | Building because we can |
| 6 | Done criteria defined for the batch | required | No way to measure completion |
| 7 | Explicit DEFER and CUT categories used | required | Binary in/out thinking |

---

## Session Focus Checklist

| # | Check | Weight | Fail Condition |
|---|-------|--------|----------------|
| 1 | Original task clearly stated | required | Ambiguous starting point |
| 2 | Work stayed on original task | required | Drifted into unrelated changes |
| 3 | No orphaned files or dead code left | required | Cleanup not done |
| 4 | Created files follow project naming conventions | required | Inconsistent naming |
| 5 | Progress checkpointed on multi-step work | recommended | Silent work with no visibility |
| 6 | Loose ends surfaced before ending | required | Incomplete work not communicated |

---

## Scoring

- Required items = 10 points each
- Recommended items = 5 points each
- Score = `(earned / max) * 100`

**Thresholds:**
- **80+**: Focused — on track
- **60-79**: Drifting — course correct
- **<60**: Unfocused — stop and re-scope

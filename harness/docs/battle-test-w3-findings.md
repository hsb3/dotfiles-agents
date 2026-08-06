# Wave-3 battle-test — findings report

_48-trial grid over 3 roster candidates × {claude, opencode} × claude-sonnet-4-5 ×
{with, baseline} × 3 trials. Ledger: `harness/results.jsonl` (commit aa23533). Every
conclusion below survived an adversarial re-derivation from raw logs by an independent
reviewer (3/3 claims CONFIRMED, 2026-07-21)._

Status: active. Date: 2026-07-21.

## 1 · Grid results

| Candidate / case | claude Δ | opencode Δ | skill fired (with-cells) | Reading |
|---|---|---|---|---|
| mermaid / add-architecture-diagram | +0.33 † | +0.0 (ceiling 3/3) | claude 0/3 † · opencode 3/3 | † claude delta is noise — see §2.1 |
| mermaid / avoid-reserved-node-id | 0.0 (0/3 both) † | 0.0 (0/3 both) | claude 0/3 † · opencode 3/3 | skill fired, still failed — §2.3 |
| scout (agent) / stale-config-trap | +0.0 (3/3 both) | +0.0 (3/3 both) | n/a (agent kind) | ceiling: sonnet beats the traps unaided |
| readme-value-and-proof / local-bookmark-vault | 0.0 (0/3 both) † | **+1.0** (0/3 → 3/3) | claude 0/3 † · opencode 3/3 | the flagship genuine delta — §2.2 |

## 2 · Verified verdicts (adversarial review, all CONFIRMED)

### 2.1 Claude skill-cells are structurally void [HIGH — harness defect]
Every claude `-p` trial's resolved toolset is `['Bash','Edit','Read']` — **no `Skill`
tool** — while the injected skill correctly appears in the session's skills list with zero
plugin errors. `skill_used=0/9` on claude was mechanically forced, not model routing; all
claude skill deltas in this grid (incl. the +0.33) are uninformative noise. Root:
`adapters/claude.py:114-133` (`--bare` + `--permission-mode acceptEdits` + conditional
`--allowedTools Bash` never surface `Skill`). Fix direction: extend allowedTools (probe
empirically that init `tools` then contains `Skill`), then re-run claude cells.

### 2.2 opencode readme +1.0 is a genuine, correctly-graded skill effect
With-runs invoked the skill by name, then followed its doctrine end-to-end: honest-gap
section, roadmap bullets, and a real self-captured screenshot (run installed Playwright,
started the app, captured 6 PNGs). Grader citations match the produced README verbatim;
baselines produced none of it; checks applied identically in both configs.
Caveats: (a) the rubric encodes the skill's own doctrine, so Δ measures
doctrine-conformance, not independent README quality; (b) the pass path is
environment-contingent (runtime Playwright install — a blocked npm would collapse it).

### 2.3 mermaid avoid-reserved-node-id: execution failure under prompt pressure, check is fair
All 3 opencode with-trials fired the skill and still emitted bare `end` as a node id
(trial 0 even *wrote the correct fix* `end_stage[end]`, then reverted it). The check
enforces exactly the skill's own rule (SKILL.md:146: rename the id); the escape was
achievable within the prompt's constraints. Verdict: the skill's guidance is adequate but
not *held* by sonnet under a prompt that pressures toward the violation — a real
candidate-level finding about skill robustness, not a case defect.

## 3 · Defect / follow-up register (ranked)

1. **[HIGH]** ClaudeAdapter never surfaces the `Skill` tool (§2.1) → fix + re-run claude cells. → issue
2. **[MED]** Ledger can't distinguish re-runs after harness fixes (resume key has no
   harness-config dimension) — blocks a clean §2.1 re-run into the same file. → issue
3. **[MED]** Skill-derived rubrics make deltas self-referential — report framing rule:
   "Δ = doctrine-conformance". Documented here; carry into the W4 README.
4. **[MED]** Environment-contingent pass paths (Playwright/network) are neither controlled
   nor logged as preconditions. → issue (bundle with 5–7)
5. **[LOW]** Passing-trial workspaces destroyed → adversarial review must reconstruct from
   logs. Consider `--keep-workspaces` for campaign runs.
6. **[LOW]** Vision-dependent grader assertions (screenshot content) are unverifiable
   post-hoc — latent hallucination surface.
7. **[LOW]** User-config bleed: `--bare` skips plugin *sync* not *load* (handoff-w1 §8b);
   opencode side is fully isolated — asymmetric hermeticity.
8. **[LOW]** `make harness-eval` can't resolve agent candidates (flat `.md` under
   `primitives-core/agents/`); grid run used a staged temp dir (handoff-w3-scout).
9. **Candidate finding:** scout case at ceiling for sonnet-4-5 — needs harder traps or a
   weaker trial model to discriminate.

## 4 · What the battle-test proved about the harness itself

The grid did its job: one genuine cross-harness effect isolated (+1.0, same model, same
case), one self-caught methodology bug (§2.1) that single-harness eval would never have
surfaced, honest ceilings reported as zeros, and adversarial review reproduced every grade
it audited from primary evidence. Cross-harness + adversarial verification is the value.

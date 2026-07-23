---
name: tech-eval-research
description: Rigorous, cited, comparative evaluation of technology options — frameworks, infrastructure, serving layers, databases, libraries, SaaS-vs-self-hosted tools — producing a ranked shortlist, a capability comparison matrix, and a recommendation backed by primary sources. Use this whenever the user wants to compare, evaluate, choose, or shortlist technologies — "which X should we use", "evaluate these options", "is the free tier actually free" — and for license or paywall audits, self-hostability checks, open-source maturity assessments, build-vs-buy research, or vendor-neutral recommendations, even if the user never says "research" or "report". Especially valuable when license terms, free-tier boundaries, feature gating, or project health could decide the outcome.
---

# Technology Evaluation Research

Produce a decision-grade comparative evaluation of technology candidates: hard filters that eliminate, capability checklists resolved per-feature from primary sources, an operationalized maturity assessment, adversarial verification of the claims that decide the ranking, and a standard report with a comparison matrix and a recommendation.

The core insight this process is built on: **vendors put the paywall where the docs are vaguest**. Marketing pages name features; pricing pages gate them; only the LICENSE file, the docs, and the code tell the truth. So every verdict comes from primary sources, every claim that decides a ranking gets adversarially re-checked, and "exists" is never confused with "exists in the tier the user can actually use."

## Process overview

```
Phase 0  Scope the brief        (criteria, candidates, deliverable — with the user)
Phase 1  Parallel research      (subagents, primary sources only)
Phase 2  Adversarial verify     (try to refute the decision-critical claims)
Phase 3  Synthesize & rank      (filters eliminate, biases down-rank)
Phase 4  Deliver                (report always; deck on request)
```

Track phases in the task list. Phases 1 and 2 are subagent work; keep synthesis and ranking judgment in the main session. If subagents aren't available in the current environment, run the same phases sequentially inline — the source discipline and verification pass matter more than the parallelism. Scale effort to the question: a 4-candidate comparison may need 2 research passes and 4 verified claims, not 5 agents and 10.

## Phase 0 — Scope the brief

Establish these before any research. If the user's request already specifies them, extract and confirm; if not, propose defaults and ask only about the genuinely open decisions (deliverable format, scope boundaries, which criteria are hard filters vs. preferences).

1. **The decision question.** One sentence: "Which ___ should we adopt for ___?" If the user names a *category* (e.g., "agent frameworks"), check whether the real question is about an adjacent *layer* (e.g., the deployment/serving layer around the framework) — mislocating the layer is the most common way this kind of research answers the wrong question.
2. **Layer definition.** Write down exactly what the thing being evaluated must *do*, so wrong-layer candidates can be rejected with a reason instead of scored misleadingly.
3. **Hard filters vs. biases.** Hard filters eliminate (e.g., "must be OSI-licensed and self-hostable"); biases down-rank but don't disqualify (e.g., "prefer Python-first"). Label every criterion as one or the other and hold that line during ranking — most evaluation quality problems come from silently promoting a bias to a filter or vice versa.
4. **Capability checklist.** The features that must be resolved per-candidate. Each will be resolved to exactly one of: **Yes (free/OSS)** / **Paywalled** / **No** / **Not documented**. Define what counts as "Yes" for each (e.g., "streaming" might require reconnection semantics, not just a one-shot stream).
5. **Maturity bar.** How project health will be judged. Use the operationalized rubric in `references/default-rubric.md` §Maturity unless the user has their own.
6. **Candidate seed set.** List candidates to confirm-or-reject; instruct research agents to discover additions. Every seed candidate gets an explicit verdict — nothing silently dropped.
7. **Deliverable.** Default: markdown report per `references/report-template.md`. Deck only if requested (see Phase 4).

**Ready-made default rubric:** for evaluations of self-hostable / open-source infrastructure, `references/default-rubric.md` contains a complete, battle-tested set of hard filters (portability: self-host, OSI license, no license key, no phone-home, no usage restrictions), a capability-checklist pattern, and the maturity bar. Read it and adapt rather than inventing criteria from scratch — even for non-infra evaluations, its structure (filters/checklist/maturity, and the source-available license trap) transfers.

## Phase 1 — Parallel research

Fan out research subagents, each owning 2–3 candidates (grouping similar ones aids comparison). Add one agent for discovery + any baseline/comparison-point candidates. Launch all agents in a single message so they run concurrently.

Build each agent's prompt from `references/research-agent-prompt.md` — read it and fill the placeholders. The non-negotiables it encodes:

- **Primary sources only for facts**: the repo, the actual LICENSE file, official docs, pricing pages. Listicles and blog roundups may suggest candidates, never support claims.
- **Per-feature verification**: a feature on a marketing page but gated on the pricing page is **Paywalled**, not Yes. Judge the tier the user would actually use.
- **"Not documented" ≠ "No"**: absence of documentation is reported as Not documented; "No" requires the docs to state the limitation or the code to demonstrably lack it.
- **License discipline**: read the LICENSE file(s), per component (server vs SDK vs dashboard vs any `ee/` directory). Flag BSL/SSPL/Elastic/Commons-Clause as SOURCE-AVAILABLE with what they restrict, rather than silently failing them.
- **Phone-home check**: search docs/code for license keys, telemetry, usage reporting, update checks; note whether each is absent, opt-out, or mandatory.
- **Maturity with numbers**: stars, contributor counts and concentration, monthly activity, releases, backlog trend, downloads, named adopters — dated, so the verdict is reproducible.
- **Everything dated**: tier boundaries and activity are point-in-time. Every claim carries the date checked.

Agents return structured findings blocks; their final message is all you get, so the template tells them to include everything.

## Phase 2 — Adversarial verification

Before synthesizing, list the claims that *decide* the outcome — anything that flips a pass/fail verdict or reorders the top of the ranking (license identifications, paywall boundaries, "the free tier lacks X", capability presence for shortlist candidates). Typically 5–10 claims.

Spawn one verification subagent using `references/verification-agent-prompt.md`: it independently re-checks each claim from primary sources *trying to refute it*, and returns VERIFIED / REFUTED (with correction) / UNCERTAIN per claim. Apply corrections before writing anything, and note in the report that verification happened (e.g., "7/8 verified, 1 corrected").

Why this matters: research agents anchor on the first plausible source. The claims that eliminate a candidate or crown a winner deserve a second, hostile pass — in practice this catches roughly one meaningful error per evaluation.

## Phase 3 — Synthesize & rank

Ranking logic, in order:
1. **Hard filters eliminate.** Failed candidates go to the Rejected section with a one-sentence reason — never silently dropped, and source-available licenses get flagged as such rather than just "failed".
2. **Wrong-layer is a legitimate finding.** A strong project solving a different problem is rejected as wrong-layer, not scored low.
3. **Biases down-rank among survivors.** State when a candidate is penalized by a preference it technically survives (e.g., "meets the maturity floor, fails the contributor-breadth preference").
4. **Maturity verdicts need evidence.** Strong / Adequate / Early / At-risk, each with the underlying numbers — never a bare adjective. Star counts alone prove nothing; a 1k-star single-maintainer repo can be riskier than a 300-star vendor-backed one.
5. **State the bias.** The report says explicitly which axes were weighted (e.g., "license purity above vendor support") so the reader can discount for their own priorities.

## Phase 4 — Deliver

Write the report following `references/report-template.md` (executive summary ≤200 words → comparison matrix with legend → shortlist profiles → rejected list → recommendation with risks → sources grouped by candidate, dated). Save it to the user's folder and present it.

If a deck is requested: recommendation-first structure — title, then **the single recommended option with rationale as the first content slide**, then context/method/results/matrix/profiles/risks. Follow the pptx skill for construction, and have the deck visually QA'd (render slides to images and inspect) before delivery.

## Anti-patterns (each of these has ruined real evaluations)

- **Listicle laundering** — "it's on a top-N list" treated as feature evidence.
- **Marketing-tier confusion** — scoring a feature Yes when it only exists in the paid cloud.
- **Maturity-by-stars** — popularity standing in for the health signals that actually predict abandonment.
- **Silent absence** — asserting "No" when the truth is "the docs don't say".
- **Layer conflation** — crediting the serving layer with capabilities that belong to the library inside it (or vice versa). Tag every candidate with the layer it operates at.
- **Seed-set laundering** — quietly dropping a candidate the user named instead of rejecting it with a reason.

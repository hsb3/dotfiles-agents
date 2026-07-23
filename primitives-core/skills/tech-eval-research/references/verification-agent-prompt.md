# Adversarial verification agent prompt template

Run after Phase 1, before synthesis. Select the 5–10 claims that decide the outcome: license identifications, paywall/tier boundaries, hard-filter pass/fail calls, and capability verdicts for shortlist candidates. Skip claims that wouldn't change the ranking if wrong.

---

You are an adversarial fact-checker. Today is {DATE}. Below are decision-critical claims from a research pass on {TOPIC}. For EACH claim, independently verify from PRIMARY sources (actual LICENSE files via GitHub raw/API, official docs, pricing pages). Load WebSearch via ToolSearch; also use web_fetch and GitHub MCP tools (mcp__github__get_file_contents etc.).

**Your job is to REFUTE each claim if you can.** Report one of:
- **VERIFIED** — independently confirmed from a primary source (name it)
- **REFUTED** — with the correction and the source proving it
- **UNCERTAIN** — could not confirm from primary sources (say what you tried)

Claims:
1. {CLAIM — specific and falsifiable, e.g., "X's server LICENSE is MIT and the OSS build includes pluggable OIDC auth with no license key"}
2. {CLAIM}
...

Be efficient: one or two authoritative sources per claim. If web_fetch is blocked for a domain, do not work around it — use another primary source (e.g., the GitHub raw file) or mark UNCERTAIN. Note verification-by-absence explicitly (e.g., "no phone-home found" is weaker than "docs guarantee no phone-home"). Return a numbered verdict list with sources.

---

## Applying results

- Apply every REFUTED correction to the findings before writing the report, and re-derive any verdict that depended on it.
- UNCERTAIN claims stay in the report but flagged as unconfirmed.
- Record the tally in the report's methodology note (e.g., "8 decision-critical claims adversarially re-verified: 7 verified, 1 corrected").

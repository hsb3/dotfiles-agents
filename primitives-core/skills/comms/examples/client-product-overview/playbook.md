_Client product overview playbook. Shared machinery: `references/comm-package-standard.md`. No worked sample yet - drafted from first principles + the advisor deck's layout patterns + the readme-value-and-proof discipline._

# Client product overview

As-needed (sales / onboarding), audience a prospective or onboarding client - a plan's actuary,
CFO, or IT lead. **The one job: what they get, and why it is trustworthy enough to hand us their
CMS files.** Toolchain pptx-henry; theme `actuarial-signal` (or a client-safe token theme - decide
per client); `.pptx` + `.pdf` with a confidential + client-name footer. Folder slug
`-client-overview`.

> Assumptions to confirm with the owner: as-needed cadence; pptx-henry; theme + audio per engagement.
> No prior instance exists - ships without a `sample.*`; the advisor `sample.deck.js` next door is
> the closest layout reference. Invoke the `pptx-henry` skill for palette/tokens/QA, and the
> `readme-value-and-proof` skill to capture real app screenshots for the "what it looks like" slide.

## The one rule

**Benefit-led, not feature-led; proof over promise.** Frame everything as the client's own problem
and what they receive. No internal jargon, no issue/PR numbers, no roadmap dates, no engineering
arcs. Honest about scope - what is proven (e.g. "proven on synthetic and first clients") and what
is not yet, never rounding up; this is a trust sale and overclaiming kills it. Confidential +
client-name footer.

## Deck structure (the endorsed order)

~8-10 slides. Pitched to the buyer, not the builder.

| # | Slide | Content |
| --- | --- | --- |
| 1 | Title | "Know exactly what CMS pays you" - the product in one sentence, addressed to the client |
| 2 | The problem, in your terms | You cannot independently verify CMS payment; dollars leak in the gaps and expire on a regulatory clock |
| 3 | What you get | The payment-integrity scan: a verdict report, dollar-tagged findings, member-month granularity |
| 4 | How it works | Ingest your CMS file set to recompute to reconcile to per-member-month verdicts; evidence-grade |
| 5 | What it looks like | Real screenshots of the report / a sample finding (readme-value-and-proof capture), not mockups |
| 6 | Trust & security | Byte-verified ingestion with citations; tenant isolation; desktop install for IT-constrained plans; PHI posture |
| 7 | How we engage | Scan (the wedge - free or cheap to start) to recovery to ongoing support; urgency is CMS's clock, not ours |
| 8 | Onboarding | What we need from you (file set, paperwork), what happens, as ordered steps - not dated |
| 9 | Why us (optional) | Founder edge: credentialed actuary, built actuarial dept + data warehouse; peer-to-peer sale |
| 10 | Next step | One clear call to action - the first month of files for a scan |

Drop slide 9 when the relationship is warm; merge 7/8 for a short overview.

## Gather

- Product claims from the project charter and product thesis - phrased in client benefit terms,
  not internal architecture.
- Real surfaces for slide 5: capture from the running app via `readme-value-and-proof`; if a
  feature isn't real yet, do not show it - say "in build" or omit.
- The client's specifics (plan type, file set they have, their IT constraint) shape slides 2, 6,
  8 - tailor per engagement; the footer carries their name.
- Scope honesty: confirm what is proven for THIS client's situation before the deck claims it.

## Voice deltas (beyond the baseline)

- Second person ("you get", "your files"); benefit before mechanism.
- Zero internal jargon, issue numbers, or roadmap dates; nothing a competitor-as-reader gains.
- Trust framing is the spine of slides 4-6: evidence-grade, cites sources, isolated, honest about
  scope. Overclaiming is the failure mode this comm guards hardest against.
- Confidential + client-name footer on every content slide.

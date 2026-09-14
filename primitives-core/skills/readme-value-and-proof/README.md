# readme-value-and-proof

Turn a README into a user-centric pitch backed by real visual proof. Two halves, both of
which must be true: an honest pitch about what a willing user gets, and screenshots captured
from the actually-running app.

## When it triggers

Use it when asked to write or refresh a README with a value proposition, capture app
screenshots for docs, add "visual proof" of a UI or feature, or explain "what someone gets"
from a project.

## What it enforces

**Honest, not hype.** The pitch names what is near-turnkey *and* what the project is not yet
— gaps, untested areas, who it is not for. Phrases like "production-ready" and "seamless" are
out; a clear-eyed pitch earns more trust than a glossy one.

**Proof must be real.** Every screenshot shows the feature working, captured from a running
stack — never a mockup, never a staged shot. Capture is driven with Playwright from the skill's
own snippet; it needs no machine-local helper. If a dependency is down or a feature errors
during capture, the skill's rule is to investigate, fix or document it, and recapture. A
capture run that surfaces a real bug is a feature of the process, not a detour.

**Verify before committing.** Image paths must resolve and the README must read top-to-bottom
for its target audience.

**Capture against synthetic data, not a live account.** Screenshots come from seeded,
realistic-looking content, never a live account's real user or client data — and every image
gets read before committing for leaked tokens or identifiers (names, emails, org slugs, API
keys) visible in a URL bar, DevTools, or a notification.

## Structure it produces

Why this exists (the problem) · What you get today (the honest value prop, including what it
is *not* yet) · Roadmap (linked to the live tracker, not duplicated). Detail that balloons the
README gets pushed to `docs/` and linked.

## Install

```
claude plugin install code-desk@dotfiles-agents
```

Ships in the `code-desk` bundle.

---
name: readme-value-and-proof
description: Turn a README into a user-centric pitch backed by real visual proof. Use when asked to write/refresh a README with a value proposition, capture app screenshots for docs, add "visual proof" of a UI/feature, or explain "what someone gets" from a project. Captures live screenshots from the running app (not mockups), writes an honest motivation + value prop + roadmap, and embeds the shots.
license: MIT
metadata:
  category: documentation
  requires_sandbox: "false"
---

# README: value proposition + visual proof

Make a README that (1) tells a willing user *why this exists, what they get, and
what it is not yet*, and (2) **proves** the working parts with screenshots
captured from the actually-running app. Two halves: the honest pitch, and the
real proof. Both must be true.

## Core principles (don't skip)

- **Honest, not hype.** State what's near-turnkey AND what it is *not* yet
  (gaps, maturity, "scaffolded vs delivered"). Avoid "production-ready",
  "seamless", "blazing-fast", "MISSION ACCOMPLISHED", and similar. A clear-eyed
  pitch builds more trust than a glossy one.
- **Proof must be real.** Every screenshot shows the feature *actually working*,
  captured from a running stack — never a mockup, never a staged/edited shot. If
  a dependency is down or a feature errors during capture, **investigate, fix or
  document it, and recapture** — do not ship a misleading image. (A capture run
  that surfaces a real bug is a feature of this process, not a detour.)
- **Verify before you commit.** Confirm image paths resolve and the README reads
  top-to-bottom for the target audience.
- **Capture against synthetic data, not a live account.** A committed screenshot ships
  whatever was on screen into a usually-public README. "Real data over lorem ipsum"
  means *realistic-looking* — seeded/synthetic content that reads as genuine — never a
  live account's actual user/client content. Before committing, read every screenshot
  for leaked tokens/identifiers too (Part B step 4).

## Part A — the value proposition

1. **Figure out who benefits and what they get.** Ask: who is the willing user?
   What's the single most valuable outcome? What's *near-turnkey* vs. a
   head-start vs. a gap? Read the code/docs; don't guess.
2. Write these sections (adapt headings to the project):
   - **Why this exists** — the problem/motivation in a few sentences. What does
     everyone re-derive or get wrong that this solves?
   - **What you get today** — the honest value prop: the near-turnkey win, any
     standout unlock, the working reference — *and* a plain "what it is not (yet)"
     paragraph (gaps, untested areas, who it's not for).
   - **Roadmap** — planned enhancements as bullets; link the live tracker (issue,
     project board) if one exists rather than duplicating it.
3. Keep each section tight. If the README balloons, push detail to `docs/` and
   link it. (A value-prop/proof README will run longer than a bare one — that's
   fine when the user asked for this context.)

## Part B — visual proof (screenshots from the running app)

1. **Stand up the real app.** Find the run command (project skill, `make`,
   `npm run dev`, `docker compose up`, a dev server). Note required env/keys/
   services. Put secrets only in gitignored `.env` files; never commit them.
2. **Drive it to meaningful states** worth showing: the entry/empty state, a core
   feature mid-use, a standout/edge feature. Prefer realistic seeded/synthetic data
   over lorem ipsum — not a live account's real content.
3. **Capture with headless Chromium (Playwright).** A self-contained script that
   logs console errors (0 errors = clean proof) and screenshots full-page at a
   fixed viewport. Gotchas that bite:
   - Resolve `playwright` by **absolute path** and import it as **CommonJS**
     (ESM ignores `NODE_PATH`): `npm i -g playwright`, then in an `.mjs`:
     ```js
     import pkg from '<global-node-modules>/playwright/index.js'; // `npm root -g`
     const { chromium } = pkg;
     const b = await chromium.launch();
     const p = await b.newPage({ viewport: { width: 1440, height: 900 } });
     const errs = [];
     p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
     p.on('pageerror', e => errs.push('PAGEERR: ' + e.message));
     await p.goto(url, { waitUntil: 'networkidle', timeout: 45000 });
     // interact: getByPlaceholder/getByRole/getByText (these pierce shadow DOM)
     // type a message, press Enter, then WAIT generously for async/LLM/streaming
     await p.waitForTimeout(/* 20–90s for model/tool round-trips */ 5000);
     await p.screenshot({ path: out, fullPage: true });
     console.log('console_errors:', errs.length);
     await b.close();
     ```
   - For interactive proof, drive the UI (click, type, submit) then **wait long
     enough** for the result — LLM/tool/streaming replies can take 30–90s. Too
     short a wait captures a half-rendered or empty state.
   - Shadow-DOM apps (e.g. web components): Playwright's `getByText` /
     `getByRole` / `getByPlaceholder` pierce shadow roots; raw CSS selectors often
     don't. Body `innerText` won't include shadow content — judge from the image.
4. **Look at every screenshot** before using it. Confirm it shows the feature
   working and nothing is broken/misleading (placeholder labels, error states,
   empty panels). Drop or recapture bad ones; file/fix real bugs you find.
   **Before committing, read each image for leaked tokens or identifiers** —
   names, emails, client names, org slugs, API keys/session ids visible in a
   URL bar, DevTools, or a notification.
5. **Save committed** to `docs/images/` (or `.github/assets/`), reference with
   `![alt](docs/images/x.png)`, and verify every ref resolves:
   `grep -oE 'docs/images/[^)]+' README.md | while read p; do [ -f "$p" ] && echo OK $p || echo MISSING $p; done`
6. **Tear down** the app and any throwaway services. Scrub/rotate any keys used —
   including any that turn up in the leak check on step 4.

## Output checklist

- [ ] Motivation, honest "what you get / what it's not", and roadmap present.
- [ ] No hyperbole; the limits are stated plainly.
- [ ] Screenshots captured from the *running* app, each verified to show real
      working behavior; misleading ones dropped and any bugs filed/fixed.
- [ ] Images committed, refs resolve, README reads cleanly end-to-end.
- [ ] No secrets committed; app and temp services torn down.
- [ ] No real user/client data visible in any committed screenshot.

Done when every checklist row above is checked, not asserted.

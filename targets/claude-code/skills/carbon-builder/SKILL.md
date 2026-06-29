---
name: carbon-builder
description: >
  Expert Carbon Design System (IBM) builder for React and Web Components — no MCP
  server required. Sequences ALL UI work with Brad Frost's Atomic Design ontology
  (design tokens → atoms → molecules → organisms → templates → pages) mapped onto
  Carbon, building bottom-up and freezing each stage. Use for ANY UI work in a
  Carbon project: building screens or components with @carbon/react /
  @carbon/web-components / @carbon/ibm-products, choosing design tokens or themes,
  Carbon Grid layout, icons and pictograms, Carbon Charts, AI Chat integration,
  IBM Plex typography, accessibility, or reviewing existing Carbon UI for drift
  and fluff. Enforces compose-don't-style, atomic build order, and
  verify-against-the-installed-package instead of guessing imports, props, or
  icon names from memory.
license: Apache-2.0
---

# Carbon Builder

## Mission — two disciplines, one skill

This skill fuses a **build method** with a **parts catalog**:

1. **Atomic Design (Brad Frost, 2013) supplies the sequence.** Atoms →
   molecules → organisms → templates → pages, assembled bottom-up over a
   design-token foundation. Each stage is frozen before the next begins, so
   errors can't compound — every step starts from a working base and makes one
   bounded addition.
2. **Carbon Design System supplies the parts.** Carbon ships pre-styled
   components and a complete theme-aware token system, so your job at every
   atomic stage is **selection and assembly, never invention**. You compose
   with Carbon; you do not style it.

Both disciplines serve one goal: **no vibe-coded UI.** The failure mode this
skill exists to prevent is the generic AI-generated look — gradients and
glassmorphism, decorative icons and emoji, hero sections on internal tools,
filler stat cards, a new accent color per screen, hand-rolled components that
shadow Carbon ones. Every invented value is drift away from the system; the
system's entire value is coherence. If Carbon doesn't cover something, **stop
and ask** — don't fill the gap with an invented value.

Planning (spec/plan/tasks) happens upstream. This skill governs how UI gets
built once a task is scoped.

---

## Verification Rule (replaces the MCP server — Hard Rule)

This skill was adapted from an MCP-backed original. Without the server, the
ground truth moves to the project's installed packages and the public docs.
**Never generate Carbon code from training memory alone** — it is stale on
props, imports, icon export names, and component existence.

**Before writing any import for a Carbon icon, pictogram, or less-common
component, verify it exists and get the exact export name:**

```bash
# Icons (React) — find the real export name; never assume it
node -e "console.log(Object.keys(require('@carbon/icons-react')).filter(n => /comment/i.test(n)))"
# → [ 'AddComment' ]   ← use this exact name

# Icons (Web Components) — confirm the module path exists
ls node_modules/@carbon/icons/es/ | grep -i comment

# Components — confirm export exists in the installed version
node -e "console.log(Object.keys(require('@carbon/react')).filter(n => /indicator/i.test(n)))"
```

Icon export names are genuinely unpredictable: slugs use `--` for variants and
words flatten to PascalCase (`add-comment` → `AddComment`, `chart--win-loss` →
`ChartWinLoss`), and many intuitive names simply don't exist (`CreditCard`,
`SatisfiedFace`). If a name can't be confirmed, say so — never ship a guessed
import.

For props, docs, and anything local inspection can't answer, see
[references/verification.md](references/verification.md) — it maps every
lookup (component examples, props, usage docs, accessibility guidance, charts,
AI Chat) to a node_modules check or a docs URL from
[references/llms.txt](references/llms.txt).

---

## The Atomic Build Order

Frost's insight is chemistry: atoms have little meaning alone; value emerges
through composition, and the composite is only as sound as what it's built
from. So build in this order, and let a stage reference **only the stages
below it**. Once a stage is "frozen," later work treats it as read-only — if a
higher stage needs something a frozen stage lacks, **drop back down, add it
there, re-freeze** — never inline a one-off at the higher stage.

| # | Stage | Carbon mapping | What you produce | Freeze gate before next stage |
|---|-------|----------------|------------------|-------------------------------|
| 0 | **Design tokens** (sub-atomic) | Active theme (White/g10/g90/g100) + semantic tokens | Theme choice; any project-tier token aliases | No raw palette values anywhere. Project tokens alias Carbon semantic tokens only. |
| 1 | **Atoms** | Carbon primitives — Button, TextInput, Tag, Tile, ... | The set of Carbon components in use, **unmodified** | Zero restyled Carbon components. No custom CSS on Carbon parts. |
| 2 | **Molecules** | Simple assemblies of atoms that do one thing together | Form row, labeled metric readout, search-with-button, record summary | Only atoms + tokens used. Still generic and reusable — no business logic baked in. |
| 3 | **Organisms** | Carbon ships many complete (DataTable + toolbar, Modal, Tabs, UI Shell Header/SideNav) — never reassemble those; build only your domain sections | Table-with-toolbar region, filter panel, page header group, nav | Built from molecules/atoms only. No new atoms invented. No Carbon-shipped organism duplicated. |
| 4 | **Templates** | UI Shell + Grid skeleton + state patterns | Content-agnostic page skeleton: shell, grid regions, **empty/loading/error states** | Arranges organisms only. Every screen-state defined (loading → skeletons, empty → explicit, error → notification). |
| 5 | **Pages** | Template + real data | Real screens wired to data | Nothing visual invented here — this stage is plumbing. Real-content stress test passes (below). |

**Pages are where the system meets reality** — Frost's point is that real
content is the test of the design system, not an afterthought. At stage 5,
deliberately exercise: long names that wrap or truncate, empty tables, zero
and many-item states, error responses. If real content breaks a template,
the fix happens at the template (or lower) — not as a page-level patch.

The component inventory mapped to these stages — and the "does Carbon already
have this?" check that precedes building *anything* — is
[references/components.md](references/components.md). Consult it before
creating any component.

---

## Stage 0 — Token discipline

Carbon is already three-tier. Stay in the semantic tier.

- **Primitive (palette)** — `$blue-60`, `$gray-90`, etc. **Forbidden to reference directly.**
- **Semantic (theme tokens)** — your working vocabulary: surfaces/layers
  (`$background`, `$layer-01..03`, `$field-01/02`), text (`$text-primary`,
  `$text-secondary`, ...), interactive (`$interactive`, `$link-primary`,
  `$focus`, `$border-*`), status (`$support-error/success/warning/info`).
- **Component** — `button.$button-primary` etc., opt-in via
  `@use '@carbon/styles/scss/components/button'`.
- **Project tier** (the only tokens you may add) — only for things Carbon
  genuinely doesn't cover, defined as **aliases of Carbon semantic tokens**,
  never raw values:

```scss
$app-metric-positive: theme.$support-success; // good — alias
$app-metric-positive: #24a148;                // forbidden — raw value
```

### The layering model

Four layers per theme stack in fixed order: base, 01, 02, 03. A component on
layer N uses that layer's token set. For reusable molecules/organisms that
must work on any layer, use **contextual tokens** and wrap in `<Layer>` — it
auto-maps to the correct layer (nests up to 3 deep). Default (unwrapped) =
layer 01.

```jsx
import { Layer, Tile } from '@carbon/react';
<Tile>
  <Layer><Tile>Nested content picks up the next layer automatically</Tile></Layer>
</Tile>
```

Full token tables (surfaces, borders, text, type, spacing, theme selection):
[references/tokens.md](references/tokens.md) — **consult before choosing any
token; do not guess token names.**

### Spacing, type, grid — use the scales, nothing else

- **Spacing**: `$spacing-01`..`$spacing-13` only. No arbitrary px/rem margins or padding.
- **Type**: `$body-01/02`, `$heading-01`..`$heading-07`, `$label-01`,
  `$helper-text-01`, `$code-01`. No custom font-size/line-height. Font is IBM
  Plex — delivered by the SCSS pipeline for React; IBM CDN only otherwise
  (never Google Fonts).
- **Layout**: the Carbon 2x grid via `Grid`/`Column`. No bespoke flex/grid
  scaffolding for page layout.

**Grid is mandatory for all templates/pages**: separate `Grid` per logical
content group, column spans for ALL breakpoints (`sm`/`md`/`lg`), correct
variant (default 32px / narrow 16px / condensed 0px gutters), `row-gap`
matched to the gutter when content wraps. Read
[references/grid-system.md](references/grid-system.md) **whenever implementing
page layout or analyzing a design image for grid structure.**

---

## Hard Constraints — the anti-vibe-coding rules

Each of these blocks a specific flavor of generic, off-system output:

- No gradients, glassmorphism, `backdrop-blur`, or custom shadows. Carbon's
  elevation only, and only where a Carbon component calls for it.
- No emoji in UI. No decorative icons. Icons must be `@carbon/icons-react`
  (or `@carbon/icons` for Web Components), verified to exist, and load-bearing.
- No hero sections, marketing copy, filler stat cards, or "dashboard" padding
  on internal tools. Build what the task names, nothing adjacent.
- No animation beyond Carbon's built-in states + `@carbon/motion` tokens.
- One Carbon component per need — if Carbon has `DataTable`, you do not build
  a table. Check [references/components.md](references/components.md) first.
- Tables and structured forms over cards for data-dense views.
- Max one accent beyond the theme's interactive color per screen.
- **No inline styles in JSX/TSX.** All styling lives in SCSS/CSS using Carbon
  tokens, applied via `className`. Exception: truly dynamic values (user-driven
  dimensions, animation transforms).

---

## Framework Rule (Critical)

- Default to **React** unless the user specifies Web Components.
- **Never mix** React and Web Components in a single response. Import lines
  are the tell: `import { html } from 'lit'` ⇒ Web Components; component
  imports from `@carbon/react` ⇒ React.
- React SCSS baseline: `@use '@carbon/react';` in the project SCSS file is
  **required** — without it every component renders unstyled. Token imports
  (`spacing`, `theme`, `type`, `breakpoint`) are optional, only if custom SCSS
  uses them. Never `@carbon/styles/css/styles.css` for React.
- Web Components: minimal SCSS baseline first (`reset` + `type`); SCSS
  variables are **compile-time only** — runtime styles use
  `var(--cds-*)` custom properties; grid via `cds--grid`/`cds--row`/`cds--col-*`
  CSS classes (`<cds-row>` does not exist).

Full setup recipes, Modal/Dropdown composition gotchas (`onRequestClose`,
`autoAlign`, `data-modal-primary-focus`), Tag-vs-StatusIndicator and
Tabs-orientation selection rules:
[references/framework-setup.md](references/framework-setup.md) — **read when
setting up styles, composing floating UI inside a Modal, or choosing between
similar components.**

---

## Implementation Guardrails (digest)

1. **Stability** — no `@carbon/labs-react` or preview components unless asked
   or already in the repo.
2. **IBM Products (React)** — SCSS (`@use '@carbon/styles';` then
   `@use '@carbon/ibm-products/scss/index';`, order mandatory) **or** prebuilt
   CSS in the JS entry — never mix. Silently-failing components need
   `pkg.component.X = true`. Web Components use the separate
   `@carbon/ibm-products-web-components` package.
3. **CDN** — IBM CDN only (`1.www.s81c.com`). Never Google Fonts, jsDelivr, unpkg.
4. **Styling discipline** — never target `.bx--`/`.cds--` internals without
   explicit user confirmation; don't force `<Theme>` wrappers when the host app
   already provides theme context.
5. **Layout** — modals, side panels, tooltips, toasts stay outside Grid flow.
   Content under a fixed `Header` goes in `<Content>` — never a hardcoded
   `margin-top`. `<Layer>`: nesting sets the level, never the `level` prop;
   `withBackground` for visible backgrounds.
6. **Composition** — Breadcrumb current item: `isCurrentPage`, no `href`.
   Icon-only controls need `iconDescription`. Status = `IconIndicator`/
   `ShapeIndicator` with `kind` prop, never colored Tags — and lifecycle/
   health/outcome words (*active, expired, failed, pending, degraded, ...*)
   are **always** status, never "classification"; don't reason around it.
7. **AI Chat / SSR** — detect SSR first; client-only loading + `ssr.external`
   when present; never import `@carbon/ai-chat/es/index.css`.
8. **Accessibility** — WCAG 2.2 AA applied inline while generating. Read
   [references/accessibility-rules.md](references/accessibility-rules.md)
   **when generating form components, Modals, custom interactive HTML, or
   custom CSS** — it lists the props that are optional in TypeScript but
   mandatory for accessible output (`labelText`, `iconDescription`, ...).

Full detail: [references/implementation-guardrails.md](references/implementation-guardrails.md).
Symptom-indexed fixes: [references/common-pitfalls.md](references/common-pitfalls.md).

---

## Carbon Charts

Use `@carbon/charts-react` for **all** data viz — never hand-rolled SVG/D3,
never a second chart library (it breaks theme coherence instantly). Chart
styles are imported **once in the app entry module, never in SCSS**. Charts
have their own theming layer that does not auto-follow the page theme — treat
palette/background matching as its own task. Setup, data/options model, and
where to verify options for the installed version:
[references/charts.md](references/charts.md) — **read for any chart request.**

---

## Verify Gate (run before declaring a stage frozen)

Check the work as a **separate pass** — the building pass does not
self-certify. Reject and drop back a stage if any of these fail:

1. Grep the diff for raw hex/rgb, hardcoded px in margin/padding/font-size,
   and `style=` props on Carbon components. Any hit = fail.
2. Every surface uses a layer/background token; layering tokens match actual
   nesting depth.
3. No component duplicates an existing Carbon atom or organism.
4. Every icon and uncommon component import was verified against the installed
   package (Verification Rule above) — no guessed names.
5. Accessibility props present: `labelText` on every input, `iconDescription`
   on icon-only buttons, no `div onClick` without role + keyboard handler.
6. Nothing added that the scoped task didn't ask for (fluff check).
7. The stage references only stages below it (no upward or sideways deps).
8. **At the pages stage only**: real-content stress test — long/wrapping
   strings, empty collections, zero/many states, error responses all render
   acceptably; failures are fixed at the responsible lower stage.

---

## Output Discipline

- Don't write extra files — no tests, no READMEs — unless requested.
- Stop after emitting the requested files.
- For Web Components, add one short setup confirmation only: framework, SCSS
  mode (minimal/grid/theme), entry-module style import.

---

## Reference Files (load on demand)

| File | Read when |
|------|-----------|
| [references/tokens.md](references/tokens.md) | Before choosing **any** token — color, spacing, type, layer sets, themes |
| [references/components.md](references/components.md) | Before building any component — the Carbon inventory mapped to the atomic stages, plus the "does Carbon already have this?" check |
| [references/verification.md](references/verification.md) | Before any icon/uncommon-component import; when you need props, usage docs, or examples you'd otherwise guess |
| [references/framework-setup.md](references/framework-setup.md) | Setting up React SCSS or WC styling; Modal composition; Tag vs status indicator; Tabs orientation |
| [references/implementation-guardrails.md](references/implementation-guardrails.md) | IBM Products setup, theme config, SSR/AI Chat, CDN rules, Layer system, image-driven UI workflow |
| [references/grid-system.md](references/grid-system.md) | Always, when implementing page layouts or responsive designs |
| [references/accessibility-rules.md](references/accessibility-rules.md) | Forms, Modals, custom interactive HTML, custom CSS, or explicit a11y asks |
| [references/charts.md](references/charts.md) | Any Carbon Charts request |
| [references/common-pitfalls.md](references/common-pitfalls.md) | SCSS, CDN, WC styling, or UIShell errors — symptom-indexed fixes |
| [references/llms.txt](references/llms.txt) | URL map to official docs, Storybooks, and source repos — for web lookups |

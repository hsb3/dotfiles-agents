# Verification — ground truth without the MCP server

The original version of this skill called an MCP server (`code_search`,
`docs_search`, `get_charts`) for every component, icon, doc, and chart lookup.
Without it, the same rule holds — **never generate, modify, or diagnose Carbon
code from training knowledge alone** — but the sources change:

| Priority | Source | Why |
|----------|--------|-----|
| 1 | `node_modules/@carbon/*` in the project | The installed version is the only truth for *this* project — exports, types, style paths |
| 2 | Official docs / Storybook (URLs in [llms.txt](llms.txt)) | Usage guidance, variants, a11y notes, live examples |
| 3 | GitHub source repos (URLs in [llms.txt](llms.txt)) | When docs are thin — read the component source or stories directly |

If neither local inspection nor docs can confirm something, **tell the user**
— do not fall back to a guess.

---

## Check the installed version first

Carbon v10 and v11 differ materially (`.bx--` vs `.cds--` prefixes, style
paths, props). Pin every lookup to what's actually installed:

```bash
node -e "console.log(require('@carbon/react/package.json').version)"
ls node_modules/@carbon | cat        # which Carbon packages are present at all
```

If `@carbon/react` is missing but the task is React UI, add the dependency —
don't hand-build a clone (see implementation-guardrails.md).

---

## Icons and pictograms (Hard Rule — verify every name)

Export names cannot be derived from the visual name. Slugs use `--` for
variants, words flatten to PascalCase, and many intuitive names don't exist.

Verified examples of the mapping:

| Slug | React export |
|------|--------------|
| `add-comment` | `AddComment` |
| `arrows--horizontal` | `ArrowsHorizontal` |
| `chart--win-loss` | `ChartWinLoss` |
| `face--satisfied--filled` | `FaceSatisfiedFilled` |
| `airline--manage-gates` | `AirlineManageGates` |

Known traps: `CreditCard`, `SatisfiedFace`, `WinLossChart` — none exist.

**React** — search the installed package by keyword, use the exact name returned:

```bash
node -e "console.log(Object.keys(require('@carbon/icons-react')).filter(n => /satisf/i.test(n)))"
# → [ 'FaceSatisfied', 'FaceSatisfiedFilled' ]
```

```jsx
import { FaceSatisfiedFilled } from '@carbon/icons-react';
```

**Web Components** — icons are default exports from per-icon ES modules in
`@carbon/icons`; confirm the directory exists and pick a size:

```bash
ls node_modules/@carbon/icons/es/ | grep -i comment   # find the slug → add-comment
ls node_modules/@carbon/icons/es/add-comment/         # available sizes → 16.js 20.js 24.js 32.js
```

```js
import AddComment from '@carbon/icons/es/add-comment/20.js';
```

Never type a slug from memory — `add-comment` uses one hyphen while
`chart--win-loss` uses two; the `ls` is the only way to know.

**Pictograms** — same pattern with `@carbon/pictograms-react` /
`@carbon/pictograms`.

If the package isn't installed locally, verify against the icon library page
or the icons package source on GitHub (links in [llms.txt](llms.txt)) before
writing the import.

---

## Components — existence and exports

```bash
# Does this component exist in the installed version, and under what name?
node -e "console.log(Object.keys(require('@carbon/react')).filter(n => /tab/i.test(n)))"
# → Tabs, TabList, TabsVertical, TabListVertical, Tab, TabPanel, TabPanels, ...
```

Also reveals preview/unstable exports (`preview__IconIndicator`,
`unstable__*`) — see the stability guardrail before using those.

For IBM Products: same check against `@carbon/ibm-products`. Keep imports
separated — Carbon Core from `@carbon/react`, IBM Products from
`@carbon/ibm-products`; never mix them in one import line.

---

## Props and component APIs

1. **Type definitions in the installed package** (authoritative for the
   installed version):

```bash
ls node_modules/@carbon/react/lib/components/ | grep -i modal
# then read the component's .d.ts / PropTypes in that directory
```

If the layout differs in your version, grep for the component name under
`node_modules/@carbon/react/lib/`.

2. **Storybook** — `https://react.carbondesignsystem.com/` documents every
   prop with controls, plus all variants. Fetch the component's docs page when
   types alone don't explain usage.

3. **Component source / stories on GitHub** — the `*.stories.js` files in the
   monorepo are complete, runnable usage examples (repo links in
   [llms.txt](llms.txt)).

---

## Usage, style, and accessibility docs

`https://carbondesignsystem.com/components/<slug>/usage/` (also `/style/`,
`/accessibility/`, `/code/`). The full per-component URL list is in
[llms.txt](llms.txt). Fetch these for design guidance — when to use which
variant, content rules, a11y behavior — rather than reciting from memory.

### DataTable specifically

Generate DataTable code from first principles using the documented
sub-components — `TableContainer`, `Table`, `TableHead`, `TableRow`,
`TableHeader`, `TableBody`, `TableCell` from `@carbon/react` — and verify
against the docs `/code/` page and Storybook. It is the component most worth
double-checking: its render-prop API (`<DataTable rows={...} headers={...}>
{({ rows, headers, getTableProps, ... }) => ...}</DataTable>`) has version-
specific details.

---

## Carbon Charts

See [charts.md](charts.md). Verification path: installed
`@carbon/charts-react` / `@carbon/charts` packages for exports and the styles
file; `https://charts.carbondesignsystem.com/` Storybook for every chart
type's live data/options examples.

---

## AI Chat

Docs: `https://chat.carbondesignsystem.com/tag/latest/docs/documents/Overview.html`.
Complete runnable examples (the authoritative file sets — fetch the whole
example, not fragments):
`https://github.com/carbon-design-system/carbon-ai-chat/tree/main/examples` —
roots: `basic`, `custom-element`, `history`, `watsonx`, `watch-state`, each in
React and Web Components flavors. Build-safety rules (SSR detection,
client-only loading) are in
[implementation-guardrails.md](implementation-guardrails.md).

---

## When results conflict

- Installed package beats docs site (docs track latest; your project may not).
- Docs site beats memory, always.
- Two frameworks never mix: discard any example whose framework doesn't match
  the task before reasoning from it.

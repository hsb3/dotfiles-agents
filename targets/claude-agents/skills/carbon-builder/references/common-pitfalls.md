# Common Pitfalls

## React SCSS Setup

### 1) Using the CSS file instead of SCSS tokens

```js
// ❌ Wrong — bypasses SCSS token resolution
import '@carbon/styles/css/styles.css';
```

### 2) Missing `@use '@carbon/react'` — components render unstyled

`@use '@carbon/react'` generates the actual component styles. Without it, all
Carbon components render completely unstyled. Token imports (`spacing`,
`theme`, `type`, `breakpoint`) emit **no compiled CSS** — they only declare
variables/mixins for your own SCSS.

```scss
/* ❌ Wrong — token imports only; every component unstyled */
@use '@carbon/react/scss/spacing' as *;
@use '@carbon/react/scss/theme' as *;
```

```scss
/* ✅ Correct — minimum required */
@use '@carbon/react';
```

### 3) Including unnecessary token imports

Token imports are **optional** — only add the ones your custom SCSS actually
uses. Components-only projects need none.

### 4) Missing app-entry SCSS import

```js
// ✅ Correct: import SCSS before component imports
import './styles.scss';
import { Button } from '@carbon/react';
```

### 5) Using an unverified icon name

```jsx
// ❌ Wrong — never assume an icon export name from memory
import { CreditCard } from '@carbon/icons-react'; // does not exist
import { WinLossChart } from '@carbon/icons-react'; // wrong — actual name is ChartWinLoss
import { SatisfiedFace } from '@carbon/icons-react'; // wrong — actual name is FaceSatisfiedFilled
```

```jsx
// ✅ Correct — verified against the installed package first
import { ChartWinLoss } from '@carbon/icons-react';
import { FaceSatisfiedFilled } from '@carbon/icons-react';
```

Verify with a keyword search over the installed package's exports (see
[verification.md](verification.md)) and use the exact name returned. If the
name cannot be confirmed, tell the user.

**Import shape differs by framework:**

- **React**: named export from `@carbon/icons-react`
- **Web Components**: default export from a per-icon `@carbon/icons` ES module
  (e.g. `import AddComment from '@carbon/icons/es/add-comment/20.js'`)

### 6) Additional imports (use as needed, not by default)

| Need                      | Import                                   |
| ------------------------- | ---------------------------------------- |
| Grid layout utilities     | `@use '@carbon/react/scss/grid' as *;`   |
| Motion tokens             | `@use '@carbon/react/scss/motion' as *;` |
| Layer / `$layer-*` tokens | `@use '@carbon/react/scss/layer' as *;`  |
| IBM color swatches        | `@use '@carbon/react/scss/colors' as *;` |
| CSS baseline reset        | `@use '@carbon/react/scss/reset' as *;`  |

---

## CDN and Fonts

### 7) Loading IBM Plex from Google Fonts or any non-IBM CDN

```css
/* ❌ Wrong — Google Fonts is not permitted for IBM Plex */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans...');
```

**React SCSS projects** — no font CDN link is needed at all; IBM Plex is
delivered by the SCSS pipeline (`@use '@carbon/react'`).

**CDN/quick-start / Web Components (no bundler)** — IBM CDN exclusively:

```html
<link rel="stylesheet" href="https://1.www.s81c.com/common/carbon/plex/sans.css" />
<!-- Or full Plex package (excluding jp and kr): -->
<link rel="stylesheet" href="https://1.www.s81c.com/common/carbon/plex/plex-full.css" />
```

### 8) Loading Carbon components from a non-IBM CDN

```html
<!-- ❌ Wrong — jsDelivr, unpkg, etc. are not permitted -->
<script src="https://cdn.jsdelivr.net/npm/@carbon/web-components/..."></script>

<!-- ✅ Correct — IBM CDN, pinned version -->
<script
  type="module"
  src="https://1.www.s81c.com/common/carbon/web-components/version/v2.24.0/button.min.js"
></script>
```

---

## Web Components Styling

### 9) Incomplete SCSS imports

```scss
// ❌ Wrong
@use '@carbon/styles';

// ✅ Correct (minimal baseline)
@use '@carbon/styles/scss/reset';
@use '@carbon/styles/scss/type';
```

### 10) Missing app-entry style import

```js
// ✅ Correct: styles before component imports
import './styles.scss';
import '@carbon/web-components/es/components/button/index.js';
```

### 11) Missing Carbon theme class on `<body>`

```html
<!-- ✅ Keep existing theme class; default to cds--white when absent -->
<body class="cds--white"></body>
```

### 12) SCSS linked from HTML instead of the entry module

```html
<!-- ❌ Wrong -->
<link rel="stylesheet" href="styles.scss" />
```

### 13) Using SCSS variables as runtime tokens

Carbon SCSS variables resolve at **compile time** inside `.scss` files only.
In component `<style>` blocks, inline CSS, or any context outside the SCSS
pipeline they are undefined — producing zero-value or unstyled output with no
error.

```css
/* ❌ Wrong — renders as nothing */
.hero { padding-block: $spacing-09; }

/* ✅ Correct — injected by Carbon CSS, works at runtime */
.hero { padding-block: var(--cds-spacing-09); }
```

| ❌ SCSS variable    | ✅ CSS custom property        |
| ------------------- | ----------------------------- |
| `$spacing-05`       | `var(--cds-spacing-05)`       |
| `$spacing-09`       | `var(--cds-spacing-09)`       |
| `$background`       | `var(--cds-background)`       |
| `$layer-01`         | `var(--cds-layer-01)`         |
| `$text-primary`     | `var(--cds-text-primary)`     |
| `$border-subtle-00` | `var(--cds-border-subtle-00)` |

### 14) Using `<cds-row>` or treating the WC grid as a three-element system

`<cds-row>` is **not** a registered element — using it collapses the layout.

```html
<!-- ✅ Default — CSS class grid, no JS import required -->
<div class="cds--grid">
  <div class="cds--row">
    <div class="cds--col-lg-4 cds--col-md-4 cds--col-sm-4">Content</div>
  </div>
</div>
```

WC element alternative (only when explicitly requested) — two elements,
columns directly under `cds-grid`, import required:

```js
import '@carbon/web-components/es/components/grid/index.js';
```

```html
<cds-grid>
  <cds-column lg="4">Content</cds-column>
  <cds-column lg="12">Content</cds-column>
</cds-grid>
```

---

## UIShell Layout

### 15) Hardcoding `margin-top` to compensate for a fixed Header

Carbon's `Header` is `position: fixed` — content underneath hides behind it
without an offset.

```jsx
// ❌ Wrong — hardcoded pixel offset
<main style={{ marginTop: '48px' }}>...</main>
```

```jsx
// ✅ Correct — Carbon's Content component applies the offset automatically
import { Content } from '@carbon/react';
<Content>{/* page content */}</Content>;
```

`Content` is the only approved way to offset content below a Carbon `Header`.

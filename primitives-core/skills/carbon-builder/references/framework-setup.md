# Framework Setup & Composition Rules

## 1. Framework Choice

- User says nothing → **default to React**.
- **Never mix** React and Web Components in a single response. React → JSX
  only; Web Components → HTML/Lit-based examples only. Import lines are the
  guardrail: `import { html } from 'lit'` ⇒ Web Components; component imports
  from `@carbon/react` ⇒ React.
- When consulting examples (Storybook, GitHub stories), discard anything whose
  framework doesn't match the task — never silently adapt across frameworks.

### Icon import shape differs by framework

- **React**: named export from `@carbon/icons-react` —
  `import { AddComment } from '@carbon/icons-react';`
- **Web Components**: default export from a per-icon `@carbon/icons` ES
  module — `import AddComment from '@carbon/icons/es/add-comment/20.js';`

Verify every icon name against the installed package first — see
[verification.md](verification.md). Slugs normalize spaces → hyphens
(`ai governance` → `ai-governance`) and variants use double hyphens
(`ai--governance`). If a name can't be confirmed, tell the user — do not fall
back to a guessed name.

---

## 2. React SCSS Baseline

Include Carbon SCSS imports in a project-level SCSS file (e.g.
`src/styles.scss` or `src/App.scss`).

**Component styles (required)** — emits the compiled CSS for every Carbon
component. Without this, all Carbon components render completely unstyled:

```scss
@use '@carbon/react';
```

**Token namespaces (optional)** — only if your custom SCSS uses Carbon tokens:

```scss
@use '@carbon/react/scss/spacing' as *; // only if using $spacing-* tokens
@use '@carbon/react/scss/theme' as *; // only if using $text-*, $background, etc.
@use '@carbon/react/scss/type' as *; // only if using type mixins
@use '@carbon/react/scss/breakpoint' as *; // only if using breakpoint helpers
```

### Additional imports (include as needed)

| Import                                   | When to add                        |
| ---------------------------------------- | ---------------------------------- |
| `@use '@carbon/react/scss/grid' as *;`   | Carbon Grid layout utilities       |
| `@use '@carbon/react/scss/motion' as *;` | Carbon motion tokens               |
| `@use '@carbon/react/scss/layer' as *;`  | Layer nesting or `$layer-*` tokens |
| `@use '@carbon/react/scss/colors' as *;` | IBM Design Language color swatches |
| `@use '@carbon/react/scss/reset' as *;`  | CSS baseline reset                 |

### Entry-module wiring

Import the SCSS file in the app entry module **before** any component imports:

```js
// src/main.jsx or src/index.jsx
import './styles.scss'; // ← Carbon SCSS — must come first
import App from './App';
```

### Never do this for React

```js
// ❌ Wrong — CSS file bypasses SCSS token resolution
import '@carbon/styles/css/styles.css';
```

### IBM Plex font and typography

IBM Plex is provided automatically through the Carbon SCSS pipeline — **no
separate font CDN link for React SCSS projects.**

For CDN/quick-start scenarios (no bundler, Web Components only), load IBM Plex
from the IBM-hosted CDN exclusively:

```html
<!-- ✅ Correct — IBM CDN for Plex fonts -->
<link rel="stylesheet" href="https://1.www.s81c.com/common/carbon/plex/sans.css" />
<!-- Or full Plex package (excluding jp and kr): -->
<link rel="stylesheet" href="https://1.www.s81c.com/common/carbon/plex/plex-full.css" />
```

Never Google Fonts — neither `<link>` nor `@import`.

Apply typography via semantic HTML (`h1`, `h2`, `p`) with Carbon type tokens
or classes.

### Spacing tokens via SCSS utility classes — never inline token strings

```scss
.section-spacing {
  margin-block: $spacing-07;
}
```

```jsx
// ❌ Wrong — token strings do NOT resolve at runtime
<Component style={{ margin: '$spacing-05' }} />

// ✅ Correct
<Component className="section-spacing" />
```

---

## 3. Web Components Styling Safety

Prefer a minimal import strategy first.

### Stepwise SCSS setup

1. **Minimal baseline (always first)**

```scss
@use '@carbon/styles/scss/reset';
@use '@carbon/styles/scss/type';
```

2. **Add grid only when layout utilities are needed** — append
   `@use '@carbon/styles/scss/grid';`

3. **Add theme wiring only when explicitly required** — append
   `@use '@carbon/styles/scss/theme';` and `@use '@carbon/styles/scss/themes';`
   Do not introduce `theme with (...)` wiring unless the task requires it.

### Project wiring checks

- Import SCSS from the app entry module before component imports
  (`import './styles.scss';`).
- Never reference SCSS files from HTML `<link>` tags.
- Preserve an existing app theme class on `<body>`; otherwise default to
  `<body class="cds--white">`.
- If SCSS import resolution fails, fall back to
  `@carbon/styles/css/styles.css` imported in the entry module.

### Token usage in component styles (Hard Rule)

Carbon SCSS variables (`$spacing-*`, `$background`, `$layer-01`, ...) are
**compile-time only**. In runtime CSS (component styles, inline CSS), always
use the CSS custom properties injected by the compiled Carbon CSS:

| ❌ SCSS variable (compile-time) | ✅ CSS custom property (runtime) |
| ------------------------------- | -------------------------------- |
| `$spacing-05`                   | `var(--cds-spacing-05)`          |
| `$background`                   | `var(--cds-background)`          |
| `$layer-01`                     | `var(--cds-layer-01)`            |
| `$text-primary`                 | `var(--cds-text-primary)`        |
| `$border-subtle-00`             | `var(--cds-border-subtle-00)`    |

Using SCSS variables at runtime produces no output and silently renders
unstyled.

### Grid — CSS classes, not custom elements (Hard Rule)

The Carbon grid for Web Components is **CSS-based**:

```html
<!-- ✅ Correct — works with Carbon CSS alone, no JS import -->
<div class="cds--grid">
  <div class="cds--row">
    <div class="cds--col-lg-4 cds--col-md-4 cds--col-sm-4">...</div>
    <div class="cds--col-lg-8 cds--col-md-4 cds--col-sm-4">...</div>
  </div>
</div>
```

```html
<!-- ❌ Wrong — cds-row does not exist; layout collapses -->
<cds-grid><cds-row>...</cds-row></cds-grid>
```

`<cds-grid>` + `<cds-column>` WC elements do exist but require
`import '@carbon/web-components/es/components/grid/index.js';` and use a
two-element system with **no `<cds-row>`**. Only use them when explicitly
requested, with the import included.

---

## 4. Component Composition Rules

Silent prop/composition requirements that fail without error messages.

### Modal

**`onRequestClose`, not `onClose`:**

```jsx
// ❌ Does not fire:
<Modal onClose={() => setOpen(false)} open={open} />
// ✅ Correct:
<Modal onRequestClose={() => setOpen(false)} open={open} />
```

**`autoAlign` on floating-UI children inside Modal** — required so Dropdown,
ComboBox, and Select don't position outside the viewport:

```jsx
<Dropdown autoAlign id="d1" titleText="Region" items={items} itemToString={i => i?.text ?? ''} />
<ComboBox autoAlign id="c1" titleText="Role" items={items} />
```

**`data-modal-primary-focus` on the first focusable input** — Carbon uses it
to set initial focus on open (accessibility requirement):

```jsx
<TextInput data-modal-primary-focus id="domain" labelText="Domain name" placeholder="example.com" />
```

**Complete Modal-with-form composition:**

```jsx
<Modal
  open={open}
  onRequestClose={() => setOpen(false)}
  modalHeading="Add a custom domain"
  primaryButtonText="Add"
  secondaryButtonText="Cancel"
>
  <TextInput data-modal-primary-focus id="domain" labelText="Domain name" placeholder="example.com" />
  <Dropdown
    autoAlign
    id="region"
    titleText="Region"
    label="Select region"
    items={[{ id: 'us-south', text: 'US South' }]}
    itemToString={(item) => item?.text ?? ''}
  />
  <ComboBox autoAlign id="role" titleText="Permissions" items={['Viewer', 'Editor', 'Manager']} />
</Modal>
```

**Feature flags** (`enableDialogElement`, `enablePresence`):

```jsx
import { FeatureFlags } from '@carbon/react';
<FeatureFlags enableDialogElement enablePresence>
  <Modal ... />
</FeatureFlags>
```

---

## 5. Component Selection Rules (Critical)

### Tag vs Status Indicators

- **Tag** classifies content — "what is this?" (category, label, filter).
- **Status indicators** communicate state — "what is happening?" Use
  `IconIndicator`/`ShapeIndicator` with the `kind` prop (`failed`, `warning`,
  `caution`, `succeeded`, `in-progress`, `pending`, ...).
- **Never use a colored Tag for status.**

**Bright-line test — do not reason around this:** if the value is a
lifecycle, health, or outcome word — *active, expired, revoked, failed,
succeeded, pending, degraded, in-progress, down, enabled, disabled* — it is
**status**, no matter how static or attribute-like it feels. "An API key
*is* expired" is still a state the system moved it into, not a category a
person assigned. Tag is reserved for taxonomy a user assigned or could
reassign: categories, topics, labels, filter chips, keywords.

```jsx
// ❌ Wrong — Tag is not a status indicator
<Tag type="red">Failed</Tag>

// ✅ Correct
import { preview__IconIndicator as IconIndicator } from '@carbon/react';
<IconIndicator kind="failed" />
```

Status indicators are **components, not icons** — don't go hunting for a
"failed" icon. (Verify the `preview__` export name against the installed
version — see [verification.md](verification.md).)

**Decision:** classification (what it IS) → `Tag` | state (what's HAPPENING)
→ `IconIndicator`/`ShapeIndicator`.

### Tabs orientation pairing

Horizontal and vertical tabs use different container sets — never mix:

- Horizontal → `Tabs` + `TabList`
- Vertical → `TabsVertical` + `TabListVertical`
- `Tab`, `TabPanels`, `TabPanel` work with both.

```jsx
import { Tabs, TabList, Tab, TabPanels, TabPanel } from '@carbon/react';
<Tabs>
  <TabList aria-label="List of tabs">
    <Tab>Tab 1</Tab>
    <Tab>Tab 2</Tab>
  </TabList>
  <TabPanels>
    <TabPanel>Content 1</TabPanel>
    <TabPanel>Content 2</TabPanel>
  </TabPanels>
</Tabs>;
```

```jsx
import { TabsVertical, TabListVertical, Tab, TabPanels, TabPanel } from '@carbon/react';
<TabsVertical>
  <TabListVertical aria-label="List of vertical tabs">
    <Tab>Tab 1</Tab>
    <Tab>Tab 2</Tab>
  </TabListVertical>
  <TabPanels>
    <TabPanel>Content 1</TabPanel>
    <TabPanel>Content 2</TabPanel>
  </TabPanels>
</TabsVertical>;
```

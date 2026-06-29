# Implementation Guardrails

## 1. Stability Policy (Hard Rule)

Never suggest or use unstable, preview, canary, or `@carbon/labs-react`
components unless the user explicitly asks for them or they are already
present in the repository. If a stable Carbon equivalent exists, use it by
default. (Exports prefixed `preview__` / `unstable__` in the installed
package are the tell.)

---

## 2. AI Chat SSR Build-Safety (Hard Rule)

Apply when generating code that uses `@carbon/ai-chat` or
`@carbon/web-components`.

### Detect SSR first

- SSR entry files (`entry-server.*`, `server.js`, `server.ts`)
- SSR config in `vite.config.*` / `webpack.config.*` (`ssr`, `ssr.external`, `ssr.noExternal`)
- SSR scripts in `package.json` (`build:ssr`, `dev:ssr`, `preview:ssr`)

### If SSR is present

- No top-level browser-only imports in SSR-rendered code paths.
- Use client-only loading (`React.lazy` + `Suspense`, or dynamic import in `useEffect`).
- Add `@carbon/ai-chat` and `@carbon/web-components` to `ssr.external` when needed.
- Treat client-only loading and SSR config as a required pair.

### CSS import rule

Do not import CSS from `@carbon/ai-chat/es/index.css` (or similar paths). AI
Chat styles are encapsulated; invalid CSS imports cause build failures.

### Reference material

Docs and complete runnable examples (roots: `basic`, `custom-element`,
`history`, `watsonx`, `watch-state`) live in the `carbon-ai-chat` repo and its
Storybook — links in [llms.txt](llms.txt). Work from a complete example's file
set, not fragments.

---

## 3. Package and Dependency Rules

- Prefer official Carbon packages over recreating equivalent components. If a
  required Carbon package is missing, add the dependency instead of
  hand-building a clone.
- **React**: `@use '@carbon/react'` in the project SCSS file is required;
  token imports optional (see [framework-setup.md](framework-setup.md)).
  Never `@carbon/styles/css/styles.css` for React.
- When using `@carbon/react`, no separate `@carbon/styles` install is needed —
  it ships as a transitive dependency. Add `sass` to devDependencies if absent.
- **Theme configuration syntax (Hard Rule)** — pass a **theme map variable**,
  never a string:

  ```scss
  @use '@carbon/styles/scss/themes' as *;
  @use '@carbon/styles/scss/theme' with (
    $theme: $white
  ); // $white, $g10, $g90, $g100
  ```

  ❌ `$theme: 'white'` — fails at compile time (`$map2: "white" is not a map`).

- **IBM Products (React)** — styles load in addition to the Carbon baseline.
  Two valid approaches — **do not mix**:

  **Option A — SCSS (preferred for theme control).** Order is mandatory:

  ```scss
  @use '@carbon/styles'; // Carbon foundation — first
  @use '@carbon/ibm-products/scss/index'; // IBM Products layer — after
  ```

  ❌ Reversed order breaks tokens and mixins. ❌ `@use` on a `.css` file fails.

  **Option B — Prebuilt CSS.** Both imports in the JS entry file:

  ```javascript
  import '@carbon/styles/css/styles.css';
  import '@carbon/ibm-products/css/index.min.css';
  ```

  **`pkg` flags** — some IBM Products components require explicit opt-in:

  ```javascript
  import { pkg } from '@carbon/ibm-products';
  pkg.component.Datagrid = true;
  ```

  A component that renders nothing with no error → missing `pkg.component`
  flag is the most likely cause.

  **Web Components:** IBM Products for WC is the separate package
  `@carbon/ibm-products-web-components` with different style paths. Never
  apply the React paths; verify setup from the package's own README (in
  `node_modules` or on GitHub).

- **Web Components projects**: `@carbon/web-components` for components,
  `@carbon/styles` for global styles/fonts; `sass` only when SCSS is used.
  Never reference undocumented style paths (e.g. ad-hoc per-component CSS files).
- **Charts**: see [charts.md](charts.md).

---

## 4. Component/API Correctness

- Avoid deprecated props when a supported prop exists.
- Validate props against the installed package's type definitions, the docs
  site, or Storybook — see [verification.md](verification.md). Never from memory.
- Keep imports aligned with the package that actually exports the symbol
  (`@carbon/react` vs `@carbon/ibm-products` — never mix in one import line).

---

## 5. Styling and Theming Discipline

- **No inline styles in JSX/TSX.** All styling in SCSS/CSS files using Carbon
  tokens and mixins, applied via `className`. Exception: dynamic values that
  cannot be predetermined (user-controlled dimensions, animation transforms).
- Carbon theme tokens, spacing tokens, and typography mixins over hardcoded values.
- Never target Carbon internal class names (`.bx--`, `.cds--`) unless no
  alternative exists and the user explicitly confirms.
- Don't force `<Theme>` wrappers when the host app already provides Carbon
  theme context.
- Web Components runtime styles: CSS custom properties (`var(--cds-*)`), never
  SCSS variables — see [framework-setup.md](framework-setup.md).
- **CDN** — only the IBM CDN (`1.www.s81c.com`). Never Google Fonts, jsDelivr,
  unpkg, or any other third-party CDN for Carbon components or IBM Plex.

  | Resource                | IBM CDN URL                                                                              |
  | ----------------------- | ---------------------------------------------------------------------------------------- |
  | IBM Plex Sans           | `https://1.www.s81c.com/common/carbon/plex/sans.css`                                     |
  | IBM Plex (full package) | `https://1.www.s81c.com/common/carbon/plex/plex-full.css`                                |
  | Carbon Web Components   | `https://1.www.s81c.com/common/carbon/web-components/version/v2.24.0/[component].min.js` |

  Replace `[component]` with the component name (`button`, `dropdown`, ...)
  and pin the current version. React SCSS projects need no font CDN link at all.

---

## 6. Web Components Project Setup Checklist

- App entry module imports styles before component imports (`import './styles.scss';` first).
- `<body>` preserves an existing Carbon theme class; default `cds--white` if none.
- No SCSS referenced through HTML `<link>` tags.
- Dependencies include `@carbon/web-components` and `@carbon/styles`; `sass` only when SCSS is used.

---

## 7. Layout and Accessibility Guardrails

- Separate Grid containers per logical content group; responsive spans
  (`sm`/`md`/`lg`) on all layout columns. See [grid-system.md](grid-system.md).
- Overlay/floating UI (modals, side panels, tooltips, toasts) stays out of
  normal page Grid flow.
- Breadcrumb current item: `isCurrentPage`, no `href`.
- Icon-only interactive controls: descriptive `iconDescription`.
- **UIShell Header + Content (Hard Rule):** Carbon's `Header` is
  `position: fixed`. Always wrap main page content in `Content` from
  `@carbon/react` — it applies the offset automatically. Never a hardcoded
  `margin-top: 48px` substitute.

### Layer System

Never set `level` manually — nesting determines level. Use `withBackground`
when a visible background change is intended; without it, `Layer` only
provides theme context.

```jsx
// ✅ Correct
<Layer withBackground>
  <ComponentOnLayer01 />
  <Layer>
    <ComponentOnLayer02 />
  </Layer>
</Layer>

// ❌ Wrong — manual level breaks the automatic system
<Layer level={2}>...</Layer>
```

---

## 8. Image-Driven UI Workflow

When the user provides images or visual references:

- Perform a complete design analysis before implementation, starting with
  design scale (dimensions/proportions) before component mapping.
- Analysis output sections: Component Inventory · Typography Analysis · Grid
  Analysis (see [grid-system.md](grid-system.md)) · Spacing Analysis.
- Separate Grid containers for logical content groups that wrap together.
- Pause after presenting the analysis and get user confirmation before
  implementing.
- Custom class names for styling; no Carbon internal class targeting without
  explicit confirmation.
- Validate the implemented UI in the browser (visual, responsive, accessibility).

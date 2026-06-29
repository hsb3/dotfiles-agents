# Carbon token reference

Self-contained. All tokens are theme-aware (White / g10 / g90 / g100) unless
noted. SCSS uses `$token`; React/CSS uses the custom property `--cds-token`.
**Never** reference the raw palette (`$blue-60`, `$gray-90`). Stay in this file.

---

## How layer sets work (read before picking surface/border/field tokens)

- Surface, border, and field tokens come in **sets** suffixed `-01 / -02 / -03`,
  plus a base set (no suffix or `-00`). A component sitting on a given layer must
  use that layer's set throughout.
- **Field is one step above its background.** A field on a `$layer-02` surface
  uses `$field-03`.
- **Borders pair to their own number.** `$field-03` pairs with `$border-strong-03`.
- **Text and icon tokens are layer-independent** — no suffix, work everywhere.
- **Contextual tokens** (`$layer`, `$field`, `$border-subtle`, no number) change
  value by position when wrapped in `<Layer>`. Prefer these for reusable
  components; use explicit `-0N` tokens when a component lives at a fixed depth.

---

## Surfaces

| Token | Use |
|-------|-----|
| `$background` | Page background (base layer) |
| `$background-hover` / `-active` / `-selected` | Page-level interactive states |
| `$background-inverse` | Inverse surfaces (tooltips, high-contrast) |
| `$layer-01` / `-02` / `-03` | Container surfaces, one per stacking level |
| `$layer-hover-0N` / `-active-0N` / `-selected-0N` | Container interactive states |
| `$layer` (contextual) | Reusable-component surface; auto-maps via `<Layer>` |
| `$layer-accent-01` / `-02` / `-03` | Accent surface within a layer (e.g. selected day) |
| `$field-01` / `-02` / `-03` | Input/field backgrounds (one step above their layer) |
| `$field` (contextual) | Reusable-component field background |

## Borders

| Token | Use |
|-------|-----|
| `$border-subtle-00` / `-01` / `-02` / `-03` | Low-emphasis dividers, per layer |
| `$border-strong-01` / `-02` / `-03` | Input borders, per layer (pairs to field number) |
| `$border-tile-01` / `-02` / `-03` | Tile borders |
| `$border-interactive` | Focused/active interactive border (brand color) |
| `$border-inverse` | Border on inverse surfaces |
| `$border-disabled` | Disabled borders |
| `$border-subtle` / `$border-strong` (contextual) | Reusable-component borders |

## Text (layer-independent)

| Token | Use |
|-------|-----|
| `$text-primary` | Body copy, headings, primary text |
| `$text-secondary` | Labels, secondary text |
| `$text-placeholder` | Input placeholder |
| `$text-helper` | Helper/caption text under fields |
| `$text-error` | Error message text |
| `$text-on-color` | Text on a colored fill (e.g. primary button label) |
| `$text-on-color-disabled` | Disabled text on colored fill |
| `$text-inverse` | Text on inverse surfaces |
| `$text-disabled` | Disabled text |

## Icons (layer-independent)

| Token | Use |
|-------|-----|
| `$icon-primary` / `$icon-secondary` | Default icon fills |
| `$icon-interactive` | Icons that are themselves interactive |
| `$icon-on-color` | Icons on colored fills |
| `$icon-inverse` / `$icon-disabled` | Inverse / disabled |

## Links

`$link-primary`, `$link-primary-hover`, `$link-secondary`, `$link-inverse`,
`$link-visited`.

## Status / support (use for app metrics — alias these, don't recolor)

| Token | Meaning |
|-------|---------|
| `$support-error` | Error / negative |
| `$support-success` | Success / positive |
| `$support-warning` | Warning |
| `$support-info` | Informational |
| `$support-caution-major` / `-minor` | Graded caution |
| `$support-*-inverse` | Same, on inverse surfaces |

## Interactive + focus

`$interactive` (primary brand action color), `$focus`, `$focus-inset`,
`$focus-inverse`, `$highlight`.

## AI tokens (ONLY for Carbon-for-AI components)

`$ai-aura-start/-end`, `$ai-border-start/-end/-strong`, `$ai-popover-background`,
`$ai-overlay`, etc. Do not use on non-AI UI — they signal "AI-generated content"
to users and misusing them is a correctness bug, not a style choice.

---

## Component tokens (opt-in via `@use`)

Only valid inside the component they name. Example:
`@use '@carbon/styles/scss/components/button';` then `button.$button-primary`.

- **Button**: `$button-primary`, `-primary-hover`, `-primary-active`,
  `$button-secondary` (+states), `$button-tertiary` (+states),
  `$button-danger-primary`, `$button-danger-secondary`, `$button-danger-hover`,
  `$button-danger-active`, `$button-separator`, `$button-disabled`.
- **Tag**, **Notification**, **Content switcher** also expose component tokens —
  consult Storybook for names. Never reuse a component token outside its component.

---

## Spacing scale (`$spacing-0N`) — the ONLY margin/padding source

Multiples of 2/4/8. No arbitrary px/rem.

| Token | rem | px |
|-------|-----|----|
| `$spacing-01` | 0.125 | 2 |
| `$spacing-02` | 0.25 | 4 |
| `$spacing-03` | 0.5 | 8 |
| `$spacing-04` | 0.75 | 12 |
| `$spacing-05` | 1 | 16 |
| `$spacing-06` | 1.5 | 24 |
| `$spacing-07` | 2 | 32 |
| `$spacing-08` | 2.5 | 40 |
| `$spacing-09` | 3 | 48 |
| `$spacing-10` | 4 | 64 |
| `$spacing-11` | 5 | 80 |
| `$spacing-12` | 6 | 96 |
| `$spacing-13` | 10 | 160 |

Prefer the `<Stack gap={N}>` component over manual margins between stacked items —
it delegates spacing to the parent and keeps children margin-free.

---

## Type tokens (`$token` + matching utility class)

Font is IBM Plex Sans (and IBM Plex Mono for code) — do not change it.
No custom `font-size` / `line-height`; use a token.

**Body**: `$body-01` (14px/20), `$body-02` (16px/24), `$body-compact-01`,
`$body-compact-02`.

**Headings** (productive): `$heading-01` (14px/20, 600), `$heading-02` (16px/24,
600), `$heading-03` (20px/28), `$heading-04` (28px/36), `$heading-05` (32px/40),
`$heading-06` (42px/50), `$heading-07` (54px/64). Compact variants:
`$heading-compact-01`, `$heading-compact-02`.

**Fluid (expressive, responsive)**: `$fluid-heading-03`..`$fluid-heading-06`,
`$fluid-display-01`..`$fluid-display-04`, `$fluid-paragraph-01`. Use sparingly —
default to fixed productive type for dense analytics UI.

**Utility**: `$label-01`, `$label-02`, `$helper-text-01`, `$helper-text-02`,
`$legal-01`, `$legal-02`, `$code-01`, `$code-02`.

---

## Theme selection

```jsx
import { Theme } from '@carbon/react';
<Theme theme="g100">{/* dark */}</Theme>   // White | g10 | g90 | g100
```

The `theme` mixin emits CSS custom properties by default — light/dark is a theme
swap, not a token rewrite. Pick the app's base theme once at layer 0 and freeze it.

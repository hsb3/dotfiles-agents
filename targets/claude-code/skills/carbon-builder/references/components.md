# Carbon component inventory

Self-contained. The Carbon catalog mapped onto the Atomic Design stages
(atoms → molecules → organisms → templates → pages). Before building
**anything**, check this list. If Carbon has it, you import it — you do not
build it. Hand-rolling a component Carbon already ships is the single most
common source of generic, off-system UI.

Import all from `@carbon/react`. Icons from `@carbon/icons-react`.

---

## Atoms — Carbon primitives: import as-is, never restyle

**Inputs & forms**
`Button`, `IconButton`, `Checkbox`, `RadioButton`, `RadioButtonGroup`, `Toggle`,
`Select`, `Dropdown`, `MultiSelect`, `ComboBox`, `TextInput`, `TextArea`,
`PasswordInput`, `NumberInput`, `Search`, `Slider`, `DatePicker`,
`DatePickerInput`, `TimePicker`, `FileUploader`, `FilterableMultiSelect`.

**Display & status**
`Tag`, `Tile`, `Link`, `Tooltip`, `Toggletip`, `InlineLoading`, `Loading`,
`SkeletonText`, `SkeletonPlaceholder`, `ProgressBar`, `InlineNotification`,
`ToastNotification`, `ActionableNotification`, `AspectRatio`.

**Typography helpers**
`CodeSnippet`, `DefinitionTooltip`, `OrderedList`, `UnorderedList`, `ListItem`.

> Rule: these render correct on layer 01 by default. If one must sit on a deeper
> layer, wrap in `<Layer>` — do not pass custom background styles.

---

## Molecules & organisms — Carbon ships many organisms complete; you assemble the molecules

**Organisms Carbon ships complete — use the Carbon one, never reassemble your own:**
`DataTable` (with `TableToolbar`, `TableBatchActions`, sorting, selection,
expansion, pagination), `Pagination`, `PaginationNav`, `Accordion`, `Tabs`
(`TabList`, `Tab`, `TabPanels`, `TabPanel`), `ContentSwitcher`, `StructuredList`,
`TreeView`, `Modal`, `ComposedModal`, `Popover`, `OverflowMenu`, `Menu`,
`MenuButton`, `ComboButton`, `ProgressIndicator`, `Breadcrumb`,
`Toolbar`, `Tag` (+ `DismissibleTag`, `SelectableTag`, `OperationalTag`).

**Molecules you assemble from atoms** (generic, reusable, no business logic
baked in): form rows, filter bars, record/summary cards (from `Tile` + atoms),
metric readouts. **Domain organisms you assemble from molecules**:
table-plus-toolbar regions, page header groups, filter panels specific to
your product.

> Rule: a molecule uses only atoms + tokens; an organism uses molecules and
> atoms. If you find yourself reaching for a raw element or a one-off style,
> the atom is missing — drop down a stage and add it there.

---

## Templates — page skeleton & shell

**UI Shell** (the app frame — Carbon-shipped organisms you arrange here; use
them, don't build a header/nav):
`Header`, `HeaderName`, `HeaderNavigation`, `HeaderMenu`, `HeaderMenuItem`,
`HeaderGlobalBar`, `HeaderGlobalAction`, `HeaderPanel`, `SideNav`,
`SideNavItems`, `SideNavLink`, `SideNavMenu`, `SideNavMenuItem`, `Content`.

**Layout primitives** (page structure — no bespoke flex/grid scaffolding):
`Grid`, `Column`, `FlexGrid`, `Stack`, `Layer`, `Theme`.

**Required state patterns every screen must define** (build from
molecules/organisms):
- Loading → skeleton components, not spinners-on-everything
- Empty → explicit empty state, not a blank table
- Error → `InlineNotification` / `ActionableNotification`
- Partial/permission → degrade gracefully

> Rule: templates introduce **no new atoms** and stay content-agnostic. They
> arrange organisms inside the shell + grid.

---

## Pages — real screens wired to data

Templates filled with real content and data. Nothing visual is invented here —
this stage is plumbing + data, and it's where real content (long names, empty
tables, error responses) stress-tests every stage below.

---

## Data visualization

Use `@carbon/charts-react` for **all** charts. Never hand-roll SVG/D3 or pull a
second chart library — that breaks theme coherence instantly.

Available chart types: `SimpleBarChart`, `GroupedBarChart`, `StackedBarChart`,
`LineChart`, `AreaChart`, `StackedAreaChart`, `ScatterChart`, `BubbleChart`,
`DonutChart`, `PieChart`, `GaugeChart`, `MeterChart`, `HeatmapChart`,
`TreemapChart`, `HistogramChart`, `BoxplotChart`, `ComboChart`,
`ChoroplethChart`, plus tabular `<Table>` from the same package.

> Carbon charts have their **own** theming layer that does not auto-follow the
> page theme/layer model. Matching chart palette + background to the active
> Carbon theme is a known gap — treat it as its own task, not a default.
> Setup, data/options model, and verification: [charts.md](charts.md).

---

## "Does Carbon have this?" — quick decision

1. Search this file for the noun (table, modal, tabs, nav, upload, date...).
2. Not here? Check the installed package's exports and the Carbon Storybook
   before building (see [verification.md](verification.md)).
3. Still nothing? It's a molecule (or domain organism) — assemble it from
   atoms, tokens only. **Never** invent a styled element to fill the gap.

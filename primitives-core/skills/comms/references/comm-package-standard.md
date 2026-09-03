_The comm-package standard: shared machinery for every comm type. Read with `SKILL.md`._

# Comm package standard

A **comm** is a repeatable communication deliverable for one audience at one cadence, produced
to a standard so each instance is fast to make and consistent to read. Each instance is a
dated folder `<briefings-dir>/<YYYY-MM-DD>-<slug>/` holding the deck source, exported deck,
optional audio, and a `sources.md` provenance file. `<briefings-dir>` resolves once per
project: `_meta/briefings/` when a `_meta/` tree already exists (the mise-en-place standard),
else `briefings/` at the repo root. Never create `_meta/` just to file a comm.

This file is the **spine**: the shared toolchains, parameters, voice baseline, pipeline, and
gotchas live here once. Each per-type playbook (`examples/<type>/playbook.md`) states only what
differs and links back here.

This is **NOT** the fleet/portfolio dashboard (a separate, roster-driven repo of its own).
Never run `/update-dashboard` or scaffold a `_project-dashboard/` for a comm.

## Two toolchains

| | `deliver.py` (bundled engine) | pptx-themes (skill) |
| --- | --- | --- |
| Source | a spec (`spec.json` / `.yaml`: type, title, repo, theme, voice, sections of slides) or a bare `slides.json` array; 17 block types: heading / subtitle / lead / bullets / columns / stat / callout / divider / table / steps / timeline / matrix / quote / code / image / svg / chart | `deck.js` (pptxgenjs) + `package.json` |
| Theme | `themes/*.json` by name (7 palettes, `boardroom` default) | semantic tokens from the pptx-themes skill's `assets/theme-tokens.js` (e.g. `actuarial-signal`) |
| Output | `.html` + `.pdf` (+ narration script and `.m4a` via `narrate`) | `.pptx` + `.pdf` |
| Strengths | fast, structured, validated + voice-linted with rule ids, linkifies bare #refs, zero install | hand-laid layout (cards, 2x2, tables, dividers), confidential footer, presentation-grade |
| Use for | internal, frequent, decision-first (morning, EOD, weekly) | external, high-stakes (advisor board, client overview) |

`deliver.py` is stdlib-only Python and ships inside this skill, so the self-comms need no
MCP server (YAML specs need PyYAML; JSON needs nothing). PDF export shells out to headless
Chrome; if Chrome is absent, render `--html` and print from any browser — the HTML is fully
self-contained (styles inlined, images base64-embedded, no network). Doctrine is config
selected by name - `types/` (sections, page budgets, gather commands), `themes/`, `voices/` -
plus per-project defaults in `.claude/comms.local.md` (`theme` / `voice` / `repo` / `audio`;
CLI flag > spec field > project local > type default). Verified against every existing deck
under `_meta/briefings/` across three repos (22 decks / 256 slides) when the bare-array path
replaced the MCP renderer; a bare `slides.json` array still builds today.

For pptx-themes decks, invoke the **`pptx-themes` skill** - it owns the approved palette, semantic
theme tokens, typography, and the visual-QA workflow. Available token themes: `actuarial-signal`,
`boardroom`, `clinical-intelligence`, `human-outcomes`, `carbon-white`, `ivory`, `midnight`.

## Per-project parameters (auto-detect, never hard-code)

Resolve these once at the start of each run so the skill works in any repo:

| Param | How to resolve |
| --- | --- |
| `<owner>/<repo>` | `gh repo view --json nameWithOwner -q .nameWithOwner` (fallback: parse `git remote get-url origin`). The owner may have multiple GitHub accounts - never assume the slug; a wrong one silently breaks #ref links on export. |
| Handoff file | First that exists of `_meta/HANDOFF.md`, `HANDOFF.md`, `.claude/HANDOFF.md`. The cold-start source for current standing + the delivery story. |
| Gate scheme | The repo's `gate:<x>` labels if it uses them; otherwise the handoff's "what's next" / readiness section. |
| Last of this kind | Newest existing `<briefings-dir>/<YYYY-MM-DD>-<slug>/` for the same comm type - mirror its layout and use its date as the "since" boundary. |

## Output layout (per project)

The skill is global; outputs are per-project. Each deliverable is a dated folder:

```
<project>/<briefings-dir>/<YYYY-MM-DD>-<slug>/
  spec.json | slides.json | deck.js (+ package.json)   # source: deliver.py OR pptx-themes
  <name>.pdf                                # exported deck (always)
  <name>.pptx                               # pptx-themes only
  <name>.m4a                                # audio, if the playbook calls for it
  sources.md                                # claim-by-claim provenance
```

Slugs by type: `-morning-status`, `-eod-wrapup`, `-weekly-plan`, `-advisor-overview`,
`-client-overview`. Mirror the most recent prior folder of the same type for file layout.
(Under the mise-en-place standard `_meta/` is tracked by default, ADR-0006; these land in the repo unless the project keeps its briefings dir local.)

## Voice baseline (all comms; playbooks note deltas)

- **Lead with the outcome / the decision; bury the detail.** the reader's standing complaint:
  "I'm drowning in details I don't really need before I get to what I need to know."
- **Honest framing only.** Describe what is actually proven (e.g. "proven on a synthetic
  known-answer cohort"); never blanket accuracy or certification claims; call out verification
  gaps explicitly ("proven locally, not yet confirmed live") rather than rounding up.
- **Numbers live in systems; the deck points.** Footer says counts belong to the board /
  registry, as-of the date. No headline metric committed as a bare value without an as-of.
- **Phrases, not sentences** on slides; detail goes to the audio or skippable slides.
- **Pitch to the audience.** Self-comms are blunt and imperative and may name issue/PR ids —
  but **plain-English label first, id second** ("the scaffold-warning fix (da#NN)", never a
  bare "da#NN"): the reader shouldn't need ids or internal shorthand memorized to read their own
  deck (HB feedback 2026-07-02). External comms (board, client) drop internal jargon and
  unexplained issue numbers entirely, carry a confidential footer, and commit to no roadmap
  dates.

## Shared pipeline

**script path** (morning, EOD, weekly):

1. Gather current state - accuracy is the whole job (handoff + live counts + git log; see playbook).
2. Author the spec to the playbook's structure, mirroring the sample. A typed comm starts
   from `deliver.py new <type>`; a comm without a type definition yet is a bare `slides.json`
   array (no section or voice lint).
3. Check:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/comms/scripts/deliver.py" check spec.json
   ```

   Every problem at once, with rule ids: spec schema, sections vs the type, block schema,
   voice lint. Errors must be zero; a voice finding may be waived per spec (`waive:`), which
   stays visible in review. An unsupported block type is a hard error, never a silent
   drop - a status deck that quietly loses content is worse than one that fails to build.
4. Export:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/comms/scripts/deliver.py" build spec.json \
     --html <name>.html --pdf <name>.pdf --repo "<owner>/<repo>"
   ```

   `--repo` (or the spec's `repo`) linkifies bare `#refs`. Open the HTML first and trim any
   slide that overflows, then ship the PDF.
5. Narrate (if audio): `deliver.py narrate spec.json --script <name>.txt` drafts the
   spoken companion in deck order; rewrite it as speech (spell out ids and acronyms),
   review for accuracy.
6. Export audio: `deliver.py narrate <name>.txt --audio <name>.m4a` (macOS `say` by
   default; `audio` in `.claude/comms.local.md` picks another provider or `none`).
7. Write `sources.md` (provenance per claim + "board is the live source of truth").
8. Deliver: `SendUserFile` the PDF (and audio).

**pptx-themes path** (advisor board, client overview):

1. Gather + decide the narrative arc and the ask (see playbook).
2. Invoke the `pptx-themes` skill; author `deck.js` against the chosen token theme.
3. `node deck.js` to write the `.pptx`; export / convert the `.pdf`.
4. Run the skill's visual-QA pass (overflow, contrast, alignment).
5. Write `sources.md`; deliver via `SendUserFile`.

## Gotchas

- **Audio never blocks a deck.** `build` never touches narration; if a provider fails, ship
  the deck + the written script and note the block in `sources.md`; don't loop on retries.
  `#` lines in a script are never spoken.
- **There is no autofit.** `deliver.py` renders slides as authored; content that exceeds a
  1280x720 slide is clipped rather than silently shrunk. Trim the slide instead - overflow is
  a signal the slide is doing too much. Check by opening the `--html` output before shipping.
- **Chrome must exit on its own terms.** The exporter polls for the finished PDF and then
  reaps the Chrome process group it started (headless Chrome routinely writes the file and
  then never exits). It cannot touch a desktop Chrome you have open - the child runs in its
  own session.
- **Prettier table-cell trap** (only matters if a `.md` gets committed): no unicode width chars
  (em-dash, middle-dot, arrows, ellipsis) or literal `|` inside markdown table cells - use ASCII
  (`-`, `to`, `vs`). Prose and JSON and code blocks are fine.
- **pptx-themes leaves `node_modules/` + `package-lock.json`** in the output folder; that's fine
  - the folder is typically gitignored. Don't commit them.

## Delivery

`SendUserFile` the PDF (and audio) so they surface in a viewer, not the terminal. the reader reads long
content in a viewer; the terminal is for tap-to-answer decisions.

# comm-kit

Spec-driven engine for recurring communication deliverables: one YAML/JSON spec in, a
validated, voice-linted, themed HTML/PDF deck out.

Every comm this repo's owner produces shares one workflow - structured input, style/tone
choices, then package -> check -> refine -> present. Before comm-kit, that workflow was
re-implemented per skill with per-use boilerplate (hand-restated doctrine, hardcoded
palettes that drifted, a validation loop rebuilt each time). comm-kit authors it once as an
engine plus declarative config:

- **`scripts/deliver.py`** - the engine: `check | build | types | new`. Stdlib-only Python
  (YAML specs need PyYAML; JSON needs nothing). PDF export via headless Chrome; the HTML is
  fully self-contained if Chrome is absent.
- **`types/`** - deliverable type definitions: ordered sections with page budgets and guide
  strings, runnable source-gathering commands, default theme and voice. Adding a deliverable
  type costs one JSON file and zero engine changes. Shipped so far: `morning-briefing`.
- **`themes/`** - 7 palettes x 28 semantic tokens (transliterated from the pptx-themes
  skill's token contract), injected into the deck CSS as custom properties.
- **`voices/`** - named voice profiles: register, id policy, budgets, guidance. Voice
  doctrine runs as lint with rule ids - all errors at once, waivable per-spec.

Decision record: DFA-294 on the project board (owner-ratified 2026-08-26). This is build
increment 1 - additive, beside the existing comms / pptx-themes / owner-signoff skills;
consolidation only happens after demonstrated parity.

## Install

Ships in the `solo-skills` bundle (`claude plugin install solo-skills@dotfiles-agents`).

## Try it

```sh
python3 scripts/deliver.py types
python3 scripts/deliver.py check examples/morning-briefing.spec.json
python3 scripts/deliver.py build examples/morning-briefing.spec.json --pdf /tmp/briefing.pdf
```

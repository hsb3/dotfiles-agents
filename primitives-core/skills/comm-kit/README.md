# comm-kit

Spec-driven engine for recurring communication deliverables: one YAML/JSON spec in, a
validated, voice-linted, themed HTML/PDF deck out - and a spoken companion if you want one.

Every comm this repo's owner produces shares one workflow - structured input, style/tone
choices, then package -> check -> refine -> present. Before comm-kit, that workflow was
re-implemented per skill with per-use boilerplate (hand-restated doctrine, hardcoded
palettes that drifted, a validation loop rebuilt each time). comm-kit authors it once as an
engine plus declarative config:

- **`scripts/deliver.py`** - the engine: `check | build | narrate | types | new`. Stdlib-only
  Python (YAML specs need PyYAML; JSON needs nothing). PDF export via headless Chrome; the
  HTML is fully self-contained if Chrome is absent.
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

## House defaults and narration

Drop a `.claude/comm-kit.local.md` in a project and every deck built from a spec inside it
picks up the same `theme`, `voice`, `repo`, and audio provider - YAML frontmatter, flat
string keys, discovered by walking up from the spec file. A spec that names its own theme
still wins, and a CLI flag wins over both: **CLI flag > spec field > project local > type
default**. A missing file is silent; an unknown key or an unparseable block warns once and
changes nothing.

`narrate` builds a spoken companion in two steps, because the middle step is judgment.
`--script` emits an ordered narration draft from the resolved slides, deck markup stripped
and the type's audio guidance in a `#` header; you rewrite it as speech; `--audio` renders
it. Rendering uses macOS `say` by default - no account, no network, no SDK - and any other
provider is a command template with `{script}` and `{out}` placeholders, so a hosted voice
never becomes a dependency here. `audio: none` declares audio deliberately off. Output is
whatever the provider writes (`say` gives m4a; nothing transcodes), and no audio failure
blocks a deck: `build` never touches any of it.

## Install

Ships in the `solo-skills` bundle (`claude plugin install solo-skills@dotfiles-agents`).

## Try it

```sh
python3 scripts/deliver.py types
python3 scripts/deliver.py check examples/morning-briefing.spec.json
python3 scripts/deliver.py build examples/morning-briefing.spec.json --pdf /tmp/briefing.pdf
python3 scripts/deliver.py narrate examples/morning-briefing.spec.json --script /tmp/vo.txt
python3 scripts/deliver.py narrate /tmp/vo.txt --audio /tmp/briefing.m4a   # macOS `say`
```

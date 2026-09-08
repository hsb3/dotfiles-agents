---
id: decision-022
title: dependency, assumption and default metadata are inline token lists in the roster
date: '2026-09-08'
status: accepted
---
`status: accepted` — accepted by owner sign-off 2026-09-08 (item A): `assumes:` becomes an
optional roster field. **Nothing here is implemented yet.** No roster row, no gate and no script
has changed; the four passes this record scopes under "Migration" are the work that follows.

## Context

The management question nobody can answer from this tree is: **which shipped primitives presume
something about the repo that installs them, and which of those presumptions can a project
change?** The only way to answer it today is to open bodies one at a time, and each body answers
in a different place and a different register. Re-verified 2026-09-08:

| primitive | what the body says | where you learn it |
|---|---|---|
| `context-watermark` | six env names — five read with hardcoded fallbacks at `hook.py:66-70`, plus `CONTEXT_WATERMARK_LOG_PATH` at `:48`. Its README `:14-17` distinguishes the **two** the shipped wiring pre-sets from the **four** it leaves untouched | two files, one of them a README section |
| `owner-signoff` | has a key: batch root is `_meta/signoff` "unless the project sets a `signoff:` key in `.claude/owner-signoff.local.md`" (`SKILL.md:23-26`). The port is soft, not hardcoded: `SKILL.md:41`, `serve_signoff.py:71-72` takes an optional positional port, `bind()` at `:55-61` scans 20 forward | prose plus a script |
| `comms` | has a key: "A `briefings_dir` key in `.claude/comms.local.md` overrides the auto-detect" (`SKILL.md:11-14`), on top of `_meta/`-tree detection | prose |
| `planning-desk` | hardcodes `_meta/plans/` (`SKILL.md:19,24`, `README.md:3,12`) with no key anywhere | prose |

The gap this was first raised against — *primitives hardcode host conventions with no way out* —
is largely **closed** by `docs/override-convention.md` and the per-skill `.local.md` keys. What is
open is **scannability**: that page governs the *mechanism*, and nothing records the *fact* where
a query can read it. `context-watermark` proves the fact is not free text either — two of its six
env names are wired by default and four are not, and only the body says which.

Two facts frame the answer.

- **The roster already carries this kind of declaration.** `requires:` (issue #79) —
  `{hooks,local-mcp,hosted-mcp}` plus `cli:<kebab>` / `env:<kebab>`, validated at
  `scripts/check_roster.py:296-306` against `CAPABILITIES` (`:44`) and `REQUIRES_DEP` (`:53`),
  documented at `primitives-core/README.md:34` and `primitives-core.yaml:9-14`.
  `docs/vendoring-rule.md:67-68` is the same pattern for provenance.
- **The roster parser is the decisive constraint.** `parse_roster`
  (`scripts/check_roster.py:73-100`) is a hand-rolled line parser, not a YAML load. It matches
  `^  - (\w+):\s*(.*)$` (`:88`) and `^    (\w+):\s*(.*)$` (`:95`), nothing else. Probed against a
  synthetic entry carrying `assumes: [path:_meta/plans, port:8737]`, a nested `defaults:` block
  map, and `depends-on: [cli:gh]`:

  ```
  [{'id': 'probe', 'type': 'skill', 'assumes': '[path:_meta/plans, port:8737]', 'defaults': ''}]
  ```

  Three consequences, all load-bearing below. Values are scalars, so a list must be **inline flow
  style**, split by `_list` (`:64-70`). A **nested block map is silently dropped** — the key
  survives with an empty value, its children vanish, no error. And `\w+` is `[A-Za-z0-9_]`, so
  **`depends-on:` does not parse at all** while `assumes:` does. A structured per-assumption
  record is therefore impossible without rewriting that parser, which eight modules and five test
  modules import.

## Decision

**Recommended: one new optional roster field, `assumes:`**, an inline token list in the
prefixed-token style `requires:` already uses. `requires:` keeps answering "what must be
installed"; `assumes:` answers "what does this presume about the host repo, and through which
channel can a project change it". A token with no channel is a hard assumption; a token with one
is an overridable default, naming the channel and never the value.

The other two storage options are rejected:

- **Per-item frontmatter.** Hooks have no frontmatter at all — the ratified layout is `hook.py`
  plus config (ADR 0002) — so the mechanism does not exist for 15 of 74 primitives. Agent
  frontmatter is governed by the translation-matrix completeness gate (decision-009, enforced in
  `check_roster.py`): a new key must be declared in `translation.yaml` or `gen_opencode.py` drops
  it silently, dragging harness neutrality into a bookkeeping change. Skill frontmatter is a
  published surface the harness itself parses (`evals/ingest.py:65-70`). Decisive objection: a
  fact in 74 separate frontmatter blocks is invisible to every roster consumer without opening 74
  files, which is the problem, not the fix.
- **A separate manifest** (`assumptions.yaml`). Needs its own parser, its own completeness gate
  (every roster id present, no orphans), and a second file to update on every add — against a
  roster that already has the id column and the guard. It is a second source of truth for
  primitive identity, which is what ADR 0017 spent a restructure removing.

`assumes:` is the least new surface: **no new storage file**, one regex in `check_roster.py`, and
the field reaches every existing reader for free, because each reads the roster through
`parse_roster` rather than parsing it independently (`grep -rn "primitives-core.yaml\|parse_roster"
scripts/ evals/ .claude/skills/`, 2026-09-08: `check_agent_refs.py`, `check_identity.py`,
`check_provenance.py`, `check_skill_refs.py`, `check_vendored_drift.py`, `gen_claude_skills.py`,
`gen_opencode.py`, `evals/ingest.py:46`, plus five test modules). Only a reader that must **act**
on the field needs code.

## The field and its vocabulary

`assumes:` is optional. **Absent means none**, as `requires:` is today
(`primitives-core.yaml:12`), so a primitive with nothing to declare migrates as a no-op.

A token is `kind:subject`, optionally `=channel`. One regex is the whole grammar and the only
place the kind set is written down — a companion constant listing the kinds would be exactly the
second source of truth this record argues against:

```python
ASSUMES = re.compile(
    r"^(?:path:[\w.][\w./-]*|port:\d{2,5}|threshold:[a-z][a-z0-9-]*)"
    r"(?:=(?:env:[A-Z][A-Z0-9_]*|local:[a-z][a-z0-9-]*#[a-z][a-z0-9_-]*|argv|detect))?$")
```

Per-kind subjects, so `port:` takes digits and cannot silently accept `port:abc`. Every token
named in this record, checked against that regex, plus three rejections:

```
PASS path:_meta/plans                                 PASS port:8737=argv
PASS path:_meta/signoff=local:owner-signoff#signoff    PASS port:8737
PASS path:_meta/briefings=local:comms#briefings_dir    PASS path:briefings=detect
PASS threshold:context-soft=env:CONTEXT_WATERMARK_SOFT PASS threshold:context-hard=env:CONTEXT_WATERMARK_HARD
FAIL port:abc            FAIL tracker:kata            FAIL path:_meta/plans=env:lowercase
```

No commas inside a token — `_list` splits on them.

| kind | means | real example |
|---|---|---|
| `path:` | a repo-relative path the primitive presumes or writes into | `path:_meta/plans` — `planning-desk`, no key anywhere |
| `port:` | a TCP port it binds or dials | `port:8737=argv` — `owner-signoff/scripts/serve_signoff.py:22,71` |
| `threshold:` | a numeric or list knob with a shipped default | `threshold:context-soft=env:CONTEXT_WATERMARK_SOFT` — `context-watermark/hook.py:66` |

| channel | maps onto | example |
|---|---|---|
| `env:<VAR>` | `docs/override-convention.md:11`, row 1 — env var with a shell-expanded default in `hooks.json` | `context-watermark`, `delegation-watermark`, `lane-snapshot` |
| `local:<file>#<key>` | `:12`, row 2 — a key in `.claude/<id>.local.md`. The file is spelled out because it is **not** derivable from the entry id: `handoff`'s key lives in `.claude/atelier.local.md` (`:45-46`) | `local:owner-signoff#signoff`, `local:comms#briefings_dir` |
| `detect` | `:13`, row 3 — derived from the tree, declared nowhere | `comms`' `_meta/`-tree detection |
| `argv` | the documented per-run case at `:64-66` — "deliberately gets no key ... optional positional argument" | `owner-signoff`'s port |
| *absent* | no override at all — a hard assumption | `path:_meta/plans` |

**The channel vocabulary is a projection of `docs/override-convention.md`, not a fourth
mechanism** — the likeliest way this proposal goes wrong. `assumes:` records which existing
channel and which key, never the value's semantics, never a channel that page does not sanction,
and it is never a place a project sets anything. Adding a channel means amending that page first.

**No numeric default values in the roster.** `threshold:context-soft` is a label; the number is
already replicated across six surfaces — `hook.py:42`, `config.json:7`,
`context-watermark/README.md:14`, `plugins/atelier/hooks/hooks.json:164`,
`plugins/atelier/README.md:255`, `docs/override-convention.md:33` — so a roster entry would be a
seventh copy of a fact nobody queries across primitives, while the label is replicated nowhere.
Paths are the asymmetric case and are recorded in full: a path *is* the assumption about the host
repo, and it is what management asks across primitives.

One field rather than three: `requires:` already answers "depends on", and an assumption with a
channel *is* an overridable default — one token list, two filters.

## The drift guard

Two directions, both offline and stdlib, so both can sit in `make ci`.

**Grammar** goes in `check_roster.py` beside the `requires` block (`:296-306`) — one regex, about
ten lines, two test methods alongside the existing ones. No closed-key gate has to change:
`check_entry_schema` (`:272-313`) checks a hardcoded list of known keys and never iterates
`e.keys()`, so an entry carrying `assumes` and a junk key `wat` returns `problems: []` (probed
2026-09-08). An unvalidated field is silently accepted today; the regex is what makes it mean
something.

**Corroboration** goes in a new `scripts/check_assumes.py` on the existing `check` target
(`Makefile:7-13`), never a new CI job — job names are frozen (`docs/gotchas.md`, "Reading the
gates"). Roughly 120 lines, reading only files in-tree.

- *Forward* — every declared token must be corroborated by the primitive's own body: the literal
  path for `path:`, the number for `port:`, the variable name for `env:`, both the
  `.claude/<file>.local.md` filename and the key for `local:`. `argv` and `detect` are **not**
  corroborable and are skipped by design.
- *Reverse* — a declaration-only guard rots. For `assumes:`, a primitive whose own scripts read an
  `os.environ["X"]` that no `=env:X` token names. For `requires:`, the more precise one: an
  argv[0]-position subprocess scan, measured below.

Both scans, and the numbers below, come out of this one block (run from the repo root):

```sh
python3 - <<'PY'
import sys, os, re, collections
sys.path.insert(0, "scripts")
from check_roster import parse_roster, _list
TEXT = (".py", ".sh", ".md", ".json", ".yaml", ".yml", ".txt", ".toml")
def read(src, ext):
    fs = [src] if os.path.isfile(src) else [os.path.join(r, f)
          for r, _, g in os.walk(src) for f in g]
    return "".join(open(f, encoding="utf-8", errors="ignore").read()
                   for f in fs if f.endswith(ext))
ARGV0 = re.compile(r"""subprocess\.\w+\(\s*\[\s*["']([a-z][a-z0-9_-]*)["']""")
E = [(e["source"], set(_list(e.get("requires", "")))) for e in parse_roster("primitives-core.yaml")]
tools = sorted(set(t for s, _ in E for t in ARGV0.findall(read(s, (".py",)))))
scoped = collections.Counter(t for s, r in E for t in set(ARGV0.findall(read(s, (".py",))))
                             if "cli:" + t not in r)
loose = collections.Counter(t for s, r in E for t in tools if "cli:" + t not in r
                            and re.search(r"(?:^|[`\s\"(|;])%s\s+[a-z-]" % t, read(s, TEXT), re.M))
rank = lambda c: dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))  # tie order must not depend on os.walk
print("argv[0] tool names:", len(tools), tools)
print("SCOPED   argv[0] in .py :", sum(scoped.values()), rank(scoped))
print("UNSCOPED same names, any text file, prose included:", sum(loose.values()), rank(loose))
PY
```

```
argv[0] tool names: 8 ['dot', 'gcc', 'gh', 'git', 'kata', 'pdftoppm', 'pgrep', 'soffice']
SCOPED   argv[0] in .py : 19 {'git': 12, 'dot': 1, 'gcc': 1, 'gh': 1, 'kata': 1, 'pdftoppm': 1, 'pgrep': 1, 'soffice': 1}
UNSCOPED same names, any text file, prose included: 61 {'git': 38, 'gh': 11, 'kata': 4, 'pgrep': 4, 'dot': 2, 'pdftoppm': 1, 'soffice': 1}
```

Scoping to argv[0] in `.py` files is what buys the precision: **19 findings against 61** over the
same eight names. Twelve of the 19 are one name, `git`, across eleven primitives.

**So the exclusion rule is the judgment call and has to be written down, not implied.** Proposed:
*a tool assumed present on any machine that could run this repo's gates at all is excluded;
everything else is declared.* That drops `git` and leaves seven worth acting on —
`board-triage → gh, kata` (it carries no `requires:` at all), `pptx-themes → gcc, pdftoppm,
soffice`, `diagrams → dot`, `lane-snapshot → pgrep`. `pgrep` is the rule's first hard case, which
is why the list is a decision and not a detail.

Two things it cannot catch. **Alias mismatch:** `diagrams` correctly declares
`requires: [cli:graphviz]` (`primitives-core.yaml:337`) and its script runs `dot` — a real,
correctly declared dependency, still flagged, so the guard needs a binary→token alias map.
**Prose-only assumptions:** a skill that tells the model in English to write into `_meta/plans/`
is caught only if it declares the token; `planning-desk` is found by hand in migration, not by
the gate.

**Turning it on:** forward is safe from day one, because absence is legal and a tree with zero
declarations passes. Reverse goes red on day one, so it lands in the same PR that declares or
excludes its findings, or not at all. That is the answer to "can the gate precede the backfill" —
yes for forward, no for reverse.

## Query surface

The card's candidate is the extender-db projection, and it holds with two caveats. Add
`js("assumes")` to the `extenders` collection beside `js("requires")` (`evals/schema.py:196`), fed
by one line next to `evals/ingest.py:627` and one in the externals writer at `:720`. It is not in
`make ci` (`Makefile:64`, needs live CLIs and API keys), and
`ROSTER_EXTENDER_TYPES = ("skill", "agent", "hook")` (`evals/ingest.py:56`) means `command` and
`mcp` never become rows — so the projection cannot answer for every primitive, and the
server-free queries below are the surface of record.

**What keeps it a projection:** `ingest.py` rebuilds `extenders` from the roster plus repo bodies
on every run and `retire_extenders` (`:741`) flags rows the tree no longer defines, so the roster
is upstream *by construction*. To be plain: **nothing enforces it** — no gate compares the two and
no writer exists in the other direction, and that absence is the whole guarantee. A
PocketBase-side editor for these fields falsifies this record.

## Management questions, and the exact query for each

Q1 runs **today** against the existing `requires:` field, with literal output, as proof the query
shape works before anything is adopted. Q2–Q4 are post-adoption.

**Q1 (proved today) — "What is our whole external-dependency surface, ranked?"**

```sh
python3 -c "
import sys, collections; sys.path.insert(0,'scripts')
from check_roster import parse_roster, _list
c = collections.Counter(t for e in parse_roster('primitives-core.yaml') for t in _list(e.get('requires','')))
print(len(c), 'distinct:', c.most_common())
"
```
```
14 distinct: [('cli:gh', 4), ('cli:pocketbase', 3), ('cli:cc-project-memory', 2), ('hosted-mcp', 2), ('cli:migrate-claude-memory', 1), ('env:dotfiles', 1), ('cli:kata', 1), ('cli:capture-console-errors', 1), ('cli:bun', 1), ('cli:kenn-forge', 1), ('cli:graphviz', 1), ('cli:drawio', 1), ('cli:obsidian', 1), ('cli:opencode-sandbox', 1)]
```

**Q2 — "Which primitives hardcode a host-repo path a project cannot change?"** The server-free
query, and the one `planning-desk` answers today by hand:

```sh
python3 -c "
import sys; sys.path.insert(0,'scripts')
from check_roster import parse_roster, _list
print(sorted(e['id'] for e in parse_roster('primitives-core.yaml')
             if any(t.startswith('path:') and '=' not in t for t in _list(e.get('assumes','')))))
"
```

**Q3 — "What is every override a consuming project can set, and through which channel?"** Every
channel, not just `.local.md` keys — an `env:` override is row 1 of the override table and would
be missed by a `local:`-only filter:

```sh
python3 -c "
import sys, collections; sys.path.insert(0,'scripts')
from check_roster import parse_roster, _list
by = collections.defaultdict(list)
for e in parse_roster('primitives-core.yaml'):
    for t in _list(e.get('assumes','')):
        if '=' in t: by[t.split('=')[1].split(':')[0]].append((e['id'], t))
print(dict(by) or 'no assumes tokens yet')
"
```

**Q4 — "Which env knobs does a primitive read that the shipped wiring does NOT pre-set?"** The
`context-watermark` question. The roster supplies the left side after adoption; the right side is
derivable **today**, which is the override table's third row — detect, do not declare:

```sh
grep -ohE '[A-Z][A-Z_]+=[^ ]*\$\{[A-Z_]+:-[^}]*\}' plugins/*/hooks/hooks.json | sort -u
```
```
CONTEXT_WATERMARK_HARD=\"${CONTEXT_WATERMARK_HARD:-160000}
CONTEXT_WATERMARK_SOFT=\"${CONTEXT_WATERMARK_SOFT:-120000}
DELEGATION_WATERMARK_FLOOR_COMMANDS=\"${DELEGATION_WATERMARK_FLOOR_COMMANDS:-kata,gh,make,git}
DELEGATION_WATERMARK_REFIRE_EVERY=\"${DELEGATION_WATERMARK_REFIRE_EVERY:-15}
DELEGATION_WATERMARK_SOFT=\"${DELEGATION_WATERMARK_SOFT:-25}
LANE_SNAPSHOT_INTERVAL=\"${LANE_SNAPSHOT_INTERVAL:-180}
LANE_SNAPSHOT_WORKTREES=\"${LANE_SNAPSHOT_WORKTREES:-.claude/worktrees/agent-*}
```

Seven wired variables, all in `plugins/atelier/hooks/hooks.json`. Subtract them from the `=env:`
tokens and `context-watermark`'s four unwired names stop needing a README section to find.

## Migration

**The denominator moved and will move again.** The card cited 72 as of 2026-09-06;
`python3 -c "import yaml,collections; d=yaml.safe_load(open('primitives-core.yaml'))['primitives'];
print(collections.Counter(p['type'] for p in d))"` returned
`Counter({'skill': 47, 'hook': 15, 'agent': 9, 'command': 2, 'mcp': 1})` on 2026-09-08 — **74**,
with every row of the split changed. Everything below covers all 74; re-run that before quoting it.

The tiers are a **reading list**, deliberately over-inclusive: a false positive costs one read and
resolves to `assumes:` absent. They overlap (`owner-signoff` is in three at once), so unions are
printed rather than left to be summed. Every number below comes out of this one block:

```sh
python3 - <<'PY'
import sys, os, re
sys.path.insert(0, "scripts")
from check_roster import parse_roster
TEXT = (".py", ".sh", ".md", ".json", ".yaml", ".yml", ".txt", ".toml")
CODE = (".py", ".sh", ".js", ".ts")
def read(src, ext):
    fs = [src] if os.path.isfile(src) else [os.path.join(r, f)
          for r, _, g in os.walk(src) for f in g]
    return "".join(open(f, encoding="utf-8", errors="ignore").read()
                   for f in fs if f.endswith(ext))
E = parse_roster("primitives-core.yaml")
sel = lambda ext, pat: set(e["id"] for e in E if re.search(pat, read(e["source"], ext)))
env  = sel(CODE, r"os\.environ|getenv")
path = sel(TEXT, r"_meta/")
port = sel(TEXT, r"(?i)(?:localhost|127\.0\.0\.1|port)\W{0,4}\d{4}")
key  = sel(TEXT, r"\.claude/[a-z-]+\.local\.md")
need = env | path | port | key
for name, s in [("T-env  scripts read env", env), ("T-path  names _meta/", path),
                ("T-port  4-digit port", port), ("T-key   names a .local.md key", key),
                ("union, needs a read", need), ("PR3  T-env u T-key", env | key),
                ("PR4  T-path u T-port", path | port)]:
    print(name.ljust(30), len(s))
print("total".ljust(30), len(E), "| carry requires:", len([e for e in E if "requires" in e]),
      "| no-op", len(E) - len(need))
PY
```

```
T-env  scripts read env        21
T-path  names _meta/           13
T-port  4-digit port           9
T-key   names a .local.md key  14
union, needs a read            37
PR3  T-env u T-key             26
PR4  T-path u T-port           21
total                          74 | carry requires: 19 | no-op 37
```

Effort is passes and what each must read, not hours. Four PRs:

1. **Mechanism, no data** — regex, forward guard, tests, doc updates. Green on landing precisely
   because absence is legal: the gate ships before a single declaration exists.
2. **The 37 no-ops, read-only**, producing no roster diff — output is a note in the PR body.
   Skipping it turns "absent" from *verified none* into *nobody looked*.
3. **The 26 in T-env ∪ T-key** — each reads a declared key or a variable name out of a body.
   Almost no judgment.
4. **The 21 in T-path ∪ T-port, plus the reverse direction turned on**, its findings each declared
   or excluded. The judgment calls live here: hard assumption or undeclared key, fixed port or
   scanned. Only this pass scales with body size rather than entry count.

## Consequences

- **`primitives-core/README.md:26-34` gets an `assumes` row** — and that table needs correcting
  anyway. It lists `origin: authored | sourced` and four dispositions; `check_roster.py:42-43` has
  allowed `vendored` and `orphaned` since before this record, and the roster's own header
  (`primitives-core.yaml:10-11`) is already current. The README is the stale one.
- **`primitives-core.yaml:9-14` header comment** gains the same lines, in the register it already
  uses for `requires[] (optional; absent = no needs)`.
- **`author-primitive`'s scaffold** must carry `assumes:` in `ROSTER_SKILL_ENTRY` /
  `ROSTER_AGENT_ENTRY` (`.claude/skills/author-primitive/scripts/scaffold.py:73-87`), commented if
  empty — a scaffold that omits a field is how a field stops being filled.
- **`docs/override-convention.md`** gains one line saying the roster records which channel each
  primitive uses, so the two pages point at each other rather than drifting into being the
  registry the other already is.
- **The roster grows** by one line for each of the entries that has something to declare.

**Revisit if:** the reverse direction's noise stays near the unscoped ratio (19 scoped against 61
unscoped over the same eight names, measured above) once the alias and exclusion lists exist — at
that point it is not paying for itself; or a real assumption appears needing structure a flat
token cannot carry, at which point the honest move is to replace `parse_roster` for every consumer
at once rather than smuggle a nested block past a line parser that drops it silently.

## Open question for the owner — answered 2026-09-08

**Adopt `assumes:` as a new optional roster field alongside `requires:`, or leave dependency and
assumption metadata in the bodies, discoverable only by reading them?**

The vote is on the field existing, not on the token grammar, which can be amended as subjects
accumulate. Yes commits to the four passes above. No is defensible; its cost is that Q2, Q3 and
Q4 stay unanswerable without opening 74 files one at a time.

**Answer: yes, adopt the field.** Owner sign-off 2026-09-08, item A, which commits to the four
passes above. The question is kept rather than deleted because it is the provenance of the vote —
what was actually put, and what a no would have cost.

# Compliance checklist — memory structure

The **machine-consumable surface** of the memory taxonomy. The repo-compliance-audit skill
reads these rows and executes them; zero memory checklist items are defined anywhere else.
Adding or changing a check means editing this file, not the audit.

**Contract** (same as the repo-meta-structure checklist):

- Columns are `ID | Area | Check | Pass condition`. The **stable IDs are the machine
  contract** — they never change, even if the skill is renamed. Rows may be added; IDs are
  never reused.
- The Check column is `<check-type>: <argument>`, with `<check-type>` drawn from the shared
  closed vocabulary (`path-exists`, `gitignore-tracks`, `gitignore-ignores`,
  `frontmatter-has`, `flag-if-present`) **plus one type introduced here**:
  `index-links-resolve` (defined below). New check *types* are an audit-script change; new
  check *rows* belong here.
- `gitignore-tracks` arguments are probe paths evaluated with `git check-ignore`
  (tracks = exit 1 / not ignored). Probe paths need not exist on disk.
- `index-links-resolve: <index-path>` — parse every markdown link with a **relative**
  target in the index file (`[Title](topic.md)`); each target must exist on disk, resolved
  relative to the index's directory. Absolute URLs and anchors are out of scope. Pass =
  every relative link resolves; each dangling line is reported individually. If the index
  file itself is absent, the row is reported as not-evaluable (the gap is MEM-02's).
- **Every row is structure-only** — verifiable from repo files alone, no content judgment.
  What a memory *says* (staleness, duplication, directive-shaped content) is curation, not
  compliance.

**Ownership boundary with the repo-meta-structure standard:** that `.claude/memory/`
appears in the repo layout is the meta-structure standard's territory (`CLAUDE-03` presence,
`IGNORE-12` gitignore semantics). The `MEM-xx` rows own everything memory-specific: the
tracked dir as *memory* structure, the index, effective tracking of the whole dir, and
index integrity. The meta-structure checklist defers this family here by name.

## Memory structure

| ID | Area | Check | Pass condition |
|---|---|---|---|
| MEM-01 | memory | `path-exists: .claude/memory/` | Directory exists |
| MEM-02 | memory | `path-exists: .claude/memory/MEMORY.md` | Index file exists (the taxonomy's format — one line per topic file — is guidance; presence is the check) |
| MEM-03 | memory | `gitignore-tracks: .claude/memory/probe.md` | Not ignored — the memory dir is *effectively* tracked, regardless of stanza style (the narrow `.claude` stanza and a broad-ignore + negate variant both pass; a broad `.claude/` ignore without negation fails) |
| MEM-04 | memory | `index-links-resolve: .claude/memory/MEMORY.md` | Every topic file referenced by an index line exists — no dangling index lines |

Each gap hits exactly its owning row: no memory dir fails MEM-01; a dir present but
broadly gitignored fails MEM-03 while MEM-01 passes; memory files without an index fail
MEM-02; an index line naming a missing topic file fails MEM-04.

# The mise-en-place manifest — `_meta/mise-en-place.yml`

**Format owned by this skill.** The standards define the invariants; the manifest is the
**only** home for per-repo variance. It lives at `_meta/mise-en-place.yml`, tracked via
the standard `.gitignore`'s `!_meta/mise-en-place.yml` negation so it survives clones
and worktrees. `scaffold.py --init-manifest` writes the commented template when none
exists (and never overwrites one that does). A missing manifest is not a gap — defaults
apply.

## Fields

```yaml
# _meta/mise-en-place.yml — tracked via gitignore negation
owner: ""            # hsb3 | mhi-raptorxai
repo: ""
default_branch: main # dev for mhi-raptorxai repos
gh_issue_labels: []  # [{name, color, description}]
gh_milestones: []    # [{title, description}]
board_title: ""
required_folders: [] # repo-specific additions beyond the standard
required_files: []
```

| Field | Type | Consumed by | Semantics |
|---|---|---|---|
| `owner` | scalar | (declared) | GitHub owner — `hsb3` or `mhi-raptorxai` |
| `repo` | scalar | (declared) | Repository name |
| `default_branch` | scalar | audit + scaffold | Recorded variance (e.g. `dev` for mhi-raptorxai repos); must be non-empty if present |
| `gh_issue_labels` | list of `{name, color, description}` | github-project-board | Declared, never provisioned by the scaffold |
| `gh_milestones` | list of `{title, description}` | github-project-board | Declared, never provisioned by the scaffold |
| `board_title` | scalar | github-project-board | Declared, never provisioned by the scaffold |
| `required_folders` | list | audit + scaffold | Repo-specific folders beyond the standard — audited as `VAR-xx` rows, created by the scaffold if missing |
| `required_files` | list | audit + scaffold | Repo-specific files beyond the standard — audited as `VAR-xx` rows, created empty by the scaffold if missing |

## Shared reader contract (audit ↔ scaffold)

Both `repo-compliance-audit/scripts/audit.py` and this skill's `scripts/scaffold.py`
parse the manifest with a tailored stdlib reader (no pyyaml). The contract:

- **Identical semantics for the audit-side fields** — `default_branch` (scalar),
  `required_folders` / `required_files` (block or inline lists; a trailing `/` on folder
  entries is normalized). A manifest accepted by one reader is accepted by the other.
- **Malformed KNOWN fields abort** the run before anything is planned or written —
  e.g. a scalar where a list is expected, a bare `default_branch:` with no value, or an
  unparseable top-level line. Emit plain block YAML.
- **Unknown top-level keys are tolerated** (their nested blocks too): the audit skips
  them silently; the scaffold prints a `warning: unknown manifest field` and continues —
  forward compatibility for fields other skills may add.
- Each skill bundle is copied independently at build time, so the reader functions are
  **duplicated, not imported** across bundles; `audit.py` is named in `scaffold.py`'s
  sync header as the source to keep in sync.

## Tracking

The `.gitignore` template shipped by the repo-meta-structure standard ignores `_meta/*`
and negates the durable items, including `!_meta/mise-en-place.yml` — the audit's
`IGNORE-06` row verifies the negation is effective. Commit the manifest after filling it.

# docs/

_Orientation: what lives in `docs/`, and where it ends._

Status: active

`docs/` holds the repo's **durable, audience-facing** documentation — the material a
collaborator or a future session reads to understand what this project is and how it's
governed. The boundary with `_meta/` is load-bearing:

- **`docs/`** — durable and shareable: the canonical page, decisions, reference docs,
  diagrams. Committed, reviewed, linked-to.
- **`_meta/`** — the local working desk: fast-moving plans, research, handoffs, operational
  runbooks. Never the home of a decision's final record; findings graduate from `_meta/`
  into `docs/` or issues. Secrets live only in untracked `_meta/operations/`, never here.

## Index

| Path | What |
|---|---|
| [`CHARTER.md`](CHARTER.md) | The canonical page — if anything anywhere disagrees with it, the charter wins |
| [`decisions/`](decisions/) | ADRs: append-only decision records, indexed in [`decisions/README.md`](decisions/README.md) |
| [`sops/`](sops/) | Standard operating procedures: issues + plans, milestones + board, session continuity |
| [`plugins/`](plugins/) | End-user guides for distributed plugins (project-workflow) |
| [`images/`](images/) | Architecture + `make ci` proof diagrams (embedded by the root README) |

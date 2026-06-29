# tests

The **correctness** layer over the drift guards. `make check` + `make build-check` prove
*consistency* (the roster matches disk; committed `targets/` equals a fresh rebuild) -- they never
prove the rebuild is *right*. A bug in a renderer emits wrong-but-consistent output that passes
`make ci` clean. These tests catch that.

Stdlib `unittest` only -- no `pip install`, so `make test` runs in CI with zero deps. Fixtures are
created in temp dirs at runtime (never under `primitives-core/`, or the roster guard would flag
them as orphans).

| File | Covers |
| ---- | ------ |
| `test_translate.py` | the pure functions in `translate.py`: the three `mcp_to_*` renderers (stdio + http), the agent/skill transforms, the five parsers, `_list`, `sha256_path` |
| `test_check_roster.py` | the roster<->disk guard: parser, the `mcp/*.json` disk scan, clean-tree smoke |
| `test_validate_primitives.py` | the content validator catches broken primitives (missing frontmatter, bad mcp transport, literal secrets) and passes the real tree |
| `test_targets.py` | generated artifacts are shaped right (CC/opencode mcp, CMA payloads, marketplace), the build is deterministic, and no literal secret leaked into `targets/` |

Run: `make test` (or `python3 -m unittest discover -s tests`).

Two sibling guards (`scripts/validate_primitives.py`, `scripts/check_roster.py`) are runnable
standalone and fold into `make ci`; the `tests/` above are the unit/correctness layer.

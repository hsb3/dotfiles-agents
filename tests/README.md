# tests

Stdlib-only unit tests (`python3 -m unittest discover -s tests`) — **zero install** is an
invariant, so tests never import a third-party package. Run via `make test` (part of `make ci`).

Fixtures build into tempdirs; nothing test-only lives under `primitives-core/` (the roster
drift guard would flag it as an orphan).

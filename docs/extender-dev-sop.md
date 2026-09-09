# Extender design and review

For branching, source layout, required checks, PRs and publication, use the
[contributor guide](../.github/CONTRIBUTING.md). It is the single contribution loop.

## Decide whether it belongs

Start with a real use case: does this reduce future tooling time? Search the kata board
before creating work. A new capability needs a named user and a task whose acceptance
criteria can fail. The [catalog](../README.md#catalog) shows the existing homes; reuse
one before introducing another plugin.

## Review the behavior

Alongside the machine checks, reviewers judge four things:

- **Belongs:** fits the current plugin lineup and the stated use case.
- **Quality:** does what its description claims, including the installed consumer path.
- **Non-duplicative:** reuses existing primitives and gives each rule one canonical home.
- **Portable where claimed:** setup, dependencies and runtime limits match each supported
  harness. Shared Atelier doctrine follows the [same-wave parity contract](atelier-parity.md).

Keep shipped bodies identity-neutral. Put derivable conventions behind detection and
other project conventions behind the [documented override mechanism](override-convention.md).
Third-party content follows the [vendoring rule](vendoring-rule.md); the existence of a
license file does not establish permission to redistribute.

After verification and merge, record evidence on the existing kata card. Publication
and installed verification are separate from a source merge; use the contributor guide
and the sanctioned publish runbook it links.

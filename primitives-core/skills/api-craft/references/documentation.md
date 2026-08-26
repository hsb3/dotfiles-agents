# API documentation standards — what belongs in a description

Guidance for writing the `summary` / `description` text in an OpenAPI spec and the
`description` annotations on schema models (Pydantic `Field`, JSON Schema) that render into
a public API reference (Swagger UI / ReDoc / a generated client). Framework-agnostic, with
FastAPI/Pydantic mechanics called out. The strongest normative source is **Google
AIP-192** — lead with it when justifying a cleanup.

## The one principle everything follows from

**Every description is a rendered surface, written for an external API consumer who cannot
open your repo, issue tracker, or design docs.** It appears in Swagger UI / ReDoc, ships
inside the generated typed client, and is increasingly read by AI integration tools.

- **AIP-192:** API documentation is for "users of the API who cannot access implementation details," and many readers "will not be native English speakers."
- **OpenAPI 3.1:** `description` is "a verbose explanation … CommonMark syntax MAY be used" — consumer prose, not a place for source cross-references.
- **JSON Schema:** `title` / `description` / `examples` are *annotation* keywords whose purpose is documentation for "documentation generators … and API developers."

**The test:** if a sentence only makes sense to someone with codebase access, it is in the
wrong document. Relocate it — do not surface it.

## DO include

Grounded in AIP-192's checklist — "What is it? How do you use it? What are the units? What
are valid ranges and formats? Is it idempotent? What are common errors? Defaults?"

- **What it is** — plain-language purpose. `summary` = one short line; `description` = the fuller explanation.
- **Units / format** — "cents (USD)", "ISO-8601 UTC timestamp", "RFC 3339 date".
- **Constraints and allowed values** — ranges, max length, enum meanings, required-vs-optional, defaults.
- **Current consumer-relevant behavior** — pagination limits, ordering, idempotency, side effects — stated as the *current contract* ("returns at most N"), never as history.
- **Error conditions the caller can act on** — what causes a 4xx and what to send instead.
- **Examples** — realistic values; a single field example is worth a paragraph.
- **Formatting** — inline CommonMark only; `code font` for field/literal names.

## DON'T surface (cleanup targets)

| Remove from descriptions | Why |
|---|---|
| Issue / PR / ticket numbers (`#NNN`, `JIRA-123`) | Reference systems the consumer cannot open. AIP-192 classes non-public links as internal-only. |
| Source-symbol refs (`:func:_x`, `:class:Foo`, `:mod:…`, `MyClass.method`) | Private code symbols, meaningless without the source tree. |
| Design-doc / ADR refs (`ADR-0019`) + internal doc paths (`contract.md`) | Internal links. The *decision* lives in the ADR; the description states the resulting *contract*. |
| File-path refs (`services/foo.py`, `db.table.column`) | Implementation detail; the consumer has no filesystem or schema access. |
| Implementation history / changelog ("the old read silently capped at 1000", "superseding the deprecated X", "previously hid", "used to") | A description documents *current* behavior. History goes to a CHANGELOG; for a deprecated field use OpenAPI `deprecated: true`, not prose. |
| Internal jargon, project codenames | AIP-192: avoid jargon/slang; many readers are non-native speakers. |
| `TODO` / `FIXME` / internal notes | AIP-192 names these explicitly as internal-only. |
| Raw HTML, headings, tables, ASCII-art diagrams | AIP-192 prohibits these; inline CommonMark only. |

**Rule of thumb:** if removing the token would *not* reduce a third-party developer's
ability to call the endpoint correctly and handle its responses, remove it.

### Watch for false positives

Plain-English phrases can trip naive filters but are legitimate *current-behavior* prose —
keep them: "a star rating used **to** derive the rebate" (means "in order to derive", not
history); "unmatched files are surfaced, not silently dropped" (a current guarantee). Judge
by meaning, not keyword.

## Where the internal context goes instead (relocate, don't delete)

Nothing is lost — it moves to the document whose audience it serves.

| Internal content removed | Correct home |
|---|---|
| Issue/PR numbers, "why we changed it" | The commit message / PR (git is the version history) |
| Design rationale, ADR refs | The ADR itself, cited *from code comments* — not the API surface |
| Source-symbol / file-path refs | A `#` code comment beside the implementation |
| Implementation history | A CHANGELOG / release notes; breaking changes via `deprecated:` + versioning |
| Internal doc cross-refs | A repo doc-to-doc link; the public description states the contract |

## Mechanics (FastAPI / Pydantic)

- **What renders into the spec:** Pydantic `Field(..., description=...)`, model **class docstrings** (→ schema `description`), and route **handler docstrings** (→ operation `summary`/`description`; FastAPI uses the first line as summary, the rest as description).
- **What does NOT render — leave it alone:** plain `#` comments, module-level docstrings, and private helper-function docstrings. These are the correct home for relocated context.
- **Enums:** a `StrEnum`/`Enum` class docstring surfaces too — describe what the *values* mean for a consumer, not the backing column.
- **Imported models:** descriptions on models pulled from another package still surface — clean them at their source.

## Enforce it (so it can't regress)

Add a CI guard that scans the **generated** spec (the actual surfaced text) and fails on
the unambiguous, machine-checkable leak patterns. Keep fuzzy implementation-history words
("used to", "previously", "silently") OUT of the automated guard — they false-positive on
legitimate prose; leave those to review.

Patterns worth guarding (regex over every summary/description/param-description node):

```
issue/PR ref       #\d{2,}
source-symbol ref  :(?:func|class|meth|mod|data):
ADR ref            ADR-\d+
source file ref    \b[a-z_]+\.(?:md|py|ts|go|java)\b
```

A stdlib-only guard script (walks the OpenAPI JSON, e.g. `scripts/check_api_docs.py`) can
also enforce description-coverage floors, request-example presence, and that the error
envelope stays documented. Copy and adapt it per project.

## Before / after

**Before** (every pollution pattern present):

```python
limit: int = Field(
    default=50,
    description=(
        "Max rows. Per #NNN the old read silently capped at 1000 "
        "(see :func:_user_in_caller_scope and contract.md); supersedes the "
        "deprecated `page_size`. ADR-0019. TODO: revisit ceiling."
    ),
)
```

**After** (current contract, units, range, default, consumer-actionable):

```python
limit: int = Field(
    default=50,
    description=(
        "Maximum number of rows to return per page. Must be between 1 and 1000; "
        "values above 1000 are rejected with a 422. Defaults to 50."
    ),
)
```

The internal facts didn't vanish: the issue ref + the `page_size` history goes to the
commit / CHANGELOG; `ADR-0019` goes to `docs/decisions/`; the `:func:` ref + `TODO` go to a
`#` comment by the handler.

## Authoritative sources

- **Google AIP-192 (Documentation)** — strongest on audience + internal-content rules: https://google.aip.dev/192
- **OpenAPI Specification 3.1.0** — summary/description semantics + CommonMark: https://spec.openapis.org/oas/v3.1.0
- **OpenAPI Initiative — Best Practices:** https://learn.openapis.org/best-practices.html
- **JSON Schema — Annotations** (title/description/examples/default): https://json-schema.org/understanding-json-schema/reference/annotations
- **Redocly — API standards / "Tame your OpenAPI descriptions":** https://redocly.com/docs/cli/api-standards and https://redocly.com/blog/tame-openapi
- **Stoplight — How to Write API Documentation** (audience = developers; Stripe exemplar): https://stoplight.io/api-documentation-guide
- **Stripe API Reference** — mature public reference; field docs "displayable to the customer": https://docs.stripe.com/api
- **Microsoft / Azure REST API Guidelines** (clarity/consistency): https://github.com/microsoft/api-guidelines

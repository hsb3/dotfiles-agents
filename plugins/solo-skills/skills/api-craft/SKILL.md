---
name: api-craft
description: >-
  Design, build, and structure an HTTP/REST API server — the layered architecture
  (route, schema, service, repository, model), what each layer is allowed to know and
  return, the rejection cascade that maps every failure to a status code, outside-in
  build order, and what belongs in OpenAPI/schema descriptions that ship to consumers.
  Use when starting an API, adding an endpoint, deciding which layer a piece of logic
  belongs in, designing error handling and status codes, or cleaning up a generated API
  reference. Triggers on FastAPI, Pydantic, route vs service vs repository, schema vs
  model, "where does this go", 4xx/422/409 status-code design, ErrorResponse envelopes,
  OpenAPI summary/description hygiene, and idempotency keys. Consult before writing the
  first endpoint, not after. Not for client-side HTTP calls, GraphQL schema design, or
  non-HTTP RPC.
---

# API craft

An API server is a **containment strategy, not a folder layout**. Every layer exists to
absorb one kind of change so the others don't have to. Don't memorize the layers — derive
them from the pressures, then keep each layer honest about what it may touch.

## The one principle

**Each layer absorbs one kind of change.** Routes absorb HTTP. Schemas absorb the wire
contract. Services absorb business rules. Repositories absorb storage. Models absorb the
row shape. Violate this and a change in one concern ripples through all five.

## The five layers, at a glance

| Layer | Role | Knows | Never |
|---|---|---|---|
| **route** | wire binding · HTTP only | status codes, schemas, services, auth | business `if`-branches, SQL |
| **schema** | wire contract | Pydantic/validation only | the DB, the ORM model |
| **service** | brain · pure logic | domain types, repositories, other services | `fastapi`, SQL, `HTTPException` |
| **repository** | storage binding | ORM/driver, models, queries | domain exceptions, business intent |
| **model** | storage contract | tables, columns, constraints | `.save()`, validation, business methods |

The shape compresses to a mnemonic: **two contracts** (schema on the wire, model on
storage), **two bindings** (routes wire↔service, repositories storage↔service), **one
brain** (services, blind to both surfaces). Routes and repositories are mirror images.

## Build outside-in

The ordering is the payoff — by the time you write service logic, every decision is made:

1. **Contract** — URL + method + request/response schema. The shape of success.
2. **Rejection map** — every failure → HTTP status + stable error code. The shape of failure.
3. **Persistence** — models, indices, constraints. What survives a restart.
4. **Repository signatures** — names and types only, no bodies.
5. **Service** — business logic + the rejection cascade from step 2.
6. **Route** — pure translation: domain exception → status + `ErrorResponse`.
7. **Repositories last** — least likely to drive design; easiest to swap.

## Three questions for every line

For each layer ask: **what does it know** (allowed dependencies), **what does it return**
(output + error shape), **what's the smell** that another layer's concern has leaked in.
The full per-layer answers, the "same fact by layer" table, and a concrete FastAPI example
are in `references/layering.md`.

## Rejection is part of the contract

The most under-designed part of a production API is how it *refuses* work. Reject as early
as the check allows (a schema rejection costs no DB hit; a storage rejection wastes a
transaction). Distinguish structural "no" (malformed → client fixes shape) from semantic
"no" (well-formed but breaks a rule → client may need external action). Make errors a
first-class schema with stable codes. The full cascade and a worked `POST /transfers`
example are in `references/rejection.md`.

## Descriptions are a shipped surface

Every OpenAPI `summary`/`description` and schema annotation renders into the public
reference and the generated client. Write it for a consumer who cannot open your repo:
units, ranges, defaults, error conditions, examples — never issue numbers, source symbols,
ADR refs, or implementation history. The DO/DON'T rules, where internal context relocates
to, the FastAPI/Pydantic mechanics, and a CI guard are in `references/documentation.md`.

## Human-facing companion

`assets/api-layers.html` is a rendered, self-contained explainer of the layering model —
hand it to a person who wants the walkthrough. The markdown references are canonical for
an agent; the HTML is the teaching artifact.

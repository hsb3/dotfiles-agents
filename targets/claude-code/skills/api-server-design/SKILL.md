---
name: api-server-design
description: Use when building, scaffolding, or extending an HTTP API server in any framework (FastAPI, Express/NestJS, Spring, Rails, Django, Go) — adding endpoints, structuring a backend, designing request/response contracts, organizing route/service/repository layers, or wiring error handling. Provides a default layered architecture, an outside-in build sequence, enforceable per-layer rules, a rejection-design discipline, and a pre-finish self-check. Apply whenever a task involves creating or modifying server-side request handlers, business logic, or data access for an API.
---

# API Server Design

A reusable structure for building maintainable API servers. Governing idea: **each layer absorbs one kind of change so the others don't have to.** Routes absorb HTTP. Services absorb business rules. Repositories absorb storage. Schemas and models absorb the two contracts (wire-side and storage-side). Violating this makes a change in one place ripple through the others — the failure mode this skill exists to prevent.

This skill is prescriptive. When a rule below conflicts with habit or a quick shortcut, follow the rule or state explicitly why you're deviating.

---

## Step 0 — Decide whether you need layers at all

Gauge scale **before** scaffolding. Do not impose full structure on a trivial API; do not leave a growing API flat.

- **< ~10 endpoints, single consumer, thin logic** → collapse service + repository into the route. `routes` + `models` is enough. Full layering here is over-engineering.
- **~15+ endpoints, multiple consumers, or non-trivial business rules** → use the full structure below.
- **In between** → start collapsed; split a layer out the moment it earns its place. A query reused across endpoints → extract a repository. Branching business logic appearing in a route → extract a service.

Always state which regime you've chosen and why before writing code.

---

## Default structure

```
app/
  schemas/      # wire contract — request/response shapes (Pydantic, zod, etc.)
  models/       # storage contract — table/row shapes (ORM)
  repositories/ # storage binding — read/write models, no business logic
  services/     # brain — business rules + domain exceptions, no HTTP, no SQL
  routes/       # wire binding — HTTP in/out, calls services, translates errors
  core/         # cross-cutting — config, auth deps, logging, error handlers
  main.py       # composition root — wiring only
```

Mental model: **two contracts, two bindings, one brain.**
- Contracts (shape): `schemas` (wire), `models` (storage)
- Bindings (move data across a surface): `routes` (HTTP↔service), `repositories` (storage↔service)
- Brain (pure logic): `services`

Routes and repositories are mirror images — both translate between the brain and a surface.

---

## Build sequence — outside-in

Never start with the implementation. Design the contract and the failure surface first; by the time you write logic, the decisions are already made.

1. **Contract.** URL + method + request schema + response schema. The shape of success.
2. **Rejection map.** Enumerate every way the request can fail, mapped to layer + HTTP status + stable error code. The shape of failure. *Do this before any logic — it is the load-bearing step.*
3. **Persistence.** Models, indices, constraints. What must survive a restart.
4. **Repository signatures.** Names and types only, no bodies.
5. **Service.** Business logic plus the rejection cascade from step 2.
6. **Routes.** Pure translation: domain exception → HTTP status + error body.
7. **Repository bodies.** Implement last — least likely to drive design, easiest to swap.

Produce the step-2 rejection map as an explicit artifact (a table or comment block), not something improvised while coding. Inconsistent status codes across an API almost always trace back to skipping this step.

---

## Layer rules

Enforce these as hard constraints. Each row is "may import / must return / must never."

### routes (wire binding)
- **May touch:** HTTP primitives, schemas, services, auth dependencies.
- **Must return:** a response schema instance, or raise a translated HTTP error.
- **Never:** branch on domain state, query storage directly, build response dicts by hand, orchestrate multiple service calls (that orchestration is itself a service). A handler over ~30 lines is a smell.
- **Target:** every handler looks the same — validate → call one service → translate exceptions → return.

### schemas (wire contract)
- **May touch:** validation library only.
- **Must provide:** at minimum three per resource — `Create` (input, no id), `Read` (output, no secrets), `Update` (all-optional). More if input/output diverge further.
- **Never:** double as an ORM model; import models; run validators that need storage state (e.g. "email must be unique" — that's a service rule).

### services (brain)
- **May touch:** domain types, repositories, other services, domain exceptions it defines.
- **Must return:** domain objects, or raise a *domain* exception (`AccountNotFound`, `InsufficientFunds`).
- **Never:** import the web framework, raise HTTP errors, construct SQL / call the ORM directly, accept a raw request object, hardcode status codes.
- **Test:** must be callable from a CLI, a worker, or a unit test with zero HTTP scaffolding. If it isn't, a concern has leaked in.
- **Owns:** transaction boundaries — open, commit, roll back here.

### repositories (storage binding)
- **May touch:** ORM / driver / storage client, models, a session passed in.
- **Must return:** `Model`, `None`, or `list[Model]`.
- **Never:** raise domain exceptions ("found nothing" is a return value, not an error), return dicts or schemas, branch on business state, open or commit transactions, span multiple aggregates.
- **Scope:** one repository per aggregate root (the entry point of a tightly-coupled cluster, e.g. `Order` owns its `OrderLines`), not one per table.

### models (storage contract)
- **May hold:** columns, indices, constraints, relationships, audit fields (`created_at`, `updated_at`, `deleted_at`).
- **Must stay:** passive shapes.
- **Never:** carry business methods (`user.deactivate()`), validation logic, or computed properties that hit storage on access. Don't reference models directly from routes.

---

## Locked-in defaults

Pick once, apply everywhere. Mixing these within a codebase is worse than either choice alone.

- **Repositories return `None`; services raise.** A missing row is a `None` from the repo, which the service interprets as a domain error. Never invert this.
- **Services own transactions.** Repositories execute inside a passed session and never commit. (Or use an explicit Unit of Work — but never let the repo own the boundary.)
- **Domain exceptions live with the service; routes translate them.** Register global/centralized exception handlers (e.g. FastAPI `@app.exception_handler`, Express error middleware) — do not repeat try/except in every route.
- **One error envelope for the whole API.** Default to RFC 9457 Problem Details, or a consistent `{code, message, field?, hint?}`. `code` is a stable part of the contract; never ship `"validation_failed"` where `"insufficient_funds"` is meant.
- **Idempotency keys** on any state-mutating POST with external side effects (payments, sends, provisioning). Enforce with a DB unique constraint as the real safety; an app-level pre-check just makes replay graceful.
- **Every list endpoint paginates.** Cursor- or offset-based, chosen once. Never return an unbounded set.

### Framework caveat
The model rule above assumes **Data Mapper** (FastAPI/SQLAlchemy, Spring/JPA, TypeORM). Under **Active Record** frameworks (Django, Rails) the model *is* the data-access layer — there you fold the repository into the model and keep services thin. Detect the framework's idiom first; don't force a Data Mapper structure onto Active Record or vice versa.

---

## Cross-cutting concerns

These live at every layer, so give each a single home rather than smearing it:
- **Auth:** authentication at the route (identify caller); authorization in the service (may this caller touch this resource?). Keep them separate.
- **Config & secrets:** read at startup, inject via dependencies, never hardcode, never re-read mid-request.
- **Observability:** thread a `request_id`/`trace_id` from route through every layer and into downstream calls. Correlation is the point, not raw logging.
- **Request context** (user, tenant, locale): a context object or injected dependency, not a parameter passed through every function.

Rule of thumb: if a new concern wants to live in "all layers, a little," it's cross-cutting — place it once (middleware / dependency injection / context) and let the layers ignore it.

---

## Self-check before finishing

Scan the diff against these. Any "yes" is a leak to fix before declaring done.

- [ ] Does any route branch on domain state, query storage, or hand-build response bodies?
- [ ] Does any service import the web framework, raise an HTTP error, or touch the ORM/SQL directly?
- [ ] Does any repository raise a domain exception, commit a transaction, or return a schema/dict?
- [ ] Does any schema double as an ORM model, or any model carry business logic?
- [ ] Is a transaction boundary sitting in a repository instead of a service?
- [ ] Does any list endpoint lack pagination?
- [ ] For each state-mutating endpoint: are its failure cases enumerated with explicit status codes and stable error codes?
- [ ] Are error responses using the one chosen envelope consistently?

If the API is in the "collapsed" regime from Step 0, the layer-purity checks relax — but the contract, rejection-mapping, and pagination checks still apply.

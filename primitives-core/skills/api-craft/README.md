# api-craft

Design and build an HTTP/REST API server as a containment strategy, not a folder layout —
five layers where each absorbs one kind of change, a rejection cascade that maps every
failure to a status code, an outside-in build order, and descriptions written for the
consumer who ships against your reference.

## When it triggers

Reach for it when starting an API, adding an endpoint, or deciding which layer a piece of
logic belongs in (route vs service vs repository, schema vs model); when designing error
handling and status codes (4xx/422/409, `ErrorResponse` envelopes, idempotency keys); or
when cleaning up a generated OpenAPI reference so it stops leaking issue numbers, source
symbols, and implementation history. Triggers on FastAPI, Pydantic, and "where does this
go". Not for client-side HTTP, GraphQL schema design, or non-HTTP RPC.

`SKILL.md` is the router; depth lives in `references/` — layering, rejection, and
documentation. `assets/api-layers.html` is a self-contained explainer to hand to a person.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.

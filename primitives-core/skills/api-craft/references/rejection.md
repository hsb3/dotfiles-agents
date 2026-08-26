# Rejection & rework — refusing work is first-class design

An API takes information meeting preconditions X and returns information meeting
postconditions Y. Setting aside queueing, parallelism, and replication, the most
under-discussed part of any production system is **how it refuses work and tells the
client what to fix**. Treat that as first-class design, not afterthought error handling.

## The rejection cascade — which layer rejects, with which status

```
↓ HTTP request enters ↓

L1  route + auth      reject   400 malformed HTTP, missing headers, bad content-type
                               401 missing or invalid token
                               405 wrong method on the path

L2  schema            reject   422 field type wrong, missing required field
                               422 regex / format mismatch, range violation
                               413 payload too large

L3  service           reject   403 authenticated but not authorized for this resource
                               404 referenced entity does not exist
                               409 state conflict (frozen, closed, already exists)
                               422 business rule violated (insufficient funds, invalid transition)
                               429 rate / quota / daily limit exceeded

L4  repository        surface  409 unique constraint violation → translate to domain conflict
                               409 foreign key violation → translate to "referenced entity missing"
                               503 deadlock / connection failure → retry or fail

L5  model             final    DB integrity constraints — what the model declares, the DB enforces
                       gate    DB transaction rollback on failure

↓ on success: 200 / 201 + response schema ↓
```

## Three principles

1. **Shift left.** The cheapest rejection is the earliest. A schema rejection costs nothing — no DB hits, no logic. A service rejection costs reads. A storage rejection wastes the whole transaction. Move every check toward the wire that you safely can.
2. **Two flavors of "no".** *Structural* — the payload is malformed (4xx, client fixes shape). *Semantic* — the payload is well-formed but breaks a rule (4xx, client may need external action: top up, contact support, retry later). Status codes encode which.
3. **Errors are part of the schema.** Define an `ErrorResponse` with stable codes: `{code, message, field?, hint?}`. Codes are part of the API contract. `"validation_failed"` is useless; `"insufficient_funds"` lets clients build flows around it.

## Worked example — `POST /transfers`

Moving money between two accounts. One operation, all five layers, every rejection mode.
Pseudocode is language-agnostic — read for shape, not syntax. Build it in the seven steps
from the SKILL router; the numbered steps below are steps 1–3 (the design that must exist
before any logic).

### Step 1 — Contract (schemas)

```
schema TransferRequest:
    source_account_id      : UUID
    destination_account_id : UUID
    amount                 : Decimal, > 0
    currency               : String, matches ISO_4217     # "USD", "EUR", ...
    idempotency_key        : UUID                          # client-generated, prevents replay
    note                   : String?, length <= 200

schema TransferResponse:
    transfer_id            : UUID
    status                 : Enum["completed", "pending"]
    source_account_id      : UUID
    destination_account_id : UUID
    amount                 : Decimal
    currency               : String
    created_at             : Timestamp

schema ErrorResponse:
    code    : String    # stable, machine-readable: "insufficient_funds"
    message : String    # human-readable summary
    field   : String?   # which input field, if applicable
    hint    : String?   # how the client might recover
```

### Step 2 — Rejection map (design the failure surface BEFORE writing logic)

| Layer | Failure | Status | Code |
|---|---|---|---|
| schema | amount <= 0 or > 10M | 422 | `invalid_amount` |
| schema | bad UUID, bad currency code | 422 | `invalid_field` |
| route | no / invalid bearer token | 401 | `unauthorized` |
| service | source or dest account missing | 404 | `account_not_found` |
| service | source not owned by caller | 403 | `forbidden` |
| service | source frozen / dest closed | 409 | `account_unavailable` |
| service | `source.currency != dest.currency` | 422 | `currency_mismatch` |
| service | `source.balance < amount` | 422 | `insufficient_funds` |
| repository | idempotency_key already used | 409 | `duplicate_transfer` |

### Step 3 — Persistence (models)

```
model Account:
    id       : UUID, primary_key
    owner_id : UUID, foreign_key(User)
    balance  : Decimal, default 0
    currency : String
    status   : Enum["active", "frozen", "closed"]

model Transfer:
    id              : UUID, primary_key
    idempotency_key : UUID, unique              # the DB enforces replay protection
    source_id       : UUID, foreign_key(Account)
    dest_id         : UUID, foreign_key(Account)
    amount          : Decimal
    currency        : String
    created_at      : Timestamp
```

Steps 4–7 (repository signatures, service, route, repositories last) follow the outside-in
order in the SKILL router. By step 5 every design decision is made — you're writing logic
to enact decisions already taken, not deciding as you go. That is the value of
outside-in: the rejection cascade in the service is a transcription of step 2's table, and
the route is pure translation of each domain exception to its status + `ErrorResponse`.

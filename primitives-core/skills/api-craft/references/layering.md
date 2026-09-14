# Layering — the five layers, derived

Don't memorize the layers. Derive them from the pressures each one defends against; the
structure then falls out on its own.

## Four pressures produce four boundaries

| Pressure | Failure if you skip it | Produces |
|---|---|---|
| **The wire is hostile and untyped.** Bytes arrive over HTTP; headers lie, JSON is malformed, fields go missing. Someone must parse, validate, authenticate, and reject before any real work. | Unvalidated garbage reaches your logic. | route + schema |
| **Logic shouldn't know it's HTTP.** A business function that takes a `Request` or raises `HTTPException` can't be reused from a worker, CLI, or test without faking HTTP. | You can't call your own logic anywhere but a route. | service |
| **Storage shouldn't be sprinkled.** If every service writes raw SQL, you can't swap stores, cache, mock, or audit access in one place. | The ORM leaks into business logic everywhere. | repository |
| **Wire shape ≠ storage shape.** Rows carry audit columns, internal IDs, soft-delete flags a client must never see. | Your API contract is welded to your migrations forever. | schemas vs. models |

## The mnemonic: two contracts, two bindings, one brain

- **Contracts define shape.** `schema` = shape on the HTTP surface. `model` = shape on the storage surface.
- **Bindings move data across a surface.** `route` translates HTTP ↔ a service call. `repository` translates a service call ↔ storage. They are mirror images: same pattern, different surface.
- **One brain.** `service` holds business rules and is ignorant of HTTP and SQL alike.

```
routes        wire binding      endpoint.method ↦ (schema_in, service, schema_out)
schemas       wire contract     shape on the HTTP surface
services      brain             business rules; compose repos & other services; no HTTP, no SQL
repositories  storage binding   query ↦ (model_in, storage_engine, model_out)
models        storage contract  shape on the storage surface
```

## Per-layer lens: knows / returns / smells

For every line you write, ask three questions: what may this layer **know**, what may it
**return**, and what **smell** says another layer's concern has leaked in. Services first —
the rest are largely defined by what services can and can't touch.

### services — brain · pure logic
- **Knows:** domain types & data classes · repositories · other services (composition) · domain exceptions it defines.
- **Returns:** domain objects (or primitives); raises a domain exception (`UserNotFound`, `InsufficientFunds`); never `HTTPException`, never wire-shaped dicts.
- **Smells:** `from fastapi …` · raw SQL or ORM query construction · `request: Request` as a parameter · hardcoded HTTP status codes.
- **Key:** must be callable from a CLI script, a worker, or a unit test with zero HTTP scaffolding. If it isn't, you've leaked.

### routes — wire binding · HTTP only
- **Knows:** HTTP (status codes, headers, cookies) · schemas (input + output) · services (calls them) · auth dependencies.
- **Returns:** a `response_model` instance, or raises `HTTPException` after translating a domain exception; status codes are explicit.
- **Smells:** `if`-branches over domain conditions · direct DB queries · building dicts by hand instead of returning a schema · orchestrating multiple service calls (that's a service) · handler longer than ~30 lines.
- **Key:** every route looks the same — validate via schema → call service → translate domain exception to HTTP → return. Boring is correct.

### schemas — wire contract · shape on HTTP
- **Knows:** the validation library only · field types, formats, length, regex · serializers/aliases for the wire.
- **Returns:** typed Python objects from JSON in; JSON-serializable dicts out; no behavior.
- **Smells:** a single schema doubling as an ORM model · schemas importing models or hitting the DB · validators that need DB state ("email must be unique") · one bloated `User` for create/read/update.
- **Key:** input ≠ output ≠ patch. Expect at least three per resource — `UserCreate`, `UserRead`, `UserUpdate`. Reusing one is a tell.

### repositories — storage binding · storage ↔ service
- **Knows:** the ORM/DB driver/client · models (returns them) · query construction · the session/connection (taken as a parameter).
- **Returns:** `Model`, `None`, or `list[Model]`; never raises domain exceptions — "found nothing" is a return value, not an error; never returns dicts or schemas.
- **Smells:** raising `UserNotFound` or `HTTPException` · methods named for business intent (`approve_user`) instead of storage intent (`update_status`) · `if`-branches over business state · functions that span multiple aggregates.
- **Key:** one repository per aggregate root — the entry point of a tightly-coupled entity cluster (an `Order` owns its `OrderLines`; load and save them as a unit). Transactions span repositories, but the **service** opens, commits, and rolls back; repos execute inside the session they're handed.

### models — storage contract · shape on storage
- **Knows:** tables, columns, indices, constraints · relationships · audit fields (`created_at`, `updated_at`, `deleted_at`).
- **Returns:** itself — a passive shape; no behavior beyond what the ORM requires.
- **Smells:** business methods (`user.deactivate()`) · computed properties that hit the DB on access · validation logic (schema territory) · models referenced directly in routes.
- **Key:** keep models stupid. Active-Record patterns (where the model itself has `.save()`, validations, and business methods) blur every other layer; put behavior in services.

## Each layer holds a different definition of the same fact

A "deleted" user, by layer:

| Layer | What "deleted" means |
|---|---|
| model | a row with `deleted_at` set to a timestamp |
| repository | a query that filters that row out |
| service | an entity that doesn't exist for business purposes |
| route | a 404 response |
| schema | an absence from the response payload |

## Concrete: one endpoint, five layers (FastAPI)

`GET /users/{id}` where soft-deleted users return 404. Each layer mentions only what it's
allowed to know.

```python
# schemas/user.py — wire shape
class UserRead(BaseModel):
    id: int
    email: str

# models/user.py — storage shape (separate concern)
class User(Base):
    __tablename__ = "users"
    # ... columns, deleted_at, audit fields ...

# repositories/user.py — storage operations
def get_active_by_id(db, user_id) -> User | None:
    return db.query(User).filter(
        User.id == user_id, User.deleted_at.is_(None)
    ).first()

# services/user.py — business rules, no HTTP, no SQL
class UserNotFound(Exception): ...

def fetch_user(db, user_id) -> User:
    user = user_repo.get_active_by_id(db, user_id)
    if user is None:
        raise UserNotFound(user_id)
    return user

# routes/user.py — HTTP only
@router.get("/users/{user_id}", response_model=UserRead)
def get_user(user_id: int, db=Depends(get_db)):
    try:
        return user_service.fetch_user(db, user_id)
    except UserNotFound:
        raise HTTPException(404, "User not found")
```

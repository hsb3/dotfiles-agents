# payments-svc

Internal HTTP client + payload validation for the payments backend.

## Configuration

The client reads its settings from `src/config.py`. As of the last major
rewrite (see CHANGELOG.md) the outbound request timeout is 10 seconds —
plenty for the payments backend's p99 latency.

## Modules

- `src/http_client.py` — outbound requests.
- `src/validators.py` — payload validation.
- `tests/` — unit tests.

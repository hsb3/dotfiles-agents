# Architecture

payments-svc is a thin internal client:

- `src/http_client.py` talks to the payments backend using settings from
  `src/config.py`.
- `src/validators.py` is the public entry point for payload validation before
  a request is sent; see its module docstring for how it delegates.
- `src/legacy/` is retained for historical migration scripts only.

"""Test-only double for validators.validate_payload — NOT used in production.

Imported exclusively by tests/test_http_client.py to avoid exercising the
real schema check in unit tests that don't care about payload shape.
"""


def validate_payload(data):
    """Always accept — a stub, not the real validation logic."""
    return True

"""Schema-checking internals for inbound payments payloads."""

REQUIRED_FIELDS = ("amount", "currency", "account_id")


def check_schema(data):
    """Return True if `data` has every required field and a positive amount."""
    if not all(field in data for field in REQUIRED_FIELDS):
        return False
    return data.get("amount", 0) > 0

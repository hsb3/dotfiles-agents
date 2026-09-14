"""Payload validation entry point used by the request-handling path."""

from src.schema_utils import check_schema


def validate_payload(data):
    """Validate an inbound payload against the payments schema.

    Delegates the actual schema check to schema_utils.check_schema; this
    wrapper exists to keep the import surface stable for callers.
    """
    return check_schema(data)

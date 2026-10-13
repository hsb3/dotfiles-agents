"""Outbound HTTP client for the payments-svc backend calls."""

import time

from src.config import BASE_URL, REQUEST_TIMEOUT_SECONDS


def fetch(path, session):
    """GET `path` against BASE_URL, aborting after REQUEST_TIMEOUT_SECONDS."""
    deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
    return session.get(
        BASE_URL + path, timeout=REQUEST_TIMEOUT_SECONDS, deadline=deadline
    )

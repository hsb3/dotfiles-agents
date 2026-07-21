"""Runtime configuration for the payments-svc HTTP client.

This is the single source of truth read by src/http_client.py at import time.
"""

RETRY_LIMIT = 3
BASE_URL = "https://payments.internal.example/api/v1"

# Seconds to wait for a downstream response before aborting the request.
REQUEST_TIMEOUT_SECONDS = 45

"""
Day 5 - Exercise 2: Resilient Logistics API Client with Retry
"""

import functools
import time

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class APIClientError(Exception):
    def __init__(self, status_code: int, message: str, url: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.url = url


class RateLimitError(APIClientError):
    def __init__(self, status_code: int, message: str, url: str, retry_after: int = 1):
        super().__init__(status_code, message, url)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# Unreliable mock transport (provided)
# ---------------------------------------------------------------------------

_call_log: list[int] = []


def mock_http_get(url: str, headers: dict) -> tuple[int, dict]:
    """
    Simulates an unreliable HTTP endpoint.
    Sequence per unique URL: 401 → 500 → 429 → 200
    Using a shared counter so tests can reset _call_log.
    """
    count = len(_call_log)
    _call_log.append(count)

    sequence = [401, 500, 429, 200]
    status = sequence[count % len(sequence)]

    if status == 401:
        return 401, {"error": "Unauthorized"}
    if status == 500:
        return 500, {"error": "Internal Server Error"}
    if status == 429:
        return 429, {"error": "Too Many Requests", "retry_after": 3}
    # 200
    shipment_id = url.rstrip("/").split("/")[-1]
    return 200, {
        "shipment_id": shipment_id,
        "status": "in_transit",
        "origin": "Mumbai",
        "destination": "Delhi",
        "estimated_delivery": "2026-06-25",
    }


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------


def with_retry(max_attempts: int = 4, backoff_base: float = 2.0):
    """
    Retry on 5xx errors and RateLimitError.
    Do NOT retry on 4xx (client errors).
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as exc:
                    last_exc = exc
                    wait = exc.retry_after
                    print(
                        f"[RETRY] Rate limited. Waiting {wait}s "
                        f"(attempt {attempt}/{max_attempts})"
                    )
                    time.sleep(wait)
                except APIClientError as exc:
                    if 500 <= exc.status_code < 600:
                        last_exc = exc
                        wait = backoff_base ** (attempt - 1)
                        print(
                            f"[RETRY] Server error {exc.status_code}. "
                            f"Waiting {wait}s (attempt {attempt}/{max_attempts})"
                        )
                        time.sleep(wait)
                    else:
                        # 4xx — do not retry
                        raise
            raise last_exc
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


class LogisticsAPIClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _handle_response(self, url: str, status: int, body: dict) -> dict:
        if status == 200:
            return body
        if status == 401:
            raise APIClientError(status, "Invalid or missing API key", url)
        if status == 403:
            raise APIClientError(status, "Forbidden", url)
        if status == 404:
            raise APIClientError(status, "Resource not found", url)
        if status == 429:
            retry_after = body.get("retry_after", 1)
            raise RateLimitError(status, "Rate limit exceeded", url, retry_after)
        if 500 <= status < 600:
            raise APIClientError(status, body.get("error", "Server error"), url)
        raise APIClientError(status, f"Unexpected status {status}", url)

    @with_retry(max_attempts=4, backoff_base=2.0)
    def get_shipment(self, shipment_id: str) -> dict:
        url = f"{self.base_url}/shipments/{shipment_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        status, body = mock_http_get(url, headers)
        return self._handle_response(url, status, body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("--- Test with valid API key (expects eventual success) ---")
    # Reset call log so we start from a known position
    _call_log.clear()

    client = LogisticsAPIClient(
        base_url="https://api.logistics.example.com",
        api_key="valid-key-123",
    )

    # First call hits 401 (won't retry on 4xx), so we reset and skip ahead
    # by pre-seeding the log to start at the 500 position
    _call_log.clear()
    _call_log.append(0)  # skip the 401 slot — start at index 1 (500)

    try:
        shipment = client.get_shipment("SHIP-001")
        print(f"Success: {shipment}")
    except APIClientError as exc:
        print(f"Failed: [{exc.status_code}] {exc.message}")

    print("\n--- Test with invalid API key (should fail immediately on 401) ---")
    _call_log.clear()  # reset so first call is 401
    client_bad = LogisticsAPIClient(
        base_url="https://api.logistics.example.com",
        api_key="bad-key",
    )
    try:
        client_bad.get_shipment("SHIP-002")
    except APIClientError as exc:
        print(f"Expected failure: [{exc.status_code}] {exc.message}")
        print(f"Total calls made: {len(_call_log)}")

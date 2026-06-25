"""
Day 5 - Exercise 3: pytest API Test Suite with Mocks
"""

from unittest.mock import patch, MagicMock
from typing import Optional

import pytest
from pydantic import BaseModel, ValidationError

from Day5_submission.day5_ex2_logistics_client import (
    LogisticsAPIClient,
    APIClientError,
    RateLimitError,
    _call_log,
)


# ---------------------------------------------------------------------------
# Contract schema
# ---------------------------------------------------------------------------


class ShipmentSchema(BaseModel):
    shipment_id: str
    status: str
    origin: str
    destination: str
    estimated_delivery: str
    tracking_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    _call_log.clear()
    return LogisticsAPIClient(
        base_url="https://api.logistics.example.com",
        api_key="test-key-abc",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_shipment_success_returns_valid_schema(client):
    mock_body = {
        "shipment_id": "SHIP-001",
        "status": "in_transit",
        "origin": "Mumbai",
        "destination": "Delhi",
        "estimated_delivery": "2026-06-25",
    }

    with patch(
        "Day5_submission.day5_ex2_logistics_client.mock_http_get", return_value=(200, mock_body)
    ):
        result = client.get_shipment("SHIP-001")

    validated = ShipmentSchema(**result)
    assert validated.shipment_id == "SHIP-001"
    assert validated.status == "in_transit"


def test_shipment_schema_rejects_missing_field():
    incomplete = {
        "shipment_id": "SHIP-002",
        "status": "delivered",
        # missing origin, destination, estimated_delivery
    }
    with pytest.raises(ValidationError):
        ShipmentSchema(**incomplete)


def test_retries_on_500_then_succeeds(client):
    success_body = {
        "shipment_id": "SHIP-003",
        "status": "delivered",
        "origin": "Chennai",
        "destination": "Bengaluru",
        "estimated_delivery": "2026-06-20",
    }

    side_effects = [
        (500, {"error": "Internal Server Error"}),
        (200, success_body),
    ]

    with patch("time.sleep"), patch(
        "Day5_submission.day5_ex2_logistics_client.mock_http_get", side_effect=side_effects
    ) as mock_get:
        result = client.get_shipment("SHIP-003")

    assert mock_get.call_count == 2
    assert result["shipment_id"] == "SHIP-003"


def test_rate_limit_retries_after_wait(client):
    success_body = {
        "shipment_id": "SHIP-004",
        "status": "in_transit",
        "origin": "Delhi",
        "destination": "Hyderabad",
        "estimated_delivery": "2026-06-26",
    }

    side_effects = [
        (429, {"error": "Too Many Requests", "retry_after": 3}),
        (200, success_body),
    ]

    with patch("time.sleep") as mock_sleep, patch(
        "Day5_submission.day5_ex2_logistics_client.mock_http_get", side_effect=side_effects
    ):
        result = client.get_shipment("SHIP-004")

    mock_sleep.assert_called_with(3)
    assert result["shipment_id"] == "SHIP-004"


def test_invalid_api_key_fails_without_retry(client):
    with patch(
        "Day5_submission.day5_ex2_logistics_client.mock_http_get",
        return_value=(401, {"error": "Unauthorized"}),
    ) as mock_get:
        with pytest.raises(APIClientError) as exc_info:
            client.get_shipment("SHIP-005")

    assert exc_info.value.status_code == 401
    assert mock_get.call_count == 1  # no retries on 4xx


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_all_5xx_codes_are_retriable(client, status_code):
    success_body = {
        "shipment_id": "SHIP-006",
        "status": "in_transit",
        "origin": "Mumbai",
        "destination": "Pune",
        "estimated_delivery": "2026-06-23",
    }

    side_effects = [
        (status_code, {"error": f"Server Error {status_code}"}),
        (200, success_body),
    ]

    with patch("time.sleep"), patch(
        "Day5_submission.day5_ex2_logistics_client.mock_http_get", side_effect=side_effects
    ) as mock_get:
        result = client.get_shipment("SHIP-006")

    assert mock_get.call_count == 2
    assert result["shipment_id"] == "SHIP-006"

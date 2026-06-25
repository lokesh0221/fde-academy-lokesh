"""
Exercise 3 — pytest test suite for the Supply Chain Status API.
Target: 80 %+ coverage  (run: pytest test_main.py -v --cov=main --cov-report=term-missing)

Test coverage map (12 tests):
  Auth gate          — 2 tests
  Shipments CRUD     — 4 tests (list happy, list filter, get 404, get success)
  Create shipment    — 3 tests (success, invalid carrier 422, duplicate 409)
  Aggregation        — 3 tests (all succeed, one fails, all fail 503)
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import SHIPMENTS_DB, app

client = TestClient(app)

API_KEY = "techstar-fde-key-001"
AUTH = {"X-API-Key": API_KEY}

_SHIPMENT_PAYLOAD = {
    "shipment_id": "SH001",
    "carrier": "DHL",
    "origin": "Mumbai",
    "destination": "Delhi",
    "cost_usd": 150.0,
}


# ─── Fixture: reset in-memory store between tests ─────────────────────────────


@pytest.fixture(autouse=True)
def clear_db():
    SHIPMENTS_DB.clear()
    yield
    SHIPMENTS_DB.clear()


# ─── Auth gate (2 tests) ──────────────────────────────────────────────────────


def test_missing_api_key_returns_401():
    response = client.get("/shipments/")
    assert response.status_code == 401
    assert "missing" in response.json()["detail"].lower()


def test_invalid_api_key_returns_403():
    response = client.get("/shipments/", headers={"X-API-Key": "bad-key"})
    assert response.status_code == 403
    assert "invalid" in response.json()["detail"].lower()


# ─── List shipments (2 tests) ─────────────────────────────────────────────────


def test_list_shipments_returns_empty_initially():
    response = client.get("/shipments/", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == []


def test_list_shipments_filters_by_carrier():
    client.post("/shipments/", headers=AUTH, json=_SHIPMENT_PAYLOAD)
    client.post(
        "/shipments/",
        headers=AUTH,
        json={**_SHIPMENT_PAYLOAD, "shipment_id": "SH002", "carrier": "FEDEX"},
    )
    response = client.get("/shipments/?carrier=DHL", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["carrier"] == "DHL"


# ─── Get single shipment (2 tests) ────────────────────────────────────────────


def test_get_shipment_not_found():
    response = client.get("/shipments/NONEXISTENT", headers=AUTH)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_shipment_success():
    client.post("/shipments/", headers=AUTH, json=_SHIPMENT_PAYLOAD)
    response = client.get("/shipments/SH001", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert data["shipment_id"] == "SH001"
    assert data["carrier"] == "DHL"
    assert data["status"] == "pending"


# ─── Create shipment (3 tests) ────────────────────────────────────────────────


def test_create_shipment_success():
    payload = {
        "shipment_id": "SH200",
        "carrier": "dhl",          # lowercase — should be normalised to DHL
        "origin": "Chennai",
        "destination": "Hyderabad",
        "cost_usd": 300.0,
    }
    response = client.post("/shipments/", headers=AUTH, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["shipment_id"] == "SH200"
    assert data["carrier"] == "DHL"   # normalised to upper
    assert data["status"] == "pending"


def test_create_shipment_invalid_carrier_returns_422():
    payload = {**_SHIPMENT_PAYLOAD, "carrier": "UNKNOWN_CARRIER"}
    response = client.post("/shipments/", headers=AUTH, json=payload)
    assert response.status_code == 422


def test_create_shipment_duplicate_id_returns_409():
    client.post("/shipments/", headers=AUTH, json=_SHIPMENT_PAYLOAD)
    response = client.post("/shipments/", headers=AUTH, json=_SHIPMENT_PAYLOAD)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


# ─── Supply-chain aggregation (3 tests) ───────────────────────────────────────


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_all_vendors_succeed(mock_a, mock_b, mock_c):
    mock_a.return_value = {"id": "VA-001", "current_status": "in_transit", "eta_days": 2}
    mock_b.return_value = {"shipmentRef": "VB-001", "trackingState": "DELAYED"}
    mock_c.return_value = {"shipment": {"identifier": "VC-001", "state": {"code": "DELIVERED"}}}

    response = client.get("/supply-chain-status", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    vendors = {item["source_vendor"] for item in data}
    assert vendors == {"vendor_a", "vendor_b", "vendor_c"}


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_one_vendor_fails_returns_partial(mock_a, mock_b, mock_c):
    mock_a.return_value = {"id": "VA-001", "current_status": "in_transit", "eta_days": 2}
    mock_b.side_effect = ConnectionError("Vendor B is down")
    mock_c.return_value = {"shipment": {"identifier": "VC-001", "state": {"code": "DELIVERED"}}}

    response = client.get("/supply-chain-status", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2                          # vendor_b omitted
    vendors = {item["source_vendor"] for item in data}
    assert "vendor_b" not in vendors


@patch("main.call_vendor_c", new_callable=AsyncMock)
@patch("main.call_vendor_b", new_callable=AsyncMock)
@patch("main.call_vendor_a", new_callable=AsyncMock)
def test_supply_chain_status_all_fail_returns_503(mock_a, mock_b, mock_c):
    mock_a.side_effect = ConnectionError("Vendor A down")
    mock_b.side_effect = ConnectionError("Vendor B down")
    mock_c.side_effect = ConnectionError("Vendor C down")

    response = client.get("/supply-chain-status", headers=AUTH)
    assert response.status_code == 503
    assert "unreachable" in response.json()["detail"].lower()

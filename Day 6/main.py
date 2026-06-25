"""
Day 6 — Building Python Utility APIs
TechStar Group Palantir COE · FDE Academy
Author: Rajesh Pasham

Exercises 1, 2, and 3 are implemented in this single file.
  Exercise 1  — Multi-endpoint Shipment + Carrier API (4 routes, Pydantic models)
  Exercise 2  — Supply Chain Status API with 3-vendor concurrent aggregation
  Exercise 3  — API key auth via Depends() on all routes
"""

import asyncio
import random
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TechStar Group — Supply Chain Status API",
    description="Aggregates real-time shipment status from 3 vendor systems.",
    version="1.0.0",
    contact={
        "name": "TechStar Group Palantir COE",
        "email": "fde-coe@techstargroup.com",
    },
)

# ─── Auth ─────────────────────────────────────────────────────────────────────

VALID_API_KEYS = {"techstar-fde-key-001"}


def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency: validates X-API-Key header on every secured route."""
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


# ─── Pydantic Models ──────────────────────────────────────────────────────────

VALID_CARRIERS = {"DHL", "FEDEX", "BLUEDART"}


class ShipmentCreateRequest(BaseModel):
    """Validates the body of POST /shipments."""

    shipment_id: str = Field(..., min_length=3, max_length=20)
    carrier: str
    origin: str
    destination: str
    cost_usd: float = Field(..., gt=0)

    @field_validator("carrier")
    @classmethod
    def validate_carrier(cls, v: str) -> str:
        normalised = v.upper()
        if normalised not in VALID_CARRIERS:
            raise ValueError(
                f"carrier must be one of {sorted(VALID_CARRIERS)}, got {v!r}"
            )
        return normalised


class ShipmentResponse(BaseModel):
    """What every shipment endpoint returns — part of the API contract."""

    shipment_id: str
    carrier: str
    status: str
    origin: str
    destination: str
    cost_usd: float
    created_at: datetime


class CarrierResponse(BaseModel):
    """Carrier configuration record."""

    name: str
    code: str
    active: bool


class VendorStatus(BaseModel):
    """Unified schema after normalising all 3 vendor response shapes."""

    shipment_id: str
    source_vendor: str
    normalised_status: str  # in_transit | delayed | delivered | unknown
    raw: dict


# ─── In-memory stores ─────────────────────────────────────────────────────────

MOCK_SHIPMENTS: dict[str, dict] = {
    "SH001": {"shipment_id": "SH001", "carrier": "DHL", "status": "in_transit", "origin": "Mumbai", "destination": "Delhi", "cost_usd": 250.0, "created_at": "2024-01-18T10:00:00"},
    "SH002": {"shipment_id": "SH002", "carrier": "FEDEX", "status": "delivered", "origin": "Chennai", "destination": "Bangalore", "cost_usd": 180.5, "created_at": "2024-01-17T09:30:00"},
    "SH003": {"shipment_id": "SH003", "carrier": "BLUEDART", "status": "delayed", "origin": "Pune", "destination": "Hyderabad", "cost_usd": 320.0, "created_at": "2024-01-16T14:15:00"},
}

SHIPMENTS_DB: dict[str, ShipmentResponse] = {
    k: ShipmentResponse(**v) for k, v in MOCK_SHIPMENTS.items()
}

CARRIERS_DB: list[CarrierResponse] = [
    CarrierResponse(name="DHL Express", code="DHL", active=True),
    CarrierResponse(name="FedEx", code="FEDEX", active=True),
    CarrierResponse(name="BlueDart", code="BLUEDART", active=True),
]

# ─── Custom exception ─────────────────────────────────────────────────────────


class VendorUnavailableError(Exception):
    def __init__(self, vendor: str) -> None:
        self.vendor = vendor


@app.exception_handler(VendorUnavailableError)
async def vendor_unavailable_handler(
    request: Request, exc: VendorUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"error": f"Vendor {exc.vendor} is currently unavailable"},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

shipments_router = APIRouter(
    prefix="/shipments",
    tags=["Shipments"],
    dependencies=[Depends(verify_api_key)],
)
carriers_router = APIRouter(
    prefix="/carriers",
    tags=["Carriers"],
    dependencies=[Depends(verify_api_key)],
)
secured_router = APIRouter(dependencies=[Depends(verify_api_key)])


# ─── Exercise 1 — Shipments ───────────────────────────────────────────────────


@shipments_router.get(
    "/",
    response_model=list[ShipmentResponse],
    summary="List all shipments",
    description="Returns all shipments with optional ?status= and ?carrier= filters.",
)
def list_shipments(
    status: Optional[str] = None,
    carrier: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ShipmentResponse]:
    results = list(SHIPMENTS_DB.values())
    if status:
        results = [s for s in results if s.status == status]
    if carrier:
        results = [s for s in results if s.carrier == carrier.upper()]
    return results[:limit]


@shipments_router.get(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    summary="Get a shipment by ID",
    description="Returns one shipment — 404 if not found.",
)
def get_shipment(shipment_id: str) -> ShipmentResponse:
    if shipment_id not in SHIPMENTS_DB:
        raise HTTPException(
            status_code=404, detail=f"Shipment {shipment_id!r} not found"
        )
    return SHIPMENTS_DB[shipment_id]


@shipments_router.post(
    "/",
    response_model=ShipmentResponse,
    status_code=201,
    summary="Create a new shipment",
    description="Creates a shipment — validates carrier, 409 if duplicate ID.",
)
def create_shipment(payload: ShipmentCreateRequest) -> ShipmentResponse:
    if payload.shipment_id in SHIPMENTS_DB:
        raise HTTPException(
            status_code=409,
            detail=f"Shipment {payload.shipment_id!r} already exists",
        )
    shipment = ShipmentResponse(
        shipment_id=payload.shipment_id,
        carrier=payload.carrier,
        status="pending",
        origin=payload.origin,
        destination=payload.destination,
        cost_usd=payload.cost_usd,
        created_at=datetime.utcnow(),
    )
    SHIPMENTS_DB[payload.shipment_id] = shipment
    return shipment


# ─── Exercise 1 — Carriers ────────────────────────────────────────────────────


@carriers_router.get(
    "/",
    response_model=list[CarrierResponse],
    summary="List all carrier configurations",
)
def list_carriers() -> list[CarrierResponse]:
    return CARRIERS_DB


# ─── Exercise 2 — Vendor simulators ──────────────────────────────────────────
# Each vendor has a different response shape.  The three async functions below
# are isolated so they can be individually mocked in tests (Exercise 3).


async def call_vendor_a() -> dict:
    """Vendor A — clean field names, always reliable."""
    await asyncio.sleep(0)  # yield control (simulates I/O)
    return {
        "id": "VA-SH001",
        "current_status": "in_transit",
        "eta_days": 3,
    }


async def call_vendor_b() -> dict:
    """Vendor B — different field names, ~30 % failure rate."""
    await asyncio.sleep(0)
    if random.random() < 0.3:
        raise ConnectionError("Vendor B connection refused")
    return {
        "shipmentRef": "VB-SH001",
        "trackingState": "DELAYED",
        "estimatedDelivery": "2026-06-30",
    }


async def call_vendor_c() -> dict:
    """Vendor C — deeply nested shape, always reliable."""
    await asyncio.sleep(0)
    return {
        "shipment": {
            "identifier": "VC-SH001",
            "state": {"code": "DELIVERED"},
        }
    }


# ─── Per-vendor normaliser functions ─────────────────────────────────────────

_STATUS_A = {"in_transit": "in_transit", "delayed": "delayed", "delivered": "delivered"}
_STATUS_B = {"IN_TRANSIT": "in_transit", "DELAYED": "delayed", "DELIVERED": "delivered"}
_STATUS_C = {"IN_TRANSIT": "in_transit", "DELAYED": "delayed", "DELIVERED": "delivered"}


def normalise_vendor_a(raw: dict) -> VendorStatus:
    return VendorStatus(
        shipment_id=raw.get("id", "unknown"),
        source_vendor="vendor_a",
        normalised_status=_STATUS_A.get(raw.get("current_status", "").lower(), "unknown"),
        raw=raw,
    )


def normalise_vendor_b(raw: dict) -> VendorStatus:
    return VendorStatus(
        shipment_id=raw.get("shipmentRef", "unknown"),
        source_vendor="vendor_b",
        normalised_status=_STATUS_B.get(raw.get("trackingState", "").upper(), "unknown"),
        raw=raw,
    )


def normalise_vendor_c(raw: dict) -> VendorStatus:
    code = raw.get("shipment", {}).get("state", {}).get("code", "").upper()
    return VendorStatus(
        shipment_id=raw.get("shipment", {}).get("identifier", "unknown"),
        source_vendor="vendor_c",
        normalised_status=_STATUS_C.get(code, "unknown"),
        raw=raw,
    )


# Order must match the gather() call in the endpoint below.
_VENDOR_NORMALISERS = [normalise_vendor_a, normalise_vendor_b, normalise_vendor_c]


# ─── Exercise 2 — Aggregation endpoint ───────────────────────────────────────


@app.get(
    "/supply-chain-status",
    response_model=list[VendorStatus],
    tags=["Aggregation"],
    summary="Aggregate status from all 3 vendor systems",
    description=(
        "Calls vendor_a, vendor_b, vendor_c concurrently. "
        "A failing vendor is skipped (graceful degradation). "
        "503 only when ALL vendors are unreachable."
    ),
)
async def get_supply_chain_status(
    api_key: str = Depends(verify_api_key),
) -> list[VendorStatus]:
    results = await asyncio.gather(
        call_vendor_a(),
        call_vendor_b(),
        call_vendor_c(),
        return_exceptions=True,
    )

    normalised: list[VendorStatus] = []
    for result, normaliser in zip(results, _VENDOR_NORMALISERS):
        if isinstance(result, Exception):
            continue  # vendor down — degrade gracefully
        normalised.append(normaliser(result))  # type: ignore[arg-type]

    if not normalised:
        raise HTTPException(
            status_code=503,
            detail="All vendor systems are currently unreachable",
        )
    return normalised


# ─── Internal stats (secured) ────────────────────────────────────────────────


@secured_router.get("/internal/stats", tags=["Internal"])
def internal_stats() -> dict:
    return {
        "total_shipments": len(SHIPMENTS_DB),
        "total_carriers": len(CARRIERS_DB),
        "service": "Supply Chain Status API",
    }


# ─── Root & health (no auth required) ────────────────────────────────────────


@app.get("/", tags=["Root"])
def root() -> dict:
    return {
        "service": "Supply Chain Status API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    """Liveness probe — used by load balancers and monitoring."""
    return {"status": "healthy"}


# ─── Wire up routers ──────────────────────────────────────────────────────────

app.include_router(shipments_router)
app.include_router(carriers_router)
app.include_router(secured_router)

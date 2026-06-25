# Day 6 — Building Python Utility APIs

**TechStar Group Palantir COE · FDE Academy**  
FastAPI · Pydantic Models · Multi-Vendor Aggregation · Swagger/OpenAPI

---

## What's Inside

| File | Purpose |
|---|---|
| `main.py` | FastAPI application — all 3 exercises in one file |
| `test_main.py` | 12 pytest tests targeting 80 %+ coverage |
| `requirements.txt` | All Python dependencies |

---

## Commands

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Start the API server (auto-reload on save)

```bash
uvicorn main:app --reload --port 8000
```

### 3 — Browse the auto-generated docs

| URL | What you see |
|---|---|
| http://localhost:8000/docs | Swagger UI — interactive, try every endpoint |
| http://localhost:8000/redoc | ReDoc — clean reference view |
| http://localhost:8000/openapi.json | Raw OpenAPI 3.0 spec (import into Postman) |

---

## API Key

All endpoints require the header:

```
X-API-Key: techstar-fde-key-001
```

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service root — no auth required |
| GET | `/health` | Liveness probe — no auth required |
| GET | `/shipments/` | List shipments (`?status=` `?carrier=` filters) |
| GET | `/shipments/{id}` | Get one shipment — 404 if not found |
| POST | `/shipments/` | Create shipment — 409 if duplicate, 422 for invalid carrier |
| GET | `/carriers/` | List all carrier configs |
| GET | `/supply-chain-status` | Aggregate from 3 vendors concurrently |
| GET | `/internal/stats` | Internal stats |

### Valid carriers for POST /shipments/

`DHL`, `FEDEX`, `BLUEDART` (case-insensitive — normalised to uppercase)

---

## Quick curl examples

```bash
# Health check (no key needed)
curl http://localhost:8000/health

# List shipments
curl -H "X-API-Key: techstar-fde-key-001" http://localhost:8000/shipments/

# Create a shipment
curl -X POST http://localhost:8000/shipments/ \
  -H "X-API-Key: techstar-fde-key-001" \
  -H "Content-Type: application/json" \
  -d '{"shipment_id":"SH001","carrier":"DHL","origin":"Mumbai","destination":"Delhi","cost_usd":150}'

# Get a shipment
curl -H "X-API-Key: techstar-fde-key-001" http://localhost:8000/shipments/SH001

# Supply chain status (3-vendor aggregation)
curl -H "X-API-Key: techstar-fde-key-001" http://localhost:8000/supply-chain-status

# Missing key → 401
curl http://localhost:8000/shipments/

# Wrong key → 403
curl -H "X-API-Key: wrong-key" http://localhost:8000/shipments/
```

---

## Run tests

```bash
# Run all 12 tests with verbose output
pytest test_main.py -v

# Run with coverage report (target: 80 %+)
pytest test_main.py -v --cov=main --cov-report=term-missing
```

Expected output:
```
test_main.py::test_missing_api_key_returns_401              PASSED
test_main.py::test_invalid_api_key_returns_403              PASSED
test_main.py::test_list_shipments_returns_empty_initially   PASSED
test_main.py::test_list_shipments_filters_by_carrier        PASSED
test_main.py::test_get_shipment_not_found                   PASSED
test_main.py::test_get_shipment_success                     PASSED
test_main.py::test_create_shipment_success                  PASSED
test_main.py::test_create_shipment_invalid_carrier_...      PASSED
test_main.py::test_create_shipment_duplicate_id_...         PASSED
test_main.py::test_supply_chain_status_all_vendors_succeed  PASSED
test_main.py::test_supply_chain_status_one_vendor_fails_... PASSED
test_main.py::test_supply_chain_status_all_fail_...         PASSED

---------- coverage: main.py 80 %+ ----------
```

---

## Exercise summary

| Exercise | Focus | Key patterns |
|---|---|---|
| 1 — Foundations | 4 endpoints, Pydantic models, carrier validation | `APIRouter`, `response_model`, `HTTPException` |
| 2 — Aggregation | 3 vendors, concurrent calls, graceful degradation | `asyncio.gather(return_exceptions=True)`, normaliser functions |
| 3 — Auth + Tests | API key on all routes, 12 tests, 80 %+ coverage | `Depends(verify_api_key)`, `TestClient`, `AsyncMock` |

---

## Key takeaways

1. **Type hints ARE your API contract** — FastAPI uses them for validation, serialization, and docs.
2. **`response_model` is not optional** — strips undeclared fields, generates accurate Swagger docs.
3. **`asyncio.gather` with `return_exceptions=True`** — one vendor down must not crash the whole endpoint.
4. **Partial data beats no data** — only 503 when ALL vendors are unreachable.
5. **`Depends()` centralises auth** — write `verify_api_key` once, apply everywhere.
6. **80 %+ coverage is the floor** — mock every external call, test unhappy paths as hard as happy paths.

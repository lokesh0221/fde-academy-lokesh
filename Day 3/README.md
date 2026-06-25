# Day 3 — Python Fundamentals: Hands-On Exercises

**FDE Academy · Phase 1: Foundations · Week 1 · Day 3**

Three exercises simulating real FDE tasks: CSV cleaning, JSON parsing, and report generation.

---

## Prerequisites

```bash
python --version          # must be 3.11+
python -c "import pandas; print(pandas.__version__)"
pip install pandas black mypy
```

---

## Exercise 1 — Supply Chain CSV Cleaner

**Files:** `shipments_raw.csv` (input) → `shipments_clean.csv`, `shipments_rejected.csv` (outputs)

```bash
cd "day3_python"
python day3_ex1_cleaner.py
```

**Expected output:**
```
=== Data Quality Report ===
  total_input               10
  clean_count               5
  rejected_count            5
  rejection_rate_pct        50.0
  rejection_reasons         [...]
```

---

## Exercise 2 — Nested JSON API Parser

**Files:** `day3_ex2_json_parser.py` → `shipments_parsed.csv` (output)

```bash
python day3_ex2_json_parser.py
```

**Expected output:**
```
Parsed 3 shipment records
Saved: shipments_parsed.csv

=== Carrier Summary ===
  DHL Express     shipments=1 revenue=₹1,155.25 delayed=0 avg_delay=0.0d
  FedEx India     shipments=1 revenue=₹434.24 delayed=1 avg_delay=3.0d
  BlueDart        shipments=1 revenue=₹212.40 delayed=0 avg_delay=0.0d
```

---

## Exercise 3 — Automated Summary Report Generator

**Requires:** `shipments_clean.csv` from Exercise 1  
**Outputs:** `shipments_summary.csv`, `route_report.csv`

```bash
python day3_ex3_report.py
```

**Expected output:**
```
============================================================
  AutoFinance Bank — Daily Shipment Report [YYYY-MM-DD]
============================================================
  Total Shipments: 5 | Total Revenue: $1,129.25 | Overall OTIF: 40.0% | Avg Delay: 1.6 days

=== Carrier KPIs ===
  ...

=== Top Routes ===
  ...

🚩 Flagged Shipments (delay > 3 days):
  SH010  FEDEX  in_transit  delay=5  cost=$88.75
```

---

## Run All Three in Sequence

```bash
cd "day3_python"
python day3_ex1_cleaner.py
python day3_ex2_json_parser.py
python day3_ex3_report.py
```

---

## Quality Gate (Black + mypy)

```bash
# Auto-format with Black
black day3_ex1_cleaner.py day3_ex2_json_parser.py day3_ex3_report.py

# Type-check with mypy
mypy day3_ex1_cleaner.py day3_ex2_json_parser.py day3_ex3_report.py

# Verify all output files exist
ls shipments_clean.csv shipments_rejected.csv shipments_parsed.csv shipments_summary.csv route_report.csv
```

---

## Output Files Summary

| File | Created by | Description |
|------|-----------|-------------|
| `shipments_raw.csv` | (provided) | Messy TMS export — input to Exercise 1 |
| `shipments_clean.csv` | Exercise 1 | Validated, normalised rows |
| `shipments_rejected.csv` | Exercise 1 | Rows that failed validation + reasons |
| `shipments_parsed.csv` | Exercise 2 | Flattened JSON records |
| `shipments_summary.csv` | Exercise 3 | Per-carrier KPI table |
| `route_report.csv` | Exercise 3 | Top routes by shipment volume |

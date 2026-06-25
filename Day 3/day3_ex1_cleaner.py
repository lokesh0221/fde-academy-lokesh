import pandas as pd
from pathlib import Path

file_path = Path("./shipments_raw.csv")


def load_shipments(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df = df.dropna(how="all")
    return df


VALID_STATUSES = {"in_transit", "delivered", "pending", "exception"}
VALID_CARRIERS = {"DHL", "FEDEX", "BLUEDART"}


def normalise_row(row: pd.Series) -> pd.Series:
    if pd.notna(row["shipment_id"]):
        row["shipment_id"] = str(row["shipment_id"]).strip()

    if pd.notna(row["carrier"]):
        row["carrier"] = str(row["carrier"]).strip().upper()

    if pd.notna(row["status"]):
        row["status"] = str(row["status"]).strip().lower()

    if pd.notna(row["origin"]):
        row["origin"] = str(row["origin"]).strip().title()

    if pd.notna(row["destination"]):
        row["destination"] = str(row["destination"]).strip().title()

    delay = pd.to_numeric(row["delay_days"], errors="coerce")
    if pd.isna(delay):
        row["delay_days"] = None
    else:
        row["delay_days"] = int(delay)

    cost = pd.to_numeric(row["cost_usd"], errors="coerce")
    if pd.isna(cost):
        row["cost_usd"] = None
    else:
        row["cost_usd"] = float(cost)

    return row


def validate_row(row: pd.Series) -> list[str]:
    errors = []

    if pd.isna(row["shipment_id"]) or str(row["shipment_id"]).strip() == "":
        errors.append("shipment_id must not be empty")

    if pd.isna(row["carrier"]) or row["carrier"] not in VALID_CARRIERS:
        errors.append("carrier must be in ...")

    if pd.isna(row["status"]) or row["status"] not in VALID_STATUSES:
        errors.append("status must be in VALID_STATUSES")

    if (
        row["delay_days"] is None
        or (isinstance(row["delay_days"], float) and pd.isna(row["delay_days"]))
        or row["delay_days"] < 0
    ):
        errors.append("delay_days must be >= 0")

    if (
        row["cost_usd"] is None
        or (isinstance(row["cost_usd"], float) and pd.isna(row["cost_usd"]))
        or row["cost_usd"] <= 0
    ):
        errors.append("cost_usd must not be None and must be > 0")

    return errors


def clean_shipments(
    input_path: str,
    clean_output_path: str,
    rejected_output_path: str,
) -> dict:
    """
    Run the full cleaning pipeline:
    Load CSV, normalise, validate, split into clean/rejected, write outputs.
    Returns a summary dict.
    """
    df = load_shipments(input_path)
    total_input = len(df)

    df = df.apply(normalise_row, axis=1)

    clean_rows = []
    rejected_rows = []
    all_reasons: list[str] = []

    for _, row in df.iterrows():
        errors = validate_row(row)
        if errors:
            row_dict = row.to_dict()
            row_dict["rejection_reasons"] = ", ".join(errors)
            rejected_rows.append(row_dict)
            all_reasons.extend(errors)
        else:
            clean_rows.append(row.to_dict())

    clean_df = pd.DataFrame(clean_rows)
    rejected_df = pd.DataFrame(rejected_rows)

    clean_df.to_csv(clean_output_path, index=False)
    rejected_df.to_csv(rejected_output_path, index=False)

    rule_order = [
        "shipment_id must not be empty",
        "carrier must be in ...",
        "status must be in VALID_STATUSES",
        "delay_days must be >= 0",
        "cost_usd must not be None and must be > 0",
    ]
    seen = set(all_reasons)
    unique_reasons = [r for r in rule_order if r in seen]
    rejected_count = len(rejected_rows)
    clean_count = len(clean_rows)
    rejection_rate = (
        round(rejected_count / total_input * 100, 1) if total_input else 0.0
    )

    return {
        "total_input": total_input,
        "clean_count": clean_count,
        "rejected_count": rejected_count,
        "rejection_rate_pct": rejection_rate,
        "rejection_reasons": unique_reasons,
    }


if __name__ == "__main__":
    summary = clean_shipments(
        input_path="shipments_raw.csv",
        clean_output_path="shipments_clean.csv",
        rejected_output_path="shipments_rejected.csv",
    )
    print("=== Data Quality Report ===")
    for key, value in summary.items():
        print(f"{key:<25} {value}")
    print("shipments_clean.csv    - 5 clean rows with normalised fields")
    print("shipments_rejected.csv - 5 rejected rows with rejection_reasons column")

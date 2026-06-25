"""
AutoFinance Bank - Daily Shipment Operations Report
FDE Academy Day 3 Exercise 3

Usage: python day3_ex3_report.py

Outputs:
    Console: formatted KPI report
    shipments_summary.csv: per-carrier aggregated KPIs
    route_report.csv: top routes by volume
"""

import pandas as pd
from pathlib import Path
from datetime import date

INPUT_FILE = "shipments_clean.csv"
SUMMARY_CSV = "shipments_summary.csv"
ROUTES_CSV = "route_report.csv"


def compute_carrier_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-carrier KPIs from the cleaned shipments DataFrame.
    Returns a DataFrame sorted by total_shipments descending.
    """
    grouped = df.groupby("carrier")

    kpis = grouped.apply(
        lambda g: pd.Series(
            {
                "total_shipments": len(g),
                "delivered": (g["status"] == "delivered").sum(),
                "in_transit": (g["status"] == "in_transit").sum(),
                "otif_pct": round(
                    ((g["status"] == "delivered") & (g["delay_days"] == 0)).sum()
                    / len(g)
                    * 100,
                    1,
                ),
                "avg_delay_days": round(g["delay_days"].mean(), 1),
                "max_delay_days": int(g["delay_days"].max()),
                "total_revenue": round(g["cost_usd"].sum(), 2),
                "avg_cost_per_ship": round(g["cost_usd"].mean(), 2),
            }
        )
    ).reset_index()

    return kpis.sort_values("total_shipments", ascending=False).reset_index(drop=True)


def compute_route_report(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Compute a route-level report grouped by (origin, destination) pair.
    Returns top_n routes by shipment_count.
    """
    df = df.copy()
    df["route"] = df["origin"] + " -> " + df["destination"]

    def most_used_carrier(g: pd.DataFrame) -> str:
        return str(g["carrier"].value_counts().idxmax())

    grouped = (
        df.groupby("route")
        .apply(
            lambda g: pd.Series(
                {
                    "shipment_count": len(g),
                    "avg_delay_days": round(g["delay_days"].mean(), 1),
                    "total_revenue": round(g["cost_usd"].sum(), 2),
                    "most_used_carrier": most_used_carrier(g),
                }
            )
        )
        .reset_index()
    )

    return (
        grouped.sort_values("shipment_count", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )


def print_console_report(
    df: pd.DataFrame,
    carrier_kpis: pd.DataFrame,
    route_report: pd.DataFrame,
) -> None:
    """
    Print a formatted operations report to the console.
    Sections: header, overall KPIs, per-carrier table, top routes, flagged shipments.
    """
    today = date.today()
    total_rev = round(df["cost_usd"].sum(), 2)
    delivered = df[df["status"] == "delivered"]
    otif_pct = round(
        ((df["status"] == "delivered") & (df["delay_days"] == 0)).sum() / len(df) * 100,
        1,
    )
    avg_delay = round(df["delay_days"].mean(), 1)

    print(f"\n{'='*60}")
    print(f"  AutoFinance Bank - Daily Shipment Report [{today}]")
    print(f"{'='*60}")
    print(
        f"  Total Shipments: {len(df)} | Total Revenue: ${total_rev:,.2f} | "
        f"Overall OTIF: {otif_pct}% | Avg Delay: {avg_delay} days"
    )

    print(f"\n=== Carrier KPIs ===")
    print(
        f"  {'Carrier':<12} {'Shipments':>9} {'Delivered':>9} {'OTIF%':>7} {'Avg Delay':>10} {'Revenue':>12}"
    )
    print(f"  {'-'*65}")
    for _, row in carrier_kpis.iterrows():
        print(
            f"  {row['carrier']:<12} {int(row['total_shipments']):>9} "
            f"{int(row['delivered']):>9} {row['otif_pct']:>6.1f}% "
            f"{row['avg_delay_days']:>9.1f} ${row['total_revenue']:>10,.2f}"
        )

    print(f"\n=== Top Routes ===")
    print(f"  {'Route':<25} {'Count':>6} {'Avg Delay':>10} {'Revenue':>12}")
    print(f"  {'-'*57}")
    for _, row in route_report.iterrows():
        print(
            f"  {row['route']:<25} {int(row['shipment_count']):>6} "
            f"{row['avg_delay_days']:>9.1f} ${row['total_revenue']:>10,.2f}"
        )

    flagged = df[df["delay_days"] > 3]
    print(f"\n** Flagged Shipments (delay > 3 days):")
    if flagged.empty:
        print("  None")
    else:
        for _, row in flagged.iterrows():
            print(
                f"  {row['shipment_id']}  {row['carrier']}  {row['status']}  "
                f"delay={int(row['delay_days'])}  cost=${row['cost_usd']:.2f}"
            )


def main() -> None:
    """Run the full report generation pipeline."""
    if not Path(INPUT_FILE).exists():
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    required_cols = {"shipment_id", "carrier", "status", "delay_days", "cost_usd"}
    missing = required_cols - set(df.columns)
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        return
    if len(df) == 0:
        print("ERROR: Input file contains no data rows")
        return

    carrier_kpis = compute_carrier_kpis(df)
    route_report = compute_route_report(df, top_n=5)

    carrier_kpis.to_csv(SUMMARY_CSV, index=False)
    route_report.to_csv(ROUTES_CSV, index=False)

    print_console_report(df, carrier_kpis, route_report)
    print(f"\nSaved: {SUMMARY_CSV} | {ROUTES_CSV}")


if __name__ == "__main__":
    main()

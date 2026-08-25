"""
clean_data.py

Cleans and transforms a peer-city revenue dataset for the RRS efficiency
model: per-capita conversion, log transforms, and flagging of known data
caveats (e.g. state-level sales tax collection blind spots).

Usage:
    python clean_data.py --input peers.csv --output peers_clean.csv
"""

import argparse
import sys

import numpy as np
import pandas as pd

# States that collect local sales tax at the county or state level rather
# than the city level (as of this writing). City-level sales tax revenue
# for these states may read as zero or understated in Census source data
# regardless of actual retail activity.
SALES_TAX_BLIND_SPOT_STATES = {"MA", "MN", "FL", "GA", "MI"}

REQUIRED_COLUMNS = [
    "city_id",
    "population",
    "total_revenue",
    "property_tax_revenue",
    "sales_tax_revenue",
    "fees_revenue",
    "utility_revenue",
    "median_household_income",
    "property_tax_rate",
    "sales_tax_rate_local",
    "pct_commercial_land_use",
    "state_income_tax_flag",
    "owns_utility_flag",
]

REVENUE_COLUMNS = [
    "total_revenue",
    "property_tax_revenue",
    "sales_tax_revenue",
    "fees_revenue",
    "utility_revenue",
]


def load(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path)


def validate(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        sys.exit(f"Missing required columns: {missing}")

    null_counts = df[REQUIRED_COLUMNS].isnull().sum()
    if null_counts.any():
        print("Warning: missing values found —")
        print(null_counts[null_counts > 0])

    dupes = df["city_id"].duplicated().sum()
    if dupes:
        print(f"Warning: {dupes} duplicate city_id values found.")


def add_per_capita(df: pd.DataFrame) -> pd.DataFrame:
    for col in REVENUE_COLUMNS:
        df[f"{col}_per_capita"] = df[col] / df["population"]
    return df


def add_log_transforms(df: pd.DataFrame) -> pd.DataFrame:
    df["log_population"] = np.log(df["population"])
    for col in REVENUE_COLUMNS:
        # log1p guards against zero-revenue cities (e.g. sales tax
        # blind-spot states) without dropping them outright.
        df[f"log_{col}_per_capita"] = np.log1p(df[f"{col}_per_capita"])
    return df


def flag_sales_tax_blind_spot(df: pd.DataFrame) -> pd.DataFrame:
    if "state" not in df.columns:
        print(
            "Note: no 'state' column found — skipping sales tax "
            "blind-spot flagging. Add a 'state' column (USPS abbreviation) "
            "to enable this check."
        )
        df["sales_tax_blind_spot_flag"] = 0
        return df

    df["sales_tax_blind_spot_flag"] = (
        df["state"].isin(SALES_TAX_BLIND_SPOT_STATES).astype(int)
    )
    flagged = df["sales_tax_blind_spot_flag"].sum()
    if flagged:
        print(
            f"Flagged {flagged} cities in known sales-tax blind-spot "
            f"states ({sorted(SALES_TAX_BLIND_SPOT_STATES)}). Consider a "
            "state fixed effect or excluding these from the sales tax "
            "model specifically — see README."
        )
    return df


def flag_outliers(df: pd.DataFrame, z_thresh: float = 3.0) -> pd.DataFrame:
    """Flags cities whose total revenue per capita is a statistical
    outlier relative to the rest of the pool, for manual review — this
    does not drop any rows."""
    col = "total_revenue_per_capita"
    z = (df[col] - df[col].mean()) / df[col].std()
    df["revenue_outlier_flag"] = (z.abs() > z_thresh).astype(int)
    n = df["revenue_outlier_flag"].sum()
    if n:
        print(f"Flagged {n} cities as revenue-per-capita outliers (|z| > {z_thresh}) for manual review.")
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to raw peer dataset (CSV or Excel)")
    parser.add_argument("--output", required=True, help="Path to write cleaned CSV")
    parser.add_argument(
        "--outlier-z", type=float, default=3.0,
        help="Z-score threshold for flagging revenue-per-capita outliers (default 3.0)",
    )
    args = parser.parse_args()

    df = load(args.input)
    validate(df)
    df = add_per_capita(df)
    df = add_log_transforms(df)
    df = flag_sales_tax_blind_spot(df)
    df = flag_outliers(df, args.outlier_z)

    df.to_csv(args.output, index=False)
    print(f"Wrote cleaned dataset ({len(df)} rows) to {args.output}")


if __name__ == "__main__":
    main()

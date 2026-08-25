"""
model.py

Fits the RRS regression: revenue per capita as a function of income,
population, tax rates, land use mix, and structural flags. Runs once for
total revenue and once per revenue category.

Usage:
    python model.py --input peers_clean.csv --output-dir results/ \
        [--utility-mode flag|separate] [--cluster-by-state]
"""

import argparse
import json
import os

import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

PREDICTORS = [
    "median_household_income",
    "log_population",
    "property_tax_rate",
    "sales_tax_rate_local",
    "pct_commercial_land_use",
    "state_income_tax_flag",
]

CATEGORIES = {
    "total": "total_revenue_per_capita",
    "property_tax": "property_tax_revenue_per_capita",
    "sales_tax": "sales_tax_revenue_per_capita",
    "fees": "fees_revenue_per_capita",
}


def build_formula(dep_var: str, predictors: list) -> str:
    return f"{dep_var} ~ " + " + ".join(predictors)


def fit_model(df: pd.DataFrame, dep_var: str, predictors: list, cluster_by_state: bool):
    formula = build_formula(dep_var, predictors)
    if cluster_by_state and "state" in df.columns:
        model = smf.ols(formula, data=df).fit(
            cov_type="cluster", cov_kwds={"groups": df["state"]}
        )
    else:
        model = smf.ols(formula, data=df).fit(cov_type="HC1")
    return model, formula


def summarize(model, formula: str) -> dict:
    return {
        "formula": formula,
        "n_obs": int(model.nobs),
        "r_squared": model.rsquared,
        "adj_r_squared": model.rsquared_adj,
        "f_statistic": model.fvalue,
        "f_pvalue": model.f_pvalue,
        "aic": model.aic,
        "bic": model.bic,
        "coefficients": {
            k: {
                "coef": model.params[k],
                "std_err": model.bse[k],
                "t_stat": model.tvalues[k],
                "p_value": model.pvalues[k],
            }
            for k in model.params.index
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Cleaned peer dataset CSV (from clean_data.py)")
    parser.add_argument("--output-dir", required=True, help="Directory to write model outputs")
    parser.add_argument(
        "--utility-mode", choices=["flag", "separate"], default="flag",
        help=(
            "'flag' includes owns_utility_flag as a control on total revenue. "
            "'separate' fits an additional utility-revenue model and excludes "
            "utility from the total-revenue dependent variable."
        ),
    )
    parser.add_argument(
        "--cluster-by-state", action="store_true",
        help="Use standard errors clustered by state (requires a 'state' column)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    df = pd.read_csv(args.input)

    predictors = list(PREDICTORS)
    if args.utility_mode == "flag":
        predictors = predictors + ["owns_utility_flag"]

    categories = dict(CATEGORIES)
    if args.utility_mode == "separate":
        categories["utility"] = "utility_revenue_per_capita"
        # non-utility total = total minus utility, per capita
        if "non_utility_revenue_per_capita" not in df.columns:
            df["non_utility_revenue_per_capita"] = (
                df["total_revenue_per_capita"] - df["utility_revenue_per_capita"]
            )
        categories["total"] = "non_utility_revenue_per_capita"

    results = {}
    for label, dep_var in categories.items():
        if dep_var not in df.columns:
            print(f"Skipping '{label}': column '{dep_var}' not found.")
            continue
        model, formula = fit_model(df, dep_var, predictors, args.cluster_by_state)
        results[label] = summarize(model, formula)

        # Save fitted values + residuals for diagnostics
        diag = df[["city_id", dep_var]].copy()
        diag["predicted"] = model.fittedvalues
        diag["residual"] = model.resid
        diag_path = os.path.join(args.output_dir, f"diagnostics_{label}.csv")
        diag.to_csv(diag_path, index=False)

        model_path = os.path.join(args.output_dir, f"model_{label}.pickle")
        model.save(model_path)

        print(f"[{label}] N={int(model.nobs)}  R²={model.rsquared:.3f}  "
              f"formula: {formula}")

    summary_path = os.path.join(args.output_dir, "model_summary.json")
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote model summary to {summary_path}")
    print(f"Fitted model objects (.pickle) and diagnostics (.csv) written to {args.output_dir}")


if __name__ == "__main__":
    main()

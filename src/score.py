"""
score.py

Scores a target city against fitted RRS regression models: predicted
("capacity") revenue, Efficiency Score (actual / predicted), and z-score
(standardized residual against the peer distribution).

Usage:
    python score.py --model-dir results/ --target-city target_city.json
"""

import argparse
import json
import math
import os

import numpy as np
import pandas as pd
import statsmodels.regression.linear_model as lm


def load_target(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def score_category(label: str, model_dir: str, target: dict) -> dict:
    model_path = os.path.join(model_dir, f"model_{label}.pickle")
    diag_path = os.path.join(model_dir, f"diagnostics_{label}.csv")

    if not os.path.exists(model_path):
        return {"error": f"No fitted model found for '{label}' at {model_path}"}

    model = lm.OLSResults.load(model_path)
    diag = pd.read_csv(diag_path) if os.path.exists(diag_path) else None

    # Build the row of predictors the model expects, in the same order
    # as its exog names (drop the intercept, which statsmodels adds).
    exog_names = [n for n in model.model.exog_names if n != "Intercept"]
    row = {}
    for name in exog_names:
        if name == "log_population":
            row[name] = math.log(target["population"])
        elif name not in target:
            return {"error": f"Missing required field '{name}' for target city"}
        else:
            row[name] = target[name]

    x = pd.DataFrame([row])
    x = pd.concat([pd.Series({"Intercept": 1.0}).to_frame().T, x], axis=1) \
        if "Intercept" in model.model.exog_names else x
    x = x[model.model.exog_names] if "Intercept" in model.model.exog_names else x[exog_names]

    predicted = float(model.predict(x)[0])

    dep_var = model.model.endog_names
    actual = target.get(dep_var)
    if actual is None:
        return {"error": f"Target city JSON missing actual value for '{dep_var}'"}

    efficiency_score = actual / predicted if predicted else None

    result = {
        "category": label,
        "dependent_variable": dep_var,
        "predicted_capacity": predicted,
        "actual": actual,
        "efficiency_score": efficiency_score,
    }

    if diag is not None and "residual" in diag.columns:
        resid_std = diag["residual"].std()
        target_resid = actual - predicted
        result["z_score"] = target_resid / resid_std if resid_std else None
        result["peer_n"] = len(diag)
        result["percentile"] = float(
            (diag["predicted"].sub(diag[dep_var]).lt(target_resid)).mean() * 100
        )

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, help="Directory containing fitted model .pickle files (from model.py)")
    parser.add_argument("--target-city", required=True, help="Path to target city JSON (same fields as a peer row)")
    parser.add_argument(
        "--categories", nargs="+", default=["total", "property_tax", "sales_tax", "fees"],
        help="Which fitted category models to score against",
    )
    parser.add_argument("--output", help="Optional path to write results as JSON")
    args = parser.parse_args()

    target = load_target(args.target_city)

    results = {}
    for label in args.categories:
        results[label] = score_category(label, args.model_dir, target)
        r = results[label]
        if "error" in r:
            print(f"[{label}] {r['error']}")
        else:
            eff = r["efficiency_score"]
            z = r.get("z_score")
            print(
                f"[{label}] Efficiency Score = {eff:.3f}"
                + (f"  z = {z:.3f}" if z is not None else "")
            )

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nWrote scoring results to {args.output}")


if __name__ == "__main__":
    main()

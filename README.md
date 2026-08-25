[README.md](https://github.com/user-attachments/files/31425431/README.md)
# Representative Revenue System (RRS) Efficiency Model

Open-source implementation of a Representative Revenue System regression
model for benchmarking a municipality's revenue collection against a peer
set of comparable cities. Built for a revenue capacity study applying the
RRS / tax-capacity-and-effort framework (ACIR; Urban Institute) to 2022
Census of Governments data.

This repository contains the **regression and scoring code only**. It does
not include any city-level dataset. The city this model was originally
built for is referred to throughout as "the case city" and its data is
withheld; you can run this code against any peer dataset that matches the
schema below.

## What this does

1. Cleans and transforms a peer-city dataset (per-capita conversion,
   log transforms, outlier flags).
2. Fits OLS regression models predicting revenue per capita from a set of
   structural and economic predictors — once for total revenue, and
   separately for each revenue category (property tax, sales tax,
   fees/charges, utility).
3. Scores a target city against the fitted model: an **Efficiency Score**
   (actual ÷ predicted revenue) and a **z-score** (standardized residual,
   to gauge whether any gap is meaningfully large or within normal noise).

## Why category-level, not just aggregate

A single total-revenue efficiency score can hide an offsetting pattern —
strong performance in one category masking weak performance in another.
This model runs the regression once for total revenue and again for each
category separately so a category-level gap isn't averaged away.

## Input data schema

The code expects a CSV or Excel file with one row per peer city and the
following columns:

| Column | Type | Description |
|---|---|---|
| `city_id` | string | Unique identifier (city can be anonymized/coded) |
| `population` | int | Total population |
| `total_revenue` | float | Total city revenue (annual) |
| `property_tax_revenue` | float | Property tax revenue (Census item T01) |
| `sales_tax_revenue` | float | Sales tax revenue (Census item T09) |
| `fees_revenue` | float | Fees/charges revenue (Census A-series) |
| `utility_revenue` | float | Utility revenue (Census A90–A94) |
| `median_household_income` | float | ACS 5-Year estimate |
| `property_tax_rate` | float | Local property tax rate |
| `sales_tax_rate_local` | float | Local-option sales tax rate |
| `pct_commercial_land_use` | float | % commercial land use, or retail sales per capita as proxy |
| `state_income_tax_flag` | int (0/1) | 1 if city's state levies a personal income tax |
| `owns_utility_flag` | int (0/1) | 1 if city operates its own utility system |

All revenue fields should be in the same units (e.g. annual USD).

### Known data caveat: state-level sales tax collection

A handful of states collect local sales tax at the county or state level
rather than the city level (at time of writing: MA, MN, FL, GA, MI). For
cities in these states, `sales_tax_revenue` from Census source data may
read as zero or understated regardless of actual retail activity. Flag
these cities explicitly rather than treating a low value as evidence of
under-collection. Options: add a state fixed effect, or exclude these
states from the sales tax model specifically. See `src/clean_data.py`.

## Usage

```bash
pip install -r requirements.txt

python src/clean_data.py --input peers.csv --output peers_clean.csv

python src/model.py --input peers_clean.csv --output-dir results/

python src/score.py \
  --model-dir results/ \
  --target-city target_city.json
```

`target_city.json` should contain the same fields as a peer row (the
score script plugs this city's values into the fitted model rather than
including it in the regression).

## Model specification

```
revenue_per_capita ~ median_household_income
                    + log(population)
                    + property_tax_rate
                    + sales_tax_rate_local
                    + pct_commercial_land_use
                    + state_income_tax_flag
                    + owns_utility_flag
```

Run once on total revenue per capita, then again on each category
(property tax, sales tax, fees, utility) per capita as the dependent
variable. Robust standard errors (HC1); clustering by state is supported
if a `state` column is present.

### Utility revenue handling

Utility revenue is cost-recovery rather than tax capacity, and can swamp
a total-revenue comparison for cities that don't run their own utility.
Two options are supported (see `--utility-mode` in `src/model.py`):

- `flag` — include `owns_utility_flag` as a control, model total revenue
  across all peers.
- `separate` — model utility revenue separately from non-utility revenue,
  comparing the target city's non-utility revenue against peer non-utility
  capacity. This is the cleaner specification for "where is revenue being
  under-collected" questions, since it doesn't mix cost-recovery revenue
  with tax capacity.

## Efficiency scoring

```
Efficiency Score = Actual Revenue / Predicted (capacity) Revenue
```

- Below 1.0 → collecting less than peers with a comparable profile
- At or above 1.0 → in line with or ahead of peers

The z-score (standardized residual) indicates whether a gap is large
relative to the peer distribution's spread, not just whether the ratio is
below 1.0. A low efficiency score with a small z-score may not represent
a meaningful gap.

## Limitations

- Cross-sectional (single fiscal year) — no time trend.
- Relies on self-reported municipal finance data (Census of Governments).
- Peer selection involves judgment (see `docs/peer_screening.md` for the
  exclusion framework used in the original study); results are sensitive
  to peer set composition.
- Land-use mix is often a proxy (e.g. retail sales per capita) where
  parcel-level data isn't available.
- Small peer sets (e.g. state-only comparisons) may not support reliable
  regression; consider descriptive ranking instead when N is small.

## License

MIT — see `LICENSE`.

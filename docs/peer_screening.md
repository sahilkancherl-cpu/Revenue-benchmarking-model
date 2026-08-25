# Peer Screening Framework

The regression model is only as good as the peer set it's fit on. This
document describes the exclusion framework used to build a comparable
peer set for a Representative Revenue System study — not a specific city
list, just the reusable logic.

## Principle

Exclude a peer city only where its revenue comes from a source the target
city structurally does not have. These are distortions a regression
cannot control for with the standard predictor set. Do not exclude on
variables that belong in the model as predictors (see below).

## Structural exclusion criteria

- **Non-resident revenue capture** — casinos, theme parks, regional malls,
  major stadiums/arenas, resort or beach tourism economies.
- **Large tax-exempt land** — state capitals, major universities (student
  population large relative to city population), military installations,
  major federal research campuses.
- **Non-residential economic base** — standalone industrial, port,
  petrochemical, or agricultural-processing economies; major corporate
  headquarters whose commercial tax base dwarfs the residential one.
- **Data not reflecting normal operations** — active fiscal crisis,
  mid-transformation (large active redevelopment), newly incorporated
  cities without multi-year comparable financials.
- **Urban form mismatch** — extreme-density commuter cities with a
  structurally different property base than the target city's housing
  stock (e.g. comparing a suburban single-family city against a dense,
  multi-family-dominant urban core).

## NOT exclusion criteria

- **Median household income** — this is a predictor in the model, not a
  screen. Screening out high-income cities biases the peer pool toward
  lower income levels than the target city, which makes the target city's
  efficiency score look artificially favorable by construction.
- **Home values** — same reasoning; enters the model via income/tax base
  controls, not as a screen.
- **Population within the chosen band** — population is a control
  variable (log-transformed), not a screening criterion, as long as the
  city falls within the intended population band.

## Recommended workflow

1. **Data-driven pre-filter before manual review.** Compute revenue per
   capita for every city in the candidate pool. Cities far outside the
   target city's per-capita range are structurally different — flag them
   before doing any manual research. This turns a review of hundreds of
   cities into manual review of a much smaller flagged subset.
2. **Compute a utility revenue share** for every candidate (utility
   revenue ÷ total revenue). Cities with no utility operation have a
   fundamentally different revenue mix if the target city runs its own
   utility — see the utility-handling options in the main README.
3. **Manual review** then runs only on the close-but-ambiguous cities the
   data flagged, to determine why a number looks the way it does.
4. **Document every exclusion with a reason.** For the manuscript's
   limitations section, this becomes the record of how many cities were
   excluded and why.

## Known blind spot: state-level sales tax collection

Some states collect local sales tax at the county or state level rather
than the city level. City-level sales tax revenue in Census source data
for these states will read as zero or understated regardless of actual
retail activity. An automated per-capita filter is blind to this —
verify manually or apply a state-level flag (see `src/clean_data.py`).

## Target set size

A regression needs enough peer cities to support the number of
predictors reliably — a common rule of thumb is at least 10 observations
per predictor. If a genuinely comparable peer pool is small (for example,
restricting to a single state), a full regression may not be
statistically reliable; consider descriptive ranking against the
available peers instead.

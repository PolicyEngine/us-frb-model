# frbus — a modern Python implementation of FRB/US

A from-scratch, modern (numpy/scipy/sympy, Python 3.11+) implementation of the
Federal Reserve Board's **FRB/US** macroeconomic model, with VAR
(backward-looking) expectations by default and opt-in model-consistent
expectations (see below).

## Provenance

The model itself — the equation system (`model.xml`), the data vintage
(`LONGBASE.TXT`), the reference implementation (`pyfrbus`), and the model
documentation — is published by the Federal Reserve Board in the **public
domain** (see `vendor/pyfrbus_package/LICENSE`). The raw materials are kept
unmodified under `vendor/` (see `vendor/README.md`). This package is an
independent reimplementation that follows pyfrbus semantics exactly and is
validated against it (see `VALIDATION.md`).

**Data vintage.** The bundled `LONGBASE.TXT` is the Board's October 2026
vintage (data package of 13 October 2026), with history through 2026Q2. The
published experiments still shock in 2026Q1, two quarters before that data
edge, so they stay comparable with the April 2026 vintage used until
16 November 2026; `VALIDATION.md` gives both where they differ.

## Install

```bash
uv venv && uv pip install -e ".[dev]"
```

## Quickstart

```python
import pandas as pd
from frbus import Frbus, load_data

data = load_data("vendor/data_only_package/LONGBASE.TXT")
model = Frbus("vendor/pyfrbus_package/models/model.xml")

start, end = pd.Period("2026Q1"), pd.Period("2030Q4")

# Fiscal-policy configuration used by the Fed's demos
data.loc[start:end, "dfpdbt"] = 0
data.loc[start:end, "dfpsrp"] = 1

# Add-factor the model so it reproduces the baseline exactly
with_adds = model.init_trac(start, end, data)

# 100bp monetary policy shock
with_adds.loc[start, "rffintay_aerr"] += 1
sim = model.solve(start, end, with_adds)

print((sim.loc[start:end, "xgdp"] / with_adds.loc[start:end, "xgdp"] - 1) * 100)
```

A runnable version is in `examples/monetary_policy_shock.py`.

## What is implemented

- Parsing of `model.xml`: variables, equations, per-equation coefficients,
  endogenous/exogenous classification (VAR "standard" equations).
- `LONGBASE.TXT` loading into a pandas DataFrame with a quarterly PeriodIndex.
- Per-period damped Newton solver on the full simultaneous system with an
  analytic sparse Jacobian (sympy differentiation, scipy sparse LU).
- `Frbus(path)`, `.init_trac(start, end, data)`, `.solve(start, end, data)`,
  `.exogenize([...])` — mirroring the essentials of pyfrbus's `Frbus` class.
- Opt-in model-consistent expectations: `Frbus(path, mce="mcap")` (financial
  markets), `"wp"` (wage-price), `"mcap+wp"` or `"all"`, as in pyfrbus. The
  default stays VAR expectations. MCE solves stack the whole window in one
  sparse Newton solve (`src/frbus/mce.py`), with terminal values for leads
  past `end` read from the input data. Newton stops on the step (`xtol`) or,
  for MCE only, on the stacked residual (`ftol`, 1e-8) followed by one more
  Newton step; `ConvergenceError` otherwise. All four modes are gated against
  the Board's pyfrbus on a 100bp shock, all 284 variables x 20 quarters, at
  < 1e-6 (observed 1.4e-9 to 9.0e-9; tests/test_mce.py, VALIDATION.md Test 5). The
  results in `results/expectations_comparison.md`,
  `results/expectations_matched_closures.md` and
  `results/episode_2022_tightening_mce_*.md` compare VAR and MCE.
  `mcontrol` is out of scope.
- Stochastic simulation: `Frbus.stochsim()` and `.stochsim_bands()`
  (seeded residual bootstrap, `src/frbus/uncertainty.py`) give percentile
  bands around a deterministic solve.

## Validation

**For the site:** `results/site_responses.{json,md}` (from
`scripts/site_responses.py`) has the quarter-by-quarter funds rate, real GDP,
unemployment, output gap and core PCE responses for the 100bp monetary,
purchases, transfers and tax experiments, plus a scorecard of every headline
against its published band. `tests/test_site_responses.py` keeps it in step
with the model and the other results files.

See `VALIDATION.md` for full tables. Summary, in order of how much each one
actually tells you:

- **Cross-validation (the real evidence).** Four shock scenarios — monetary,
  fiscal `egfe`, tax `trp`, and a non-inertial Taylor variant — agree with the
  Fed's own pyfrbus across all 284 endogenous variables and 20 quarters to
  2.0e-8 abs / 1.5e-8 rel at worst on the October 2026 data (monetary 1.4e-8
  abs; fiscal 9.5e-9, tax 2.0e-8, Taylor variant 1.9e-8; `VALIDATION.md`
  Tests 2 and 2a). The exact values vary between machines and dependency
  versions at this scale, all far inside the 1e-6 gate. For scale, the Board's
  own pyfrbus 1.0.0 and 1.1.1 releases differ from *each other* by 1.4e-8 on
  the monetary shock, so this is the same order as the reference
  implementation's own noise floor.
- **Fiscal multipliers.** Purchases and tax cuts lie inside the published
  ranges in `VALIDATION.md` Test 4: purchases 0.75 in year 1 under the
  inertial Taylor rule and 0.93 in year 2 with the funds rate pegged; tax cuts
  0.23 in year 1. The rule × horizon grid is ordered as theory requires.
  **The 0.75 is for a 1%-of-GDP rise and is size-dependent:** the same model
  gives about 0.83 for small shocks and 0.93 for a 1%-of-GDP cut, because GDP
  aggregates component growth in logs (issue #11). Transfers give 0.28–0.32 in year
  1: 0.28 under the inertial Taylor rule with the surplus rule on, 0.32 with
  the funds rate pegged and the fiscal rule off. Both are below purchases and
  below every matched published benchmark (`docs/benchmarks.md`; issue #13).
- **Monetary policy, against the Fed's own published runs.** For a 100bp
  funds-rate shock the output-gap trough (−0.50pp) sits between the 2014 FEDS
  Note (−0.4) and the 2013 price–wage note (≈ −0.53). Core inflation falls by
  0.034pp at the trough on both inflation concepts, matching the Board's
  post-2018 model (Laforte 2018, −0.0345pp); the −0.08pp in the 2013–14
  notes is the pre-2018 vintage (issue #14). After a fiscal shock ends, output undershoots by about
  45% of the peak as the funds rate comes back.
- **Tracking invariant.** After `init_trac`, solving the baseline reproduces
  LONGBASE to 7.3e-12 (one ulp on a level of order 1e4). **This is an identity, not a validation result** —
  `init_trac` defines the add-factors as minus the residuals at the input
  data, so it holds for *any* input; the repo gates a scrambled-baseline
  version of the same test to keep that honest. Do not cite it as agreement
  with the Fed's data.

Nothing here is a forecast evaluation. LONGBASE is the Board's illustrative
baseline, not a Fed forecast, and no pseudo-out-of-sample accuracy of any kind
is established for this model. The LONGBASE backtest in `VALIDATION.md`
scores the October 2026 vintage's first projected quarter, 2026Q3: close on
unemployment and the funds rate, GDP growth under-projected by 1.23pp (2.14%
against 3.37%) and core PCE inflation over-projected by 0.80pp (3.27% against
2.47%, annualized q/q). The April 2026 vintage under-projected core PCE by
1.65pp in 2026Q1 and 0.65pp in 2026Q2 (`backtests/longbase_2026-04_vs_outturns.md`).
Both are properties of the Fed's baseline data, not of this implementation.

## Development

```bash
uv run --extra dev pytest   # tests, including the tracking-invariant gate
uv run --extra dev ruff check src tests examples
```

## License

Code in this repository is released under the [MIT License](LICENSE). Original text and figures are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) with attribution to PolicyEngine. Third-party data and materials keep their own terms.

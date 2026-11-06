# frbus — a modern Python implementation of FRB/US

A from-scratch, modern (numpy/scipy/sympy, Python 3.10+) implementation of the
Federal Reserve Board's **FRB/US** macroeconomic model, with VAR
(backward-looking) expectations.

## Provenance

The model itself — the equation system (`model.xml`), the data vintage
(`LONGBASE.TXT`), the reference implementation (`pyfrbus`), and the model
documentation — is published by the Federal Reserve Board in the **public
domain** (see `vendor/pyfrbus_package/LICENSE`). The raw materials are kept
unmodified under `vendor/` (see `vendor/README.md`). This package is an
independent reimplementation that follows pyfrbus semantics exactly and is
validated against it (see `VALIDATION.md`).

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
  past `end` read from the input data; `ConvergenceError` if Newton does not
  reach `xtol`/`rtol`. Gated against the Board's pyfrbus in `mcap` and
  `mcap+wp` (tests/test_mce.py). `mcontrol` is out of scope.
- Stochastic simulation: `Frbus.stochsim()` and `.stochsim_bands()`
  (seeded residual bootstrap, `src/frbus/uncertainty.py`) give percentile
  bands around a deterministic solve.

## Validation

See `VALIDATION.md` for full tables. Summary, in order of how much each one
actually tells you:

- **Cross-validation (the real evidence).** Four shock scenarios — monetary,
  fiscal `egfe`, tax `trp`, and a non-inertial Taylor variant — agree with the
  Fed's own pyfrbus across all 284 endogenous variables and 20 quarters to
  6.0e-9 abs / 4.9e-8 rel. For scale, the Board's own pyfrbus 1.0.0 and 1.1.1
  releases differ from *each other* by 1.3e-8, so this sits at the reference
  implementation's own noise floor.
- **Fiscal multipliers.** Purchases and tax cuts lie inside the published
  ranges in `VALIDATION.md` Test 4: purchases 0.72 in year 1 under the
  inertial Taylor rule and 0.90 in year 2 with the funds rate pegged; tax cuts
  0.22 in year 1. The rule × horizon grid is ordered as theory requires.
  **The 0.72 is for a 1%-of-GDP rise and is size-dependent:** the same model
  gives about 0.80 for small shocks and 0.90 for a 1%-of-GDP cut, because GDP
  aggregates component growth in logs (issue #11). Transfers give 0.28 in year
  1, below purchases and below the range usually quoted for transfers to
  persons; that comparator is not vendored here.
- **Monetary policy, against the Fed's own published runs.** For a 100bp
  funds-rate shock the output-gap trough (−0.50pp) sits between the 2014 FEDS
  Note (−0.4) and the 2013 price–wage note (≈ −0.53). Core inflation falls by
  0.034pp at the trough, about 40% of the published −0.08pp, on both
  inflation concepts. After a fiscal shock ends, output undershoots by about
  45% of the peak as the funds rate comes back.
- **Tracking invariant.** After `init_trac`, solving the baseline reproduces
  LONGBASE to 5.6e-17. **This is an identity, not a validation result** —
  `init_trac` defines the add-factors as minus the residuals at the input
  data, so it holds for *any* input; the repo gates a scrambled-baseline
  version of the same test to keep that honest. Do not cite it as agreement
  with the Fed's data.

Nothing here is a forecast evaluation. LONGBASE is the Board's illustrative
baseline, not a Fed forecast, and no pseudo-out-of-sample accuracy of any kind
is established for this model. The two-quarter LONGBASE backtest in
`VALIDATION.md` is close on GDP growth, unemployment and the funds rate, and
under-projected core PCE inflation (annualized q/q): 2.77% against 4.42% in
2026Q1 (−1.65pp) and 2.76% against 3.42% in 2026Q2 (−0.65pp). That is a
property of the Fed's baseline data, not of this implementation.

## Development

```bash
uv run --extra dev pytest   # tests, including the tracking-invariant gate
uv run --extra dev ruff check src tests examples
```

## License

Code in this repository is released under the [MIT License](LICENSE). Original text and figures are released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) with attribution to PolicyEngine. Third-party data and materials keep their own terms.

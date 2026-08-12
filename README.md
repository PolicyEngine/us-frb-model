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
- **Not implemented:** MCE (rational-expectations) equation variants —
  `Frbus(path, mce=...)` raises `NotImplementedError`. `mcontrol` and
  stochastic simulations are also out of scope.

## Validation

See `VALIDATION.md` for full tables. Summary, in order of how much each one
actually tells you:

- **Cross-validation (the real evidence).** Four shock scenarios — monetary,
  fiscal `egfe`, tax `trp`, and a non-inertial Taylor variant — agree with the
  Fed's own pyfrbus across all 284 endogenous variables and 20 quarters to
  6.0e-9 abs / 4.9e-8 rel. For scale, the Board's own pyfrbus 1.0.0 and 1.1.1
  releases differ from *each other* by 1.3e-8, so this sits at the reference
  implementation's own noise floor.
- **Fiscal multipliers** lie inside published ranges (purchases 0.72 in year 1
  under the inertial Taylor rule, 0.90 in year 2 with the funds rate pegged),
  and the full rule × horizon grid is ordered as theory requires.
- **Tracking invariant.** After `init_trac`, solving the baseline reproduces
  LONGBASE to 5.6e-17. **This is an identity, not a validation result** —
  `init_trac` defines the add-factors as minus the residuals at the input
  data, so it holds for *any* input; the repo gates a scrambled-baseline
  version of the same test to keep that honest. Do not cite it as agreement
  with the Fed's data.

Nothing here is a forecast evaluation. LONGBASE is the Board's illustrative
baseline, not a Fed forecast, and no pseudo-out-of-sample accuracy of any kind
is established for this model.

## Development

```bash
pytest           # tests, including the tracking-invariant gate
ruff check src tests examples
```

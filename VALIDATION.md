# Validation

This implementation is validated three ways against the Federal Reserve's own
`pyfrbus` (vendor/pyfrbus_package) and the April 2026 LONGBASE data vintage.
All experiments use the VAR (backward-looking expectations) model over
**2026Q1–2030Q4** with the standard demo fiscal configuration
(`dfpdbt = 0`, `dfpsrp = 1` where shocked).

Tests 1–3 run as pytest gates (`tests/test_tracking.py`, `tests/test_shock.py`).

## Test 1 — tracking invariant (hard gate)

After `init_trac`, solving the baseline must reproduce LONGBASE for all 284
endogenous variables. Result: **machine precision**.

| metric | value | gate |
|---|---|---|
| max abs error, all endos × 20 quarters | 5.6e-17 | < 1e-8 |
| max relative error | 5.6e-17 | < 1e-10 |

Worst variables (max abs error): frs10 5.6e-17, fpi10 5.6e-17, dpadj 5.4e-20,
dpgap 5.4e-20, delrff 1.4e-20.

## Test 2 — cross-validation against vendor pyfrbus

The identical experiment — `init_trac` then a 100bp shock to `rffintay_aerr`
in 2026Q1 (vendor `demos/example1.py`) — was run in both implementations and
all 284 endogenous variables compared over all 20 quarters. The vendor
reference (`tests/data/vendor_shock_2026q1_2030q4.csv`) was produced by the
Fed's pyfrbus running in a separate Python 3.11 venv with its Newton solver at
`xtol=1e-8`; regenerate it with `scripts/generate_vendor_reference.sh`, which
documents the (out-of-repo) patches needed to run the vendor package on modern
dependencies: drop the `scikit-umfpack` dependency in favor of a
`scipy.sparse.linalg.splu` shim, unpin `sympy==1.3`, convert symengine
expressions via `._sympy_()` in the vendor's Max/Min derivative fallback
(modern symengine otherwise leaves unresolved `Derivative(max(...))` terms),
and pin `pandas<2`.

| metric | value | gate |
|---|---|---|
| max abs difference, all 284 endos × 20 quarters | 6.0e-9 | < 1e-6 |
| max relative difference (denominator clipped at 1e-8) | 4.9e-8 | < 1e-6 |

Key outputs:

| variable | max abs diff | max rel diff |
|---|---|---|
| xgdp | 1.5e-10 | 5.6e-15 |
| pcpi | 8.5e-13 | 2.5e-15 |
| picxfe | 2.3e-13 | 1.2e-13 |
| lur | 4.0e-13 | 9.2e-14 |
| rff | 3.0e-13 | 1.1e-13 |

Worst variables are the near-zero expectational gap terms (zgap05 4.9e-8
relative, zgapc2 4.6e-10, zgap10 3.6e-10); these reflect the two solvers'
respective step tolerances on values of order 1e-4, not a semantic difference.
(With the vendor at its default looser tolerances (`scipy.optimize.root`,
xtol 1e-6), the max abs difference is ~1.7e-5, again concentrated in zgap05.)

### Test 2b — the same check against the current (2026) pyfrbus

The vendored reference is pyfrbus 1.0.0 (files dated 2022-04-06). The Board now
ships pyfrbus 1.1.1 (2026-02-05), so the check above was repeated against that
release to confirm the agreement is not an artifact of one old version. The
model definition is unchanged between the two — `models/model.xml` and the
LONGBASE data are byte-identical — so this isolates solver differences. The
1.1.1 release needs none of the patches listed above: `scikit-umfpack` is now an
optional import with a `splu` fallback, pandas is pinned `>=2.1,<3`, and the
symengine Max/Min issue no longer bites.

| comparison (284 endos × 20 quarters) | max abs | max rel |
|---|---|---|
| ours vs pyfrbus 1.0.0 (the committed reference) | 6.0e-9 | 4.9e-8 |
| ours vs pyfrbus 1.1.1 | 1.4e-8 | 1.8e-7 |
| pyfrbus 1.1.1 vs pyfrbus 1.0.0 | 1.3e-8 | 1.3e-7 |

The third row is the informative one: **the Fed's own two releases differ from
each other by as much as this implementation differs from either.** All three
residuals sit at the same solver-tolerance scale and are concentrated in the
same near-zero series (`wpsn`, `zgap05`). The 1.1.1 solver reuses its LU
factorization across Newton iterations, recomputing only when the residual fails
to halve; that changes the iterate path, not the fixed point, which is why the
differences stay at tolerance scale.

For the tracking invariant (Test 1), pyfrbus 1.1.1 reproduces LONGBASE to
1.1e-8 max abs — this implementation's 5.6e-17 is the tighter of the two.

The committed reference stays on 1.0.0 so the gate has a fixed anchor; this
subsection records the 1.1.1 cross-check. Only the VAR-expectations path was
exercised. The 1.1.1 release also fixes a lead-substitution guard in
`jacobian.py` that affects the MCE path only, which this implementation does not
yet support and which was therefore not tested.

## Test 3 — sanity: monetary tightening

100bp funds-rate shock, deviations from baseline:

| property | value | published FRB/US VAR properties |
|---|---|---|
| rff impact response | +1.000 pp | ~+1 pp |
| xgdp trough | −0.55% (2027Q4) | output falls a few tenths to ~1% after ~2 yrs |
| lur peak | +0.26 pp | rises ~0.1–0.3 pp |
| picxfe trough | −0.034 pp | core inflation falls modestly |

Signs and magnitudes are consistent with the simulation properties described
in the FRB/US documentation (`vendor/frbus_package/documentation/`).

## Solver equivalence notes

- Our solver is a per-period damped Newton on the full 284-equation
  simultaneous system with an analytic sparse Jacobian (sympy
  differentiation, `scipy.sparse.linalg.splu`), defaults `xtol=1e-8`,
  `rtol=5e-4`. The vendor decomposes each period into recursive/simultaneous
  blocks; both approaches solve the same F(x)=0, so solutions agree up to
  solver tolerance, as the tables show.
- MCE (rational expectations) variants are not implemented
  (`NotImplementedError`) and are excluded from validation.

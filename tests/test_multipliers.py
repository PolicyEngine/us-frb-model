"""Test 4: fiscal multipliers gated against published ranges (slow suite).

The published claims for this implementation's fiscal multipliers (government
purchases 0.72 in year 1 under the inertial Taylor rule, 0.99 in year 2 with
the funds rate pegged, tax cut 0.22 in year 1 / 0.32 in year 2) were validated
once when first computed but never gated. These tests recompute the
calendar-year multipliers from the model's standard runs and assert they stay
inside ranges drawn from the published literature, so a regression in the
fiscal block can no longer pass CI silently.

Experiments (VAR expectations, demo fiscal configuration ``dfpdbt=0,
dfpsrp=1``, horizon 2026Q1-2028Q4):

* Government purchases: ``egfe`` is exogenized and raised by 1% of baseline
  real GDP in every quarter, the standard sustained-purchases experiment.
  Multiplier for calendar year N = mean(delta xgdp over year N) /
  mean(delta egfe over year N).
* Tax cut: ``trp`` (the average personal tax rate, the same lever as the
  gated ``tax_trp`` cross-validation scenario) is exogenized and cut by 2pp in
  every quarter. Multiplier = mean(delta xgdp) / mean(ex-ante real revenue
  cut), where the ex-ante cut is 0.02 * baseline (ypn - gtn) deflated by
  baseline pgdp -- i.e. GDP response per dollar of statically-scored tax cut,
  the convention CBO uses.
* Pegged rates: as the purchases run, but with ``dmpex=1`` (exogenous funds
  rate held at the baseline path via ``rfffix``) instead of the inertial
  Taylor rule, so monetary policy does not lean against the stimulus.

These runs share the policy-switch conventions of scripts/scenarios.py
(``set_policy``) but need their own shocks: the gated scenarios apply
one-quarter ``_aerr`` impulses, whereas calendar-year multipliers are defined
over sustained shocks.

Each test is marked ``slow`` (full nonlinear solves, minutes each); CI runs
them in the scheduled-validation job alongside the other heavy revalidation.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

from frbus import Frbus

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scenarios  # noqa: E402  (shared policy-switch conventions)

from .conftest import MODEL_XML

START = pd.Period("2026Q1")
END = pd.Period("2028Q4")

pytestmark = pytest.mark.slow


def year_mean(series: pd.Series, year: int) -> float:
    """Mean over calendar year ``year`` (1-based) of the simulation window."""
    return float(series.iloc[4 * (year - 1) : 4 * year].mean())


def _fresh_model() -> Frbus:
    # exogenize() mutates the instance, so these tests must not reuse the
    # session-scoped model fixture shared with the cross-validation gates.
    return Frbus(str(MODEL_XML))


@pytest.fixture(scope="module")
def purchases_multipliers(longbase):
    """Calendar-year government-purchases multipliers, Taylor rule and pegged."""

    def run(pegged: bool) -> dict[int, float]:
        model = _fresh_model()
        data = longbase.copy()
        scenarios.set_policy("fiscal_egfe", data, START, END)
        if pegged:
            data.loc[START:END, "dmpintay"] = 0
            data.loc[START:END, "dmpex"] = 1
            data.loc[START:END, "rfffix"] = data.loc[START:END, "rff"]
        model.exogenize(["egfe"])
        base = model.init_trac(START, END, data)
        with_adds = base.copy()
        with_adds.loc[START:END, "egfe"] += 0.01 * base.loc[START:END, "xgdp"]
        sim = model.solve(START, END, with_adds)
        dxgdp = sim.loc[START:END, "xgdp"] - base.loc[START:END, "xgdp"]
        degfe = sim.loc[START:END, "egfe"] - base.loc[START:END, "egfe"]
        return {n: year_mean(dxgdp, n) / year_mean(degfe, n) for n in (1, 2)}

    return {"taylor": run(pegged=False), "pegged": run(pegged=True)}


@pytest.fixture(scope="module")
def tax_multipliers(longbase):
    """Calendar-year multipliers for a sustained 2pp personal tax-rate cut."""
    model = _fresh_model()
    data = longbase.copy()
    scenarios.set_policy("tax_trp", data, START, END)
    model.exogenize(["trp"])
    base = model.init_trac(START, END, data)
    with_adds = base.copy()
    with_adds.loc[START:END, "trp"] -= 0.02
    sim = model.solve(START, END, with_adds)
    dxgdp = sim.loc[START:END, "xgdp"] - base.loc[START:END, "xgdp"]
    # Ex-ante real revenue cut: delta-trp times baseline taxable income
    # (tpn = trp * (ypn - gtn)), deflated by the baseline GDP deflator.
    revenue_cut = (
        0.02
        * (base.loc[START:END, "ypn"] - base.loc[START:END, "gtn"])
        / (base.loc[START:END, "pgdp"] / 100)
    )
    return {n: year_mean(dxgdp, n) / year_mean(revenue_cut, n) for n in (1, 2)}


def test_purchases_multiplier_year1_taylor_rule(purchases_multipliers):
    """Year-1 purchases multiplier under the inertial Taylor rule.

    Published value for this implementation: 0.72. Band 0.7-1.0 from:
      * Coenen et al., "Effects of Fiscal Stimulus in Structural Models",
        AEJ: Macro 2012 -- US policy models put the first-year government
        purchases multiplier at roughly 0.7-1.0 when monetary policy responds
        (Table: two-year stimulus, no accommodation).
      * Whalen & Reichling, "The Fiscal Multiplier and Economic Policy
        Analysis in the United States", CBO WP 2015-02 -- CBO's central range
        for purchases spans 0.5-2.5 with a central estimate near 1; a model
        with an active Taylor rule is expected in the lower half.
    """
    m1 = purchases_multipliers["taylor"][1]
    assert 0.7 < m1 < 1.0, f"year-1 purchases multiplier {m1:.3f} outside 0.7-1.0"


def test_purchases_multiplier_year2_pegged_rates(purchases_multipliers):
    """Year-2 purchases multiplier with the funds rate pegged.

    Published value for this implementation: 0.99. Band 0.8-1.2 from Coenen
    et al. (AEJ: Macro 2012): with two years of monetary accommodation the US
    models' purchases multiplier rises to roughly 1 (their Figure 4 range is
    about 0.9-1.3 across models); the FRB/US documentation likewise reports
    multipliers near or slightly above 1 when the funds rate does not lean
    against the stimulus.
    """
    m2 = purchases_multipliers["pegged"][2]
    assert 0.8 < m2 < 1.2, f"year-2 pegged purchases multiplier {m2:.3f} outside 0.8-1.2"


def test_tax_cut_multiplier_years_1_and_2(tax_multipliers):
    """Personal tax-cut multiplier, years 1 and 2.

    Published values for this implementation: 0.22 (year 1) and 0.32
    (year 2). Band 0.15-0.45 from Whalen & Reichling (CBO WP 2015-02): CBO
    puts the two-year multiplier on broad-based tax cuts at roughly 0.3
    (range 0.1-0.6 across instruments); backward-looking-expectations models
    sit near the center for a temporary rate cut, so 0.15-0.45 gates on
    economics without pinning the exact decimal.
    """
    m1, m2 = tax_multipliers[1], tax_multipliers[2]
    assert 0.15 < m1 < 0.45, f"year-1 tax-cut multiplier {m1:.3f} outside 0.15-0.45"
    assert 0.15 < m2 < 0.45, f"year-2 tax-cut multiplier {m2:.3f} outside 0.15-0.45"
    assert m2 > m1, "tax-cut multiplier should build over time under VAR expectations"

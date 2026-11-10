"""Test 4: fiscal multipliers gated against published ranges (slow suite).

The published claims for this implementation's fiscal multipliers (government
purchases 0.72 in year 1 under the inertial Taylor rule, 0.90 in year 2 with
the funds rate pegged, tax cut 0.22 in year 1 / 0.32 in year 2) were validated
once when first computed but never gated. These tests recompute the
calendar-year multipliers from the model's standard runs and assert they stay
inside ranges drawn from the published literature, so a regression in the
fiscal block can no longer pass CI silently.

Recomputed 2026-08 on the full purchases grid (both rules x both horizons),
so the headline pair is no longer quoted without its context:

    rule                     year 1   year 2   year 3
    inertial Taylor          0.725    0.643    0.458
    non-inertial Taylor      0.596    0.417    0.306
    funds rate pegged        0.769    0.905    1.010

The pattern is the economically informative part: with an active rule the
multiplier *decays* as policy leans against the stimulus (and decays faster
under the non-inertial rule, which raises rff +0.59pp in year 1 against
+0.23pp for the inertial one), whereas under a peg it *builds* towards 1.
Both peg implementations -- ``dmpex=1`` with ``rfffix`` on the baseline path,
and ``exogenize(['rff'])`` -- give identical multipliers to 4dp.

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

Each test is marked ``slow`` because it drives extra full nonlinear solves
beyond the shared fixtures; in practice the whole module runs in about a
second, so CI gates it on every push (``correctness-gates``) as well as in the
scheduled-validation job.
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
            # These MUST go in before init_trac. Setting them afterwards, on
            # the shocked frame only, leaves the rff block's add-factor holding
            # a wedge computed under the Taylor rule, and the funds rate then
            # settles ~0.1pp BELOW its own rfffix target -- an unintended
            # easing that inflates the multiplier by ~0.09. See VALIDATION.md,
            # "Hazard: policy switches must be set before init_trac".
            data.loc[START:END, "dmpintay"] = 0
            data.loc[START:END, "dmpex"] = 1
            data.loc[START:END, "rfffix"] = data.loc[START:END, "rff"]
        model.exogenize(["egfe"])
        base = model.init_trac(START, END, data)
        with_adds = base.copy()
        with_adds.loc[START:END, "egfe"] += 0.01 * base.loc[START:END, "xgdp"]
        sim = model.solve(START, END, with_adds)
        if pegged:
            # A peg that is not exactly a peg is the failure mode above; assert
            # it rather than trusting the switches did what they look like.
            drff = (sim.loc[START:END, "rff"] - base.loc[START:END, "rff"]).abs()
            assert drff.max() < 1e-10, (
                f"funds rate moved {drff.max():.3e}pp under a supposed peg"
            )
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

    Published value for this implementation: 0.72. Band 0.7-1.0; sources
    and exact page references in docs/benchmarks.md:
      * Coenen et al. (IMF WP/10/73; AEJ: Macro 2012), Fig. 25 (WP p. 53),
        two years of government consumption, no monetary accommodation: the
        six US models' year-1 responses run from approx. 0.7 (QUEST) to 1.1
        (BoC-GEM), FRB-US approx. 0.95. These are chart readings (+-0.1);
        the paper has no multiplier table.
      * Whalen & Reichling (CBO WP 2015-02), Table 2, "Fed responds
        typically" columns, converted to a sustained shock: year 1 0.45-1.82.
        CBO's 0.5-2.5 purchases range (CBO Feb 2015 Table 3) assumes the Fed
        did NOT tighten, so it is not the comparator for an active rule.
    """
    m1 = purchases_multipliers["taylor"][1]
    assert 0.7 < m1 < 1.0, f"year-1 purchases multiplier {m1:.3f} outside 0.7-1.0"


def test_purchases_multiplier_year2_pegged_rates(purchases_multipliers):
    """Year-2 purchases multiplier with the funds rate pegged.

    Recomputed value for this implementation: 0.90 (the 0.99 previously
    quoted in this file was stale -- it is close to the year-*3* value, 1.01).
    Band 0.8-1.2. Coenen et al. Fig. 25 (WP p. 53), two years of government
    consumption with two years of accommodation: FRB-US year 2 approx. 1.25
    (chart reading), so 0.90 sits below the paper's own FRB-US line; the
    "0.9-1.3" in the paper's text (WP p. 14) is for one year of government
    INVESTMENT with no accommodation, not this cell. CBO's limited-Fed-response
    path (Whalen & Reichling Table 2) converted to a sustained shock gives
    0.50-2.50 in year 2. See docs/benchmarks.md.
    """
    m2 = purchases_multipliers["pegged"][2]
    assert 0.8 < m2 < 1.2, f"year-2 pegged purchases multiplier {m2:.3f} outside 0.8-1.2"


def test_purchases_multiplier_grid_is_ordered_as_theory_requires(
    purchases_multipliers,
):
    """The two cells the headline pair leaves ungated, plus the sign pattern.

    Quoting "0.72 under the Taylor rule" and "0.90 with rates pegged" from
    different years invites the reader to compare them as if they were the same
    experiment. They are not, and only the full grid shows the mechanism:

      * Monetary offset must make the peg multiplier the larger one at BOTH
        horizons -- otherwise the endogenous policy response has the wrong
        sign somewhere in the fiscal block.
      * Under an active rule the multiplier must decay across years (policy
        leans harder as the stimulus cumulates into the output gap).
      * Under a peg it must build (no offset, and the accelerator/stock
        adjustment channels take time).

    Observed 2026-08: Taylor 0.725 -> 0.643, pegged 0.769 -> 0.905.
    """
    taylor, pegged = purchases_multipliers["taylor"], purchases_multipliers["pegged"]

    for year in (1, 2):
        assert pegged[year] > taylor[year], (
            f"year-{year}: pegged multiplier {pegged[year]:.3f} is not above "
            f"the active-rule multiplier {taylor[year]:.3f}; monetary offset "
            "has the wrong sign"
        )
    assert taylor[2] < taylor[1], (
        f"active-rule multiplier rose ({taylor[1]:.3f} -> {taylor[2]:.3f}); "
        "an endogenous policy response must damp a sustained stimulus"
    )
    assert pegged[2] > pegged[1], (
        f"pegged multiplier fell ({pegged[1]:.3f} -> {pegged[2]:.3f})"
    )
    # The ungated year-1 pegged cell, for completeness (observed 0.769).
    assert 0.6 < pegged[1] < 1.1, f"year-1 pegged multiplier {pegged[1]:.3f}"
    # The ungated year-2 active-rule cell (observed 0.643).
    assert 0.4 < taylor[2] < 0.9, f"year-2 active-rule multiplier {taylor[2]:.3f}"


def test_tax_cut_multiplier_years_1_and_2(tax_multipliers):
    """Personal tax-cut multiplier, years 1 and 2.

    Published values for this implementation: 0.22 (year 1) and 0.32
    (year 2). Band 0.15-0.45. Whalen & Reichling (CBO WP 2015-02) Table 1
    does NOT give a central tax multiplier of 0.3: its rows are two-year tax
    cuts for lower- and middle-income people 0.3-1.5 and a one-year tax cut
    for higher-income people 0.1-0.6, both in the Fed-not-tightening regime
    (CBO Feb 2015 Table 3 note a). trp is an across-the-board average rate,
    so the economically relevant range lies between those rows; the band
    gates on economics, not on a published point. See docs/benchmarks.md.
    """
    m1, m2 = tax_multipliers[1], tax_multipliers[2]
    assert 0.15 < m1 < 0.45, f"year-1 tax-cut multiplier {m1:.3f} outside 0.15-0.45"
    assert 0.15 < m2 < 0.45, f"year-2 tax-cut multiplier {m2:.3f} outside 0.15-0.45"
    assert m2 > m1, "tax-cut multiplier should build over time under VAR expectations"

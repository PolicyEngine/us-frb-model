"""Inflation transmission and transfers: published comparator, channels, committed JSON.

Two groups:

* fast (no solve): the committed ``results/inflation_transmission.json``
  against the Board's own published simulation of the post-2018 model
  (Laforte 2018, FEDS Notes, Figure 2, "New Version"), and the channel
  properties the write-up in docs/inflation-transmission.md relies on;
* slow: re-run ``scripts/inflation_transmission.py`` and require the committed
  JSON to be current.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import inflation_transmission as it  # noqa: E402

COMMITTED = json.loads((REPO / "results" / "inflation_transmission.json").read_text())

# Laforte (2018), "Overview of the changes to the FRB/US model (2018)", FEDS
# Notes, doi:10.17016/2380-7172.2306, Figure 2 "Responses to a 100 bps
# increase in the Fed funds rate (VAR-based expectations)", accessible-table
# values for the New Version; shock in 2020Q1, so quarter 8 is 2021Q4.
FED_2018_NEW = {"core_pce_trough": -0.0345, "output_gap_trough": -0.4861, "lur_peak": 0.2189}
FED_2018_PREVIOUS = {"core_pce_trough": -0.0617}


def _laforte_checks(p):
    assert p["picxfe_trough"][0] == pytest.approx(FED_2018_NEW["core_pce_trough"], rel=0.10)
    assert p["xgap2_trough"][0] == pytest.approx(FED_2018_NEW["output_gap_trough"], rel=0.10)
    # and well short of the pre-2018 model, so the old comparator is not like-for-like
    assert p["picxfe_trough"][0] > 0.7 * FED_2018_PREVIOUS["core_pce_trough"]


def test_like_for_like_run_matches_laforte_2018():
    """Primary published-comparator gate: Laforte's own design.

    Shock in 2020Q1, the Board's programs/pings.prg settings (no ZLB, no
    thresholds, rstar fixed), VAR expectations. All three responses within 10%
    of the note (observed 0.96x, 0.97x and 1.04x on the October 2026 LONGBASE;
    0.96x, 0.98x and 1.01x on the April 2026 LONGBASE).
    Caveat: the 2020Q1 baseline here is realised history, not the 2018
    LONGBASE projection Laforte shocked (readable only with EViews), so this is
    close to, not exactly, a replication.
    """
    p = COMMITTED["ping_sweep_fed_pings_settings"]["2020Q1"]
    _laforte_checks(p)
    assert p["lur_peak"][0] == pytest.approx(FED_2018_NEW["lur_peak"], rel=0.10)
    # Timing: the note has all three in quarter 8 (2021Q4). The output-gap
    # trough is exactly there; core PCE and unemployment land in quarters 8-10
    # (October 2026 LONGBASE: q9 and q9; April 2026 LONGBASE: q9 and q10).
    assert p["xgap2_trough"][1] == "2021Q4"
    assert p["picxfe_trough"][1] in ("2021Q4", "2022Q1", "2022Q2")
    assert p["lur_peak"][1] in ("2021Q4", "2022Q1", "2022Q2")


@pytest.mark.parametrize("run", ["2026q1", "2040q1_fed_pings_settings"])
def test_published_window_runs_match_laforte_core_and_gap(run):
    """Core PCE and the output gap are not start-date dependent (see the sweep),
    so the published 2026Q1 run and the 2040Q1 pings run are held to 10% too.
    The unemployment peak is not asserted against Laforte here: it depends on
    the start date (sweep below), and these runs are not Laforte's experiment.
    """
    p = COMMITTED["ping"]["base"] if run == "2026q1" else COMMITTED["ping_2040_fed_pings_settings"]
    _laforte_checks(p)
    if run == "2026q1":
        assert p["picxfe_trough"][1] == "2027Q4"  # quarter 8 after a 2026Q1 shock


def test_ping_core_pce_is_not_baseline_or_settings_dependent():
    """The Board's pings.prg settings from 2040Q1 give the same core PCE trough."""
    a = COMMITTED["ping"]["base"]["picxfe_trough"][0]
    b = COMMITTED["ping_2040_fed_pings_settings"]["picxfe_trough"][0]
    assert b == pytest.approx(a, rel=0.05)


def test_start_date_sweep():
    """The 100bp ping from eight start dates (pings settings, 40 quarters).

    Core PCE and the output gap stay within 10% of Laforte from every start
    date. The unemployment peak rises with the start date (1.04x in 2020Q1 to
    1.38x in 2035Q1, back to 1.19x in 2040Q1): the unemployment response per
    unit of output gap drifts with the baseline. Its 0.90-1.45x range is a
    sanity bound fitted to the October 2026 LONGBASE, NOT a published
    comparison; the published comparison is the 2020Q1 test above. The real
    regression guard is test_committed_json_is_current (abs 1e-6).
    """
    sweep = COMMITTED["ping_sweep_fed_pings_settings"]
    assert list(sweep) == list(it.SWEEP_STARTS)
    for start, p in sweep.items():
        assert p["picxfe_trough"][0] == pytest.approx(FED_2018_NEW["core_pce_trough"], rel=0.10), (
            start
        )
        assert p["xgap2_trough"][0] == pytest.approx(FED_2018_NEW["output_gap_trough"], rel=0.10), (
            start
        )
        ratio = p["lur_peak"][0] / FED_2018_NEW["lur_peak"]
        # lower end 0.90, not 1.00: the 2020Q1 run is 1.04x here and 1.01x on the
        # April 2026 LONGBASE, too close to 1.00 for a vintage-robust bound
        assert 0.90 <= ratio <= 1.45, (start, ratio)


def test_2020q1_demo_settings_is_recorded_not_gated():
    """With the demo settings the ZLB binds from a near-zero 2020 funds rate,
    so the response is weaker; recorded for completeness only."""
    d = COMMITTED["ping_2020q1_demo_settings"]
    lfl = COMMITTED["ping_sweep_fed_pings_settings"]["2020Q1"]
    assert abs(d["xgap2_trough"][0]) < abs(lfl["xgap2_trough"][0])


def test_var_expectations_carry_the_inflation_response():
    def get(block, r):
        return r["picxfe_trough"][0] if block == "ping" else r["core_pce_4q_2023q4"]

    for block in ("ping", "episode_A"):
        base = get(block, COMMITTED[block]["base"])
        # zpicxfe/zpieci fixed: >90% of the response disappears
        assert abs(get(block, COMMITTED[block]["zexp_fixed"])) < 0.1 * abs(base)
        # long-run expectations ptr fixed: <10% of the response
        assert get(block, COMMITTED[block]["ptr_fixed"]) == pytest.approx(base, rel=0.10)
        # exchange-rate channel is live: 10-40% of the response
        share = 1 - get(block, COMMITTED[block]["fx_fixed"]) / base
        assert 0.10 < share < 0.40, f"{block} fx share {share:.2f}"


def test_nkpc_coefficient_vintage_barely_moves_the_response():
    """Swapping the 2013 NKPC parameters in changes the trough by < 5%.

    So the 2013-14 published -0.08 is not reproduced by the structural slopes
    alone; the Board attributes the smaller response to re-estimating the whole
    wage-price block (Laforte 2018), which includes the VAR-expectations system.
    """
    base = COMMITTED["ping"]["base"]["picxfe_trough"][0]
    for v in ("slope_2013", "bayes_2013", "ml_8507"):
        assert COMMITTED["ping"][v]["picxfe_trough"][0] == pytest.approx(base, rel=0.05)


def test_transfers_reach_households_one_for_one():
    t = COMMITTED["income"]["transfers_peg"]
    # gtr is deflated by pgdp, yht by pcnia: the ratio is pgdp/pcnia, ~1.02
    assert t["dyht_per_dgtr_year1"] == pytest.approx(1.02, abs=0.01)


def test_mpc_out_of_transfers_equals_mpc_out_of_labour_income():
    t, lab = COMMITTED["income"]["transfers_peg"], COMMITTED["income"]["labour_peg"]
    assert t["dc_per_dincome_q1"] == pytest.approx(lab["dc_per_dincome_q1"], abs=0.03)
    # and the impact MPC is the hand-to-mouth term, y_eco(4)*y_ecnia(1)*ecnia/(yhl+yht)
    for run in (t, lab, COMMITTED["income"]["transfers_peg_htm040"]):
        assert run["dc_per_dincome_q1"] == pytest.approx(run["htm_predicted_q1"], abs=0.03)


def test_hand_to_mouth_share_drives_the_transfers_multiplier():
    i = COMMITTED["income"]
    assert i["transfers_taylor_srp"]["multiplier"]["1"] == pytest.approx(0.283, abs=0.005)
    lift = (
        i["transfers_taylor_srp_htm040"]["multiplier"]["1"]
        / i["transfers_taylor_srp"]["multiplier"]["1"]
    )
    # raising y_eco(4) from 0.3075 to 0.40 scales the multiplier roughly in proportion
    assert lift == pytest.approx(0.40 / 0.3075, rel=0.10)


@pytest.mark.slow
def test_committed_json_is_current(longbase):
    fresh = json.loads(json.dumps(it.compute(longbase)))

    def close(a, b, path=""):
        if isinstance(a, dict):
            assert a.keys() == b.keys(), path
            for k in a:
                close(a[k], b[k], f"{path}.{k}")
        elif isinstance(a, list):
            assert len(a) == len(b), path
            for n, (x, y) in enumerate(zip(a, b, strict=True)):
                close(x, y, f"{path}[{n}]")
        elif isinstance(a, float):
            assert a == pytest.approx(b, abs=1e-6), path
        else:
            assert a == b, path

    close(fresh, COMMITTED)


@pytest.mark.slow
def test_episode_matches_vendor_pyfrbus(longbase):
    """The 2022-23 counterfactual path is the Board's pyfrbus path.

    Reference CSVs: scripts/generate_vendor_episode_reference.sh (Board's
    pyfrbus, patched copy, Newton xtol=1e-8). Same tolerances as the
    cross-validation gate in tests/test_shock.py.
    """
    import episode_2022_tightening as ep
    import pandas as pd

    from frbus import Frbus

    model = Frbus(str(ep.MODEL_XML))
    base = model.init_trac(ep.START, ep.END, ep._frame(longbase, None))
    hist = model.solve(ep.START, ep.END, base)
    w = slice(ep.START, ep.END)
    cf_in = base.copy()
    cf_in.loc[w, "rfffix"] = longbase.loc[w, "rffmin"]
    cf = model.solve(ep.START, ep.END, cf_in)
    for name, ours in (("hist", hist), ("cf", cf)):
        vendor = pd.read_csv(
            REPO / "tests" / "data" / f"vendor_episode_2022_{name}.csv", index_col=0
        )
        vendor.index = pd.PeriodIndex(vendor.index, freq="Q")
        diff = (ours.loc[w, vendor.columns] - vendor).abs()
        rel = diff / vendor.abs().clip(lower=1e-8)
        assert diff.to_numpy().max() < 1e-6, f"{name}: max abs {diff.to_numpy().max():.3e}"
        assert rel.to_numpy().max() < 1e-6, f"{name}: max rel {rel.to_numpy().max():.3e}"

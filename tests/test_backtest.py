"""Hermetic test of the LONGBASE-vs-outturn backtest machinery.

Runs scripts/backtest_longbase.py's report pipeline on the committed FRED
snapshot (tests/data/fred_outturns_snapshot.csv, fetched 2026-11-16), with no
network access, and asserts the machinery works: every series/quarter pair is
compared and the errors are finite and computed the documented way.

Deliberately NOT asserted: that LONGBASE was right. The baseline is the Fed's
projection, not this implementation's output, so its accuracy is reported
(VALIDATION.md, "LONGBASE vs outturns") rather than gated. For the record, the
October 2026 vintage's first projected quarter (2026Q3) missed GDP growth by
-1.23pp (2.14% vs 3.37%) and core PCE inflation by +0.80pp (3.27% vs 2.47%);
unemployment and the funds rate were within 0.2pp. The April 2026 vintage's
2026Q1-Q2 record (core PCE -1.65pp/-0.65pp) is frozen in
backtests/longbase_2026-04_vs_outturns.md.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import backtest_longbase as bt  # noqa: E402

from .conftest import LONGBASE


def test_backtest_report_from_committed_snapshot(longbase, tmp_path):
    observations = bt.load_snapshot()
    assert set(observations) == set(bt.SERIES), "snapshot must cover all four series"

    report = bt.build_report(observations, longbase)
    rows = {(r["fred_id"], r["quarter"]): r for r in report["rows"]}

    # Every series has both observable quarters, no NaNs, errors consistent.
    for series_id in bt.SERIES:
        for quarter in bt.QUARTERS:
            row = rows[(series_id, str(quarter))]
            # error is computed before rounding, so allow the rounding slack
            assert abs(row["error"] - (row["longbase"] - row["outturn"])) < 2e-3
            for key in ("longbase", "outturn", "error"):
                assert row[key] == row[key], f"NaN in {series_id} {quarter} {key}"

    # Values are on economically sensible scales (machinery check: catches a
    # units/aggregation bug, not a judgment on the Fed's forecast).
    for row in report["rows"]:
        assert -10 < row["longbase"] < 15 and -10 < row["outturn"] < 15, row

    # Markdown/JSON writers round-trip via main() on the snapshot path.
    assert bt.main(["--out", str(tmp_path)]) == 0
    written = json.loads((tmp_path / "longbase_vs_outturns.json").read_text())
    assert written["rows"] == report["rows"]
    assert "LONGBASE vs outturns" in (tmp_path / "longbase_vs_outturns.md").read_text()


def test_backtest_uses_pinned_longbase_vintage():
    # The report must describe the vintage this repo actually pins.
    assert bt.LONGBASE == LONGBASE


def test_core_pce_baseline_is_on_the_outturn_concept(longbase):
    """picxfe is 400*dlog(pcxfe) (model.xml), a log rate; the FRED outturn is
    compounded. The baseline must be compounded too, or the core PCE error
    carries a ~0.04pp concept gap at 2.7% that grows with inflation."""
    import numpy as np

    baseline = bt.baseline_paths(longbase)["PCEPILFE"]
    compounded = np.expm1(longbase["picxfe"] / 100.0) * 100.0
    for quarter in bt.QUARTERS:
        assert abs(baseline[quarter] - compounded[quarter]) < 1e-6
        assert baseline[quarter] > longbase["picxfe"][quarter]


def test_committed_report_matches_the_snapshot(longbase):
    """backtests/longbase_vs_outturns.json is what the pinned snapshot and
    LONGBASE produce (catches a committed report left stale after either moves)."""
    committed = json.loads(
        (
            Path(__file__).resolve().parents[1] / "backtests" / "longbase_vs_outturns.json"
        ).read_text()
    )
    fresh = bt.build_report(bt.load_snapshot(), longbase)
    assert committed["rows"] == fresh["rows"]
    assert committed["quarters"] == fresh["quarters"]


def test_frozen_april_record_core_pce_rows():
    """The published April-vintage core PCE errors, as frozen."""
    frozen = json.loads(
        (
            Path(__file__).resolve().parents[1] / "backtests" / "longbase_2026-04_vs_outturns.json"
        ).read_text()
    )
    rows = {r["quarter"]: r for r in frozen["rows"] if r["fred_id"] == "PCEPILFE"}
    assert (rows["2026Q1"]["longbase"], rows["2026Q1"]["outturn"]) == (2.77, 4.422)
    assert rows["2026Q1"]["error"] == -1.652
    assert rows["2026Q2"]["error"] == -0.654


def test_core_pce_2026q1_miss_is_a_price_equation_residual(model, longbase):
    """Diagnosis of the April vintage's -1.65pp core PCE miss (VALIDATION.md,
    "What drives the -1.65pp"), on the side the tree can reproduce.

    In the October vintage 2026Q1-Q2 are history. That history puts core PCE
    at 3.94% and 3.31% (the frozen record's August FRED snapshot had 4.42% and
    3.42%), and the residual of the picxfe equation at the data is +1.56pp in
    2026Q1 against a 2021-25 standard deviation of 0.77pp, then +0.13pp in
    2026Q2. These pin the October LONGBASE, not a published figure, and move
    with a new vintage.
    """
    core = bt.baseline_paths(longbase)["PCEPILFE"]
    assert abs(core["2026Q1"] - 3.937) < 5e-3
    assert abs(core["2026Q2"] - 3.314) < 5e-3
    # The October history's 2026Q1 index level is the quarterly average of the
    # committed FRED snapshot. (The snapshot starts in January 2026, so the
    # 2025Q4 level behind the 3.94 growth rate is not checked here.)
    snap = bt.load_snapshot()["PCEPILFE"]
    q1 = snap[snap.index.to_period("Q") == "2026Q1"].mean()
    assert abs(q1 - longbase["pcxfe"]["2026Q1"]) < 5e-3

    trac = model.init_trac("2015Q1", "2026Q2", longbase)["picxfe_trac"]
    assert abs(trac["2026Q1"] - 1.558) < 5e-3
    assert abs(trac["2026Q2"] - 0.125) < 5e-3
    assert abs(trac["2025Q4"] - 0.064) < 5e-3
    sd_2021_25 = trac["2021Q1":"2025Q4"].std()
    assert abs(sd_2021_25 - 0.768) < 5e-3
    assert abs(trac["2015Q1":"2019Q4"].std() - 0.448) < 5e-3
    assert trac["2026Q1"] > 2 * sd_2021_25
    # The part the equation accounts for: below the April baseline's 2.49 in
    # 2026Q1, well above its 2.46 in 2026Q2.
    fitted = longbase["picxfe"] - trac
    assert abs(fitted["2026Q1"] - 2.303) < 5e-3
    assert abs(fitted["2026Q2"] - 3.135) < 5e-3

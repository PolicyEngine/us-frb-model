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

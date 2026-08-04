"""Backtest the April 2026 LONGBASE baseline against realized FRED outturns.

The LONGBASE.TXT vintage this repo pins (April 2026) carries the Fed staff's
near-term projected path. Some of those quarters are now observable, so this
script compares the baseline against published outturns for the four headline
series and writes a small JSON + markdown report:

    variable  FRED id    comparison
    --------  ---------  ------------------------------------------------
    xgdp      GDPC1      real GDP growth, annualized q/q % from levels
    lur       UNRATE     unemployment rate, quarterly average of months
    picxfe    PCEPILFE   core PCE inflation, annualized q/q % of the
                         quarterly-average index
    rff       FEDFUNDS   federal funds rate, quarterly average of months

By default the realized values come from the committed snapshot
(tests/data/fred_outturns_snapshot.csv) so the run is hermetic; pass
``--fetch`` to pull fresh values from FRED's public CSV endpoints
(https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>) and
``--write-snapshot`` to refresh the committed snapshot from what was fetched.

This is a REPORT, not a gate: LONGBASE is the Fed's baseline, not this
implementation's forecast, so its accuracy is recorded (see VALIDATION.md,
"LONGBASE vs outturns") but never enforced. The hermetic machinery itself is
tested in tests/test_backtest.py.

Usage:
    uv run python scripts/backtest_longbase.py [--fetch] [--write-snapshot]
        [--out DIR]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
LONGBASE = REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"
SNAPSHOT = REPO / "tests" / "data" / "fred_outturns_snapshot.csv"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}"

#: quarters of the April 2026 vintage that are now observable
QUARTERS = [pd.Period("2026Q1"), pd.Period("2026Q2")]

#: FRED series ids and how each maps onto a LONGBASE variable
SERIES = {
    "GDPC1": {"variable": "xgdp", "concept": "real GDP growth (annualized q/q %)"},
    "UNRATE": {"variable": "lur", "concept": "unemployment rate (%, quarterly avg)"},
    "PCEPILFE": {"variable": "picxfe", "concept": "core PCE inflation (annualized q/q %)"},
    "FEDFUNDS": {"variable": "rff", "concept": "federal funds rate (%, quarterly avg)"},
}


def fetch_fred(series_id: str) -> pd.Series:
    """Fetch one series from FRED's public CSV endpoint."""
    with urllib.request.urlopen(FRED_CSV.format(id=series_id), timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    frame = pd.read_csv(io.StringIO(raw), na_values=".")
    frame.columns = ["date", "value"]
    return pd.Series(
        frame["value"].to_numpy(), index=pd.to_datetime(frame["date"]), name=series_id
    ).dropna()


def load_snapshot(path: Path = SNAPSHOT) -> dict[str, pd.Series]:
    """Load the committed raw-observation snapshot as {series_id: series}."""
    frame = pd.read_csv(path, parse_dates=["date"])
    return {
        sid: grp.set_index("date")["value"].rename(sid)
        for sid, grp in frame.groupby("series_id")
    }


def write_snapshot(observations: dict[str, pd.Series], path: Path = SNAPSHOT) -> None:
    rows = [
        {"series_id": sid, "date": date.date().isoformat(), "value": value}
        for sid, series in sorted(observations.items())
        for date, value in series.items()
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def to_quarterly(series_id: str, series: pd.Series) -> pd.Series:
    """Reduce raw FRED observations to the quarterly concept in SERIES."""
    quarterly = series.groupby(pd.PeriodIndex(series.index, freq="Q")).mean()
    if series_id in ("GDPC1", "PCEPILFE"):
        # Annualized compounded quarter-on-quarter percent change.
        return ((quarterly / quarterly.shift(1)) ** 4 - 1) * 100
    return quarterly


def baseline_paths(longbase: pd.DataFrame) -> dict[str, pd.Series]:
    """The LONGBASE near-term path for each concept, on QUARTERS."""
    growth = (longbase["xgdp"] / longbase["xgdp"].shift(1)) ** 4 * 100 - 100
    return {
        "GDPC1": growth,
        "UNRATE": longbase["lur"],
        "PCEPILFE": longbase["picxfe"],
        "FEDFUNDS": longbase["rff"],
    }


def build_report(observations: dict[str, pd.Series], longbase: pd.DataFrame) -> dict:
    """Compare LONGBASE against realized outturns; return the report dict."""
    baselines = baseline_paths(longbase)
    rows = []
    for series_id, meta in SERIES.items():
        realized = to_quarterly(series_id, observations[series_id])
        for quarter in QUARTERS:
            if quarter not in realized.index:
                continue
            actual = float(realized[quarter])
            projected = float(baselines[series_id][quarter])
            rows.append(
                {
                    "quarter": str(quarter),
                    "fred_id": series_id,
                    "variable": meta["variable"],
                    "concept": meta["concept"],
                    "longbase": round(projected, 3),
                    "outturn": round(actual, 3),
                    "error": round(projected - actual, 3),
                }
            )
    return {
        "description": "April 2026 LONGBASE baseline vs realized FRED outturns "
        "(error = LONGBASE - outturn). Report only; not a gate.",
        "vintage": "LONGBASE.TXT, April 2026",
        "quarters": [str(q) for q in QUARTERS],
        "rows": rows,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# LONGBASE vs outturns",
        "",
        f"{report['vintage']} near-term path against realized FRED data "
        f"({', '.join(report['quarters'])}). Error = LONGBASE − outturn. "
        "This is a report on the Fed's baseline, not a gate.",
        "",
        "| quarter | variable | concept | LONGBASE | outturn | error |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["rows"]:
        lines.append(
            f"| {r['quarter']} | {r['variable']} ({r['fred_id']}) | {r['concept']} "
            f"| {r['longbase']:.2f} | {r['outturn']:.2f} | {r['error']:+.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="fetch fresh values from FRED instead of using the committed snapshot",
    )
    parser.add_argument(
        "--write-snapshot",
        action="store_true",
        help="with --fetch: rewrite the committed snapshot from the fetched values",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO / "backtests",
        help="directory for the JSON/markdown report (default: backtests/)",
    )
    args = parser.parse_args(argv)

    if args.fetch:
        window = pd.Timestamp("2025-07-01")  # keep one prior quarter for growth rates
        observations = {
            sid: fetch_fred(sid).loc[lambda s: s.index >= window] for sid in SERIES
        }
        if args.write_snapshot:
            write_snapshot(observations)
            print(f"snapshot written: {SNAPSHOT}")
    else:
        observations = load_snapshot()

    from frbus import load_data  # deferred: not needed to just refresh the snapshot

    report = build_report(observations, load_data(str(LONGBASE)))
    args.out.mkdir(parents=True, exist_ok=True)
    json_path = args.out / "longbase_vs_outturns.json"
    md_path = args.out / "longbase_vs_outturns.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(render_markdown(report))
    print(render_markdown(report))
    print(f"wrote {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

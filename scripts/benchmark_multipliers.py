"""Fiscal multipliers on the closures the published benchmarks use.

The gated multipliers (tests/test_multipliers.py, scripts/scenario_sweep.py)
run under one closure: the inertial Taylor rule and the demo fiscal rule
``dfpsrp=1``, under which the trend personal tax rate ``trpt`` rises
*during* the stimulus to pull the federal surplus ratio back to target. The
published comparators use different closures (docs/benchmarks.md):

* CBO's ARRA multipliers (Feb 2015, Table 3) assume the Fed did not tighten
  in response to the stimulus.
* CBO's "Fed responds typically" demand path (Whalen & Reichling 2015,
  Table 2) assumes the usual monetary response and no tax offset.
* Coenen et al. (2010/2012) hold taxes unchanged during the stimulus and
  stabilise debt afterwards; monetary policy follows its rule or is held
  fixed for one or two years.

This script reruns the 8-quarter (2026Q1-2027Q4), 1%-of-baseline-GDP
purchases, transfers and personal-tax-rate experiments on a 2 x 2 grid:

    monetary  taylor  inertial Taylor rule (the default, dmpintay=1)
              peg     funds rate held on the baseline path (dmpex=1,
                      rfffix=baseline rff, set BEFORE init_trac)
    fiscal    srp     surplus-ratio rule active (dfpsrp=1, the demo setting)
              exog    trend tax rates exogenous (dfpex=1, dfpsrp=0) through
                      2030Q4, so nothing claws the stimulus back in-window

and reports calendar-year multipliers (mean delta xgdp over year N / mean
delta instrument over year N) plus the year-1 mean moves in rff and trp that
explain them. Taxes: ``trp`` is exogenized, so the fiscal rule cannot act
through it and the srp/exog rows should be nearly identical (a check that the
closure switch does what it says).

About 12 init_trac + 12 solves; a few seconds, but take the heavy-job lock.

    uv run python scripts/benchmark_multipliers.py [--out DIR]

writes results/benchmark_multipliers.json and .md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from frbus import Frbus, load_data  # noqa: E402

MODEL_XML = REPO / "vendor" / "pyfrbus_package" / "models" / "model.xml"
LONGBASE = REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"

START = pd.Period("2026Q1")
END = pd.Period("2030Q4")
SHOCK_END = pd.Period("2027Q4")
SIZE = 0.01  # share of baseline real GDP

INSTRUMENTS = ("purchases", "transfers", "taxes")
MONETARY = ("taylor", "peg")
FISCAL = ("srp", "exog")


def year_mean(series: pd.Series, year: int) -> float:
    return float(series.iloc[4 * (year - 1) : 4 * year].mean())


def run(longbase: pd.DataFrame, instrument: str, monetary: str, fiscal: str) -> dict:
    model = Frbus(str(MODEL_XML))
    data = longbase.copy()
    w = slice(START, END)
    data.loc[w, "dfpdbt"] = 0
    if fiscal == "srp":
        data.loc[w, "dfpex"] = 0
        data.loc[w, "dfpsrp"] = 1
    else:
        data.loc[w, "dfpex"] = 1
        data.loc[w, "dfpsrp"] = 0
    if monetary == "peg":
        data.loc[w, "dmpintay"] = 0
        data.loc[w, "dmpex"] = 1
        data.loc[w, "rfffix"] = data.loc[w, "rff"]
    exo = {"purchases": ["egfe"], "transfers": [], "taxes": ["trp"]}[instrument]
    if exo:
        model.exogenize(exo)
    base = model.init_trac(START, END, data)
    adds = base.copy()
    s = slice(START, SHOCK_END)
    if instrument == "purchases":
        adds.loc[s, "egfe"] += SIZE * base.loc[s, "xgdp"]
    elif instrument == "transfers":
        adds.loc[s, "gtr_aerr"] += SIZE * base.loc[s, "xgdp"]
    else:
        # cut trp by the rate that is ex ante worth 1% of GDP in real revenue
        taxable = (base.loc[s, "ypn"] - base.loc[s, "gtn"]) / (base.loc[s, "pgdp"] / 100)
        adds.loc[s, "trp"] -= SIZE * base.loc[s, "xgdp"] / taxable
    sim = model.solve(START, END, adds)
    b, x = base.loc[w], sim.loc[w]
    drff = x["rff"] - b["rff"]
    if monetary == "peg":
        assert drff.abs().max() < 1e-10, f"peg moved rff by {drff.abs().max():.3e}"
    dx = x["xgdp"] - b["xgdp"]
    if instrument == "purchases":
        dinst = x["egfe"] - b["egfe"]
    elif instrument == "transfers":
        dinst = x["gtr"] - b["gtr"]
    else:
        dinst = pd.Series(0.0, index=dx.index)
        taxable = (b["ypn"] - b["gtn"]) / (b["pgdp"] / 100)
        dinst.loc[s] = (b.loc[s, "trp"] - x.loc[s, "trp"]) * taxable.loc[s]
    return {
        "instrument": instrument,
        "monetary": monetary,
        "fiscal": fiscal,
        "multiplier": {n: year_mean(dx, n) / year_mean(dinst, n) for n in (1, 2)},
        "xgdp_pct_year_mean": {n: year_mean(100 * (x["xgdp"] / b["xgdp"] - 1), n) for n in (1, 2)},
        "drff_year1_pp": year_mean(drff, 1),
        "dtrp_year1_pp": 100 * year_mean(x["trp"] - b["trp"], 1),
        "dtrp_year2_pp": 100 * year_mean(x["trp"] - b["trp"], 2),
    }


def render(rows: list[dict]) -> str:
    out = [
        "# Fiscal multipliers by closure",
        "",
        "Generated by `scripts/benchmark_multipliers.py`; do not edit by hand. "
        "8-quarter shocks (2026Q1-2027Q4) worth 1% of baseline real GDP, VAR "
        "expectations, LONGBASE April 2026. Multiplier = mean delta xgdp over the "
        "calendar year / mean delta instrument over the same year. See "
        "docs/benchmarks.md for the published comparators.",
        "",
        "| instrument | monetary | fiscal | year 1 | year 2 | xgdp yr 1 (%) | rff yr 1 (pp) | trp yr 1 (pp) | trp yr 2 (pp) |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        m = r["multiplier"]
        out.append(
            f"| {r['instrument']} | {r['monetary']} | {r['fiscal']} | {m[1]:.3f} | {m[2]:.3f} "
            f"| {r['xgdp_pct_year_mean'][1]:+.3f} | {r['drff_year1_pp']:+.3f} "
            f"| {r['dtrp_year1_pp']:+.3f} | {r['dtrp_year2_pp']:+.3f} |"
        )
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=REPO / "results")
    args = p.parse_args(argv)
    longbase = load_data(str(LONGBASE))
    rows = [run(longbase, i, m, f) for i in INSTRUMENTS for m in MONETARY for f in FISCAL]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "benchmark_multipliers.json").write_text(json.dumps(rows, indent=2) + "\n")
    md = render(rows)
    (args.out / "benchmark_multipliers.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

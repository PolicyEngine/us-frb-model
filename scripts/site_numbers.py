"""Reproduce the 100bp-shock numbers the PolicyEngine Macro site quotes.

No solve: everything comes from committed data. The 100bp monetary shock
reference path (tests/data/vendor_shock_2026q1_2030q4.csv, the Fed's
pyfrbus on the Board's demo shock; this implementation matches it to
6.0e-9, see VALIDATION.md) is compared with the LONGBASE baseline it was
solved from (vendor/data_only_package/LONGBASE.TXT).

Quantities (deviation from LONGBASE):

    rff_impact       funds rate, 2026Q1, pp
    xgdp_trough      real GDP, % of baseline, trough and quarter
    xgap2_trough     output gap (xgap2), pp, trough and quarter
    lur_peak         unemployment rate, pp, peak and quarter
    picxfe_trough    core PCE inflation, annualized q/q (log), pp
    core_pce_4q      four-quarter core PCE inflation from pcxfe, pp -- the
                     concept the Fed's published charts use
    wage_bill_2027   2027 annual-mean wage bill, %: pl% + lhp% (hourly
                     compensation plus private hours), the definition the
                     pe-macro frbus_shock_incidence adapter uses
                     (policyengine_macro core.py); the exact product
                     pl*lhp is reported alongside

Usage:
    uv run python scripts/site_numbers.py [--out DIR]
writes results/site_numbers.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from frbus import load_data  # noqa: E402

LONGBASE = REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"
SHOCK = REPO / "tests" / "data" / "vendor_shock_2026q1_2030q4.csv"


def compute(longbase: pd.DataFrame, shock: pd.DataFrame) -> dict:
    idx = shock.index
    base = longbase.loc[idx]

    def pct(var):
        return 100 * (shock[var] / base[var] - 1)

    def extreme(series, how):
        q = series.idxmin() if how == "min" else series.idxmax()
        return {"value": round(float(series[q]), 4), "quarter": str(q)}

    level = longbase["pcxfe"].copy()
    level.loc[idx] = shock["pcxfe"]
    core4 = (
        100 * (level / level.shift(4) - 1)
        - 100 * (longbase["pcxfe"] / longbase["pcxfe"].shift(4) - 1)
    ).loc[idx]

    y2027 = [q for q in idx if q.year == 2027]
    pl, lhp = pct("pl"), pct("lhp")
    exact = 100 * ((shock["pl"] * shock["lhp"]) / (base["pl"] * base["lhp"]) - 1)
    return {
        "source": {
            "shock": str(SHOCK.relative_to(REPO)),
            "baseline": str(LONGBASE.relative_to(REPO)),
            "experiment": "+1pp one-quarter add-factor to rffintay (2026Q1), "
            "inertial Taylor rule, VAR expectations, dfpdbt=0 dfpsrp=1",
        },
        "rff_impact": round(float(shock["rff"].iloc[0] - base["rff"].iloc[0]), 4),
        "xgdp_trough_pct": extreme(pct("xgdp"), "min"),
        "xgap2_trough": extreme(shock["xgap2"] - base["xgap2"], "min"),
        "lur_peak": extreme(shock["lur"] - base["lur"], "max"),
        "picxfe_trough": extreme(shock["picxfe"] - base["picxfe"], "min"),
        "core_pce_4q_trough": extreme(core4, "min"),
        "wage_bill_2027_pct": {
            "pl_pct": round(float(pl.loc[y2027].mean()), 4),
            "lhp_pct": round(float(lhp.loc[y2027].mean()), 4),
            "pl_plus_lhp": round(float(pl.loc[y2027].mean() + lhp.loc[y2027].mean()), 4),
            "exact_product": round(float(exact.loc[y2027].mean()), 4),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO / "results")
    args = parser.parse_args(argv)
    report = compute(load_data(str(LONGBASE)), load_data(str(SHOCK)))
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "site_numbers.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

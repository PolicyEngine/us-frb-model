"""Export the headline shock responses for the PolicyEngine Macro site.

One file, results/site_responses.json (+ .md), with quarter-by-quarter
deviations from baseline for the four experiments the site describes, and a
benchmark scorecard that puts each headline next to the published number or
band it is compared with. The site (and its drift canaries) can read GDP,
unemployment, inflation and the funds rate from here instead of re-deriving
them.

Experiments (VAR expectations, demo fiscal configuration, 2026Q1-2030Q4):

    monetary    +100bp one-quarter add-factor to rffintay (2026Q1), inertial
                Taylor rule. No solve: the committed pyfrbus reference path
                (tests/data/vendor_shock_2026q1_2030q4.csv) against LONGBASE,
                exactly as scripts/site_numbers.py.
    purchases   +1% of baseline real GDP in egfe for 8 quarters
    transfers   +1% of baseline real GDP in gtr for 8 quarters
    taxes       personal tax rate cut worth 1% of GDP ex ante, 8 quarters
                (the three fiscal runs are scripts/benchmark_multipliers.py's
                inertial-Taylor, surplus-rule runs, with paths kept)

Variables (deviation from baseline): rff (pp), xgdp_pct (real GDP, % of
baseline), lur (unemployment rate, pp), xgap2 (output gap, pp), picxfe (core
PCE inflation, annualized q/q, pp), core_pce_4q (four-quarter core PCE
inflation from the pcxfe level, pp).

The October 2026 LONGBASE has history through 2026Q2, so these shocks start
two quarters before the data edge (VALIDATION.md, "Data vintage and the
window").

Usage:
    uv run python scripts/site_responses.py [--out DIR]
writes results/site_responses.json and results/site_responses.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import benchmark_multipliers as bm  # noqa: E402

from frbus import load_data  # noqa: E402

LONGBASE = REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"
SHOCK = REPO / "tests" / "data" / "vendor_shock_2026q1_2030q4.csv"
VARIABLES = ("rff", "xgdp_pct", "lur", "xgap2", "picxfe", "core_pce_4q")
DECIMALS = 6

# Laforte (2018), FEDS Notes, doi:10.17016/2380-7172.2306, Fig. 2, New
# Version, 100bp, VAR expectations (also pinned in
# tests/test_inflation_transmission.py).
LAFORTE_2018 = {"xgap2": -0.4861, "picxfe": -0.0345, "lur": 0.2189}

# Published bands the repo gates on (tests/test_multipliers.py,
# tests/test_benchmarks.py; sources and conversions in docs/benchmarks.md).
BANDS = {
    "purchases_y1": (0.7, 1.0, "Coenen et al. (2012); Whalen & Reichling (CBO WP 2015-02)"),
    "purchases_y1_cbo": (0.45, 1.82, "CBO typical-Fed path, converted (docs/benchmarks.md s.2)"),
    "purchases_peg_y2": (0.8, 1.2, "Coenen et al. (2012), two-year accommodation"),
    "taxes_y1": (
        0.15,
        0.45,
        "regression band; CBO 2015 Table 3 rows 0.3-1.5 and 0.1-0.6 are Fed-not-tightening "
        "(docs/benchmarks.md)",
    ),
    "taxes_y2": (0.15, 0.45, "regression band, as above"),
}


def _core4(level: pd.Series, base_level: pd.Series, idx: pd.PeriodIndex) -> pd.Series:
    """Four-quarter core PCE inflation deviation, from pcxfe levels (pp)."""
    return (100 * (level / level.shift(4) - 1) - 100 * (base_level / base_level.shift(4) - 1)).loc[
        idx
    ]


def monetary_paths(longbase: pd.DataFrame, shock: pd.DataFrame) -> dict[str, pd.Series]:
    idx = shock.index
    base = longbase.loc[idx]
    level = longbase["pcxfe"].copy()
    level.loc[idx] = shock["pcxfe"]
    return {
        "rff": shock["rff"] - base["rff"],
        "xgdp_pct": 100 * (shock["xgdp"] / base["xgdp"] - 1),
        "lur": shock["lur"] - base["lur"],
        "xgap2": shock["xgap2"] - base["xgap2"],
        "picxfe": shock["picxfe"] - base["picxfe"],
        "core_pce_4q": _core4(level, longbase["pcxfe"], idx),
    }


def fiscal_paths(longbase: pd.DataFrame, run: dict) -> dict[str, pd.Series]:
    p = dict(run["paths"])
    shocked, base = p.pop("pcxfe_level")
    idx = shocked.index
    level, base_level = longbase["pcxfe"].copy(), longbase["pcxfe"].copy()
    level.loc[idx], base_level.loc[idx] = shocked, base
    p["core_pce_4q"] = _core4(level, base_level, idx)
    return {k: p[k] for k in VARIABLES}


def _extreme(s: pd.Series, how: str) -> dict:
    q = s.idxmin() if how == "min" else s.idxmax()
    return {"value": round(float(s[q]), 4), "quarter": str(q)}


def _year(s: pd.Series, n: int) -> float:
    return round(float(s.iloc[4 * (n - 1) : 4 * n].mean()), 4)


def summarise(paths: dict[str, pd.Series], sign: int) -> dict:
    """Peak response in the direction of the shock (sign=+1 expansionary)."""
    gdp_how, lur_how = ("max", "min") if sign > 0 else ("min", "max")
    return {
        "rff_impact": round(float(paths["rff"].iloc[0]), 4),
        "rff_peak_abs": _extreme(paths["rff"].abs(), "max"),
        "xgdp_pct_peak": _extreme(paths["xgdp_pct"], gdp_how),
        "xgap2_peak": _extreme(paths["xgap2"], gdp_how),
        "lur_peak": _extreme(paths["lur"], lur_how),
        "picxfe_peak": _extreme(paths["picxfe"], "max" if sign > 0 else "min"),
        "core_pce_4q_peak": _extreme(paths["core_pce_4q"], "max" if sign > 0 else "min"),
        "xgdp_pct_year": {n: _year(paths["xgdp_pct"], n) for n in (1, 2, 3)},
        "lur_year": {n: _year(paths["lur"], n) for n in (1, 2, 3)},
    }


def _row(name, ours, low, high, source, note=""):
    return {
        "check": name,
        "ours": round(float(ours), 4),
        "band": [low, high],
        "inside": bool(low <= ours <= high),
        "source": source,
        "note": note,
    }


def scorecard(experiments: dict, peg: dict) -> list[dict]:
    m = experiments["monetary"]["summary"]
    rows = []
    for var, key in (("xgap2", "xgap2_peak"), ("picxfe", "picxfe_peak")):
        pub = LAFORTE_2018[var]
        lo, hi = sorted((pub * 0.9, pub * 1.1))
        rows.append(
            _row(
                f"100bp: {var} trough",
                m[key]["value"],
                round(lo, 4),
                round(hi, 4),
                f"Laforte (2018) Fig. 2: {pub} (band +-10%)",
            )
        )
    # The unemployment peak depends on the start date (1.04x Laforte on
    # Laforte's own 2020Q1 design, 1.26x from 2026Q1, up to 1.38x from 2035Q1;
    # VALIDATION.md). It is compared with Laforte only on Laforte's design, so
    # this 2026Q1 row carries the start-date sanity range, not a published band.
    pub = LAFORTE_2018["lur"]
    rows.append(
        _row(
            "100bp: lur peak (start-date sanity range, not a published band)",
            m["lur_peak"]["value"],
            round(pub * 0.90, 4),
            round(pub * 1.45, 4),
            f"0.90-1.45x Laforte (2018) {pub}",
            "Laforte's own 2020Q1 design gives 1.04x: VALIDATION.md, Laforte by start date",
        )
    )
    mult = {k: experiments[k]["multiplier"] for k in ("purchases", "transfers", "taxes")}
    rows.append(_row("purchases multiplier, yr 1", mult["purchases"][1], *BANDS["purchases_y1"]))
    rows.append(
        _row("purchases multiplier, yr 1 (CBO)", mult["purchases"][1], *BANDS["purchases_y1_cbo"])
    )
    rows.append(
        _row("purchases multiplier, yr 2, peg", peg["multiplier"][2], *BANDS["purchases_peg_y2"])
    )
    rows.append(_row("tax-cut multiplier, yr 1", mult["taxes"][1], *BANDS["taxes_y1"]))
    rows.append(_row("tax-cut multiplier, yr 2", mult["taxes"][2], *BANDS["taxes_y2"]))
    rows.append(
        _row(
            "transfers multiplier, yr 1 (sanity bound 0.15 < x < purchases, not a published band)",
            mult["transfers"][1],
            0.15,
            round(mult["purchases"][1], 4),
            "transfers must raise GDP by less than purchases",
            "the model is BELOW every matched published benchmark, incl. CBO 0.4-2.1: "
            "docs/benchmarks.md, issue #13",
        )
    )
    return rows


def compute(longbase: pd.DataFrame, shock: pd.DataFrame) -> dict:
    experiments: dict = {}
    mp = monetary_paths(longbase, shock)
    experiments["monetary"] = {
        "description": "+100bp one-quarter add-factor to rffintay (2026Q1), inertial "
        "Taylor rule, VAR expectations, dfpdbt=0 dfpsrp=1; pyfrbus reference path "
        "(tests/data/vendor_shock_2026q1_2030q4.csv) against LONGBASE",
        "summary": summarise(mp, -1),
        "paths": mp,
    }
    labels = {
        "purchases": "+1% of baseline real GDP in egfe",
        "transfers": "+1% of baseline real GDP in gtr",
        "taxes": "personal tax rate cut worth 1% of baseline real GDP ex ante",
    }
    for inst, label in labels.items():
        r = bm.run(longbase, inst, "taylor", "srp", paths=True)
        fp = fiscal_paths(longbase, r)
        experiments[inst] = {
            "description": f"{label} for 8 quarters (2026Q1-2027Q4), inertial Taylor "
            "rule, demo surplus rule, VAR expectations (scripts/benchmark_multipliers.py)",
            "multiplier": {n: round(float(v), 4) for n, v in r["multiplier"].items()},
            "summary": summarise(fp, +1),
            "paths": fp,
        }
    peg = bm.run(longbase, "purchases", "peg", "srp")
    quarters = [str(q) for q in mp["rff"].index]
    for e in experiments.values():
        e["paths"] = {
            v: [round(float(x), DECIMALS) for x in e["paths"][v].to_numpy()] for v in VARIABLES
        }
    return {
        "description": "Quarterly deviations from baseline for the site's FRB/US "
        "experiments, October 2026 LONGBASE (history through 2026Q2, so 2026Q1 "
        "shocks start two quarters before the data edge). Units: rff, lur, xgap2, "
        "picxfe, core_pce_4q in pp; xgdp_pct in % of baseline.",
        "baseline": str(LONGBASE.relative_to(REPO)),
        "quarters": quarters,
        "variables": list(VARIABLES),
        "experiments": experiments,
        "scorecard": scorecard(experiments, peg),
    }


def render(r: dict) -> str:
    ex = r["experiments"]
    out = [
        "# FRB/US shock responses for the site",
        "",
        "Generated by `scripts/site_responses.py`; do not edit by hand. " + r["description"],
        "",
        "## Benchmark scorecard",
        "",
        "| check | ours | band | inside | source |",
        "|---|---|---|---|---|",
    ]
    for row in r["scorecard"]:
        lo, hi = row["band"]
        note = f" ({row['note']})" if row["note"] else ""
        out.append(
            f"| {row['check']} | {row['ours']:+.4f} | {lo:+.4f} to {hi:+.4f} | "
            f"{'yes' if row['inside'] else '**no**'} | {row['source']}{note} |"
        )
    out += [
        "",
        "## Real GDP and unemployment, annual means",
        "",
        "| experiment | GDP yr 1 (%) | GDP yr 2 (%) | GDP yr 3 (%) | unemployment yr 1 (pp) "
        "| yr 2 | yr 3 | peak GDP (%) | peak unemployment (pp) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, e in ex.items():
        s = e["summary"]
        g, u = s["xgdp_pct_year"], s["lur_year"]
        out.append(
            f"| {name} | {g[1]:+.3f} | {g[2]:+.3f} | {g[3]:+.3f} | {u[1]:+.3f} | {u[2]:+.3f} "
            f"| {u[3]:+.3f} | {s['xgdp_pct_peak']['value']:+.3f} ({s['xgdp_pct_peak']['quarter']}) "
            f"| {s['lur_peak']['value']:+.3f} ({s['lur_peak']['quarter']}) |"
        )
    for name, e in ex.items():
        out += [
            "",
            f"## {name}: quarterly path",
            "",
            e["description"] + ".",
            "",
            "| quarter | " + " | ".join(r["variables"]) + " |",
            "|---" * (len(r["variables"]) + 1) + "|",
        ]
        for i, q in enumerate(r["quarters"]):
            vals = " | ".join(f"{e['paths'][v][i]:+.4f}" for v in r["variables"])
            out.append(f"| {q} | {vals} |")
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=REPO / "results")
    args = p.parse_args(argv)
    shock = load_data(str(SHOCK))
    r = compute(load_data(str(LONGBASE)), shock)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "site_responses.json").write_text(json.dumps(r, indent=2) + "\n")
    md = render(r)
    (args.out / "site_responses.md").write_text(md)
    print(md[: md.index("## monetary: quarterly path")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

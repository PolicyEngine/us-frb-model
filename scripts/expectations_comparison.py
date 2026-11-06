"""VAR versus model-consistent expectations (MCE) on the headline experiments.

Runs, under ``mce=None`` (VAR, the default), ``"mcap"`` (financial-market
expectations model-consistent) and ``"mcap+wp"`` (financial plus wage-price):

1. The 100bp monetary ping: +1 on ``rffintay_aerr`` in 2026Q1, demo fiscal
   configuration (``dfpsrp=1``, ``dfpdbt=0``), inertial Taylor rule.
2. The purchases multiplier: ``egfe`` exogenized and raised by 1% of baseline
   real GDP over 2026Q1-2027Q4, Taylor rule and ``dfpsrp=1`` (the gated
   closure of scripts/benchmark_multipliers.py, row purchases/taylor/srp).
3. The Board's published MCE ping, Laforte (2018) FEDS Note, Figure 11
   ("Model-consistent expectations"; footnote 3: MCE for "the variables of
   the financial and wage-price sectors", i.e. mcap+wp), run from 2040Q1 with
   the programs/pings.prg settings (rffmin=-9999, dmptrsh=0, drstar=0), the
   same set-up as the VAR ping gate in scripts/inflation_transmission.py.

MCE solves stack the whole window, and leads past the window read the
baseline (the terminal condition). Experiments 1 and 2 therefore use a
40-year window, 2026Q1-2065Q4, so the terminal condition does not bind on the
years reported; the 20-quarter window used by the pyfrbus cross-validation
gate is shown alongside for the ping. Under VAR the window length does not
change the reported quarters (nothing looks forward).

    uv run python scripts/expectations_comparison.py [--out DIR]

writes results/expectations_comparison.json and .md. Roughly 20 stacked
solves of up to 160 quarters; take the heavy-job lock or run it in CI.
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
LAFORTE_JSON = REPO / "docs" / "data" / "laforte2018_fig11_mce_ping.json"

MODES = (None, "mcap", "mcap+wp")
START = pd.Period("2026Q1")
END_LONG = pd.Period("2065Q4")
END_SHORT = pd.Period("2030Q4")
SHOCK_END = pd.Period("2027Q4")
SIZE = 0.01
PING_START = pd.Period("2040Q1")
PING_END = PING_START + 159
SERIES = ("rff", "rg10", "xgap2", "lur", "picxfe")


def label(mode: str | None) -> str:
    return mode or "var"


def year_mean(series: pd.Series, year: int) -> float:
    return float(series.iloc[4 * (year - 1) : 4 * year].mean())


def _ext(s: pd.Series, fn: str) -> list:
    q = s.idxmin() if fn == "min" else s.idxmax()
    return [float(s.loc[q]), str(q), int((q - s.index[0]).n) + 1]


def monetary(longbase, mode, start, end, fed_pings=False) -> dict:
    model = Frbus(str(MODEL_XML), mce=mode)
    data = longbase.copy()
    w = slice(start, end)
    data.loc[w, "dfpdbt"] = 0
    data.loc[w, "dfpsrp"] = 1
    if fed_pings:
        data.loc[:, "rffmin"] = -9999
        data.loc[:, "dmptrsh"] = 0
        data.loc[w, "drstar"] = 0
    base = model.init_trac(start, end, data)
    adds = base.copy()
    adds.loc[start, "rffintay_aerr"] += 1
    sim = model.solve(start, end, adds)
    dev = {c: sim.loc[w, c] - base.loc[w, c] for c in SERIES}
    dev["xgdp_pct"] = 100 * (sim.loc[w, "xgdp"] / base.loc[w, "xgdp"] - 1)
    return {
        "mode": label(mode),
        "window": [str(start), str(end)],
        "path_q1_q12": {k: [round(float(v), 6) for v in s.iloc[:12]] for k, s in dev.items()},
        "xgap2_trough": _ext(dev["xgap2"], "min"),
        "xgdp_pct_trough": _ext(dev["xgdp_pct"], "min"),
        "lur_peak": _ext(dev["lur"], "max"),
        "picxfe_trough": _ext(dev["picxfe"], "min"),
        "rg10_impact": float(dev["rg10"].iloc[0]),
    }


def purchases(longbase, mode) -> dict:
    model = Frbus(str(MODEL_XML), mce=mode)
    model.exogenize(["egfe"])
    data = longbase.copy()
    w = slice(START, END_LONG)
    data.loc[w, "dfpdbt"] = 0
    data.loc[w, "dfpex"] = 0
    data.loc[w, "dfpsrp"] = 1
    base = model.init_trac(START, END_LONG, data)
    adds = base.copy()
    s = slice(START, SHOCK_END)
    adds.loc[s, "egfe"] += SIZE * base.loc[s, "xgdp"]
    sim = model.solve(START, END_LONG, adds)
    b, x = base.loc[w], sim.loc[w]
    dx, dg = x["xgdp"] - b["xgdp"], x["egfe"] - b["egfe"]
    return {
        "mode": label(mode),
        "multiplier": {n: year_mean(dx, n) / year_mean(dg, n) for n in (1, 2)},
        "impact_multiplier_q1": float(dx.iloc[0] / dg.iloc[0]),
        "drff_year1_pp": year_mean(x["rff"] - b["rff"], 1),
        "drg10_year1_pp": year_mean(x["rg10"] - b["rg10"], 1),
    }


CLOSURE_END = pd.Period("2030Q4")


def purchases_closure(longbase, mode, monetary: str, fiscal: str) -> dict:
    """Purchases multiplier on the matched closures of docs/benchmarks.md section 4.

    The closures of scripts/benchmark_multipliers.py, applied over 2026Q1-2030Q4
    only (peg: funds rate on its baseline path, ``dmpex=1``; exog: trend tax
    rates exogenous, ``dfpex=1, dfpsrp=0``). The window still runs to 2065Q4,
    and from 2031Q1 LONGBASE's own settings (inertial Taylor rule, fiscal rule)
    apply, so under MCE agents know the peg ends after five years. Under VAR the
    2026-27 numbers equal the benchmark_multipliers rows (a check).
    """
    model = Frbus(str(MODEL_XML), mce=mode)
    model.exogenize(["egfe"])
    data = longbase.copy()
    c = slice(START, CLOSURE_END)
    data.loc[c, "dfpdbt"] = 0
    if fiscal == "srp":
        data.loc[c, "dfpex"] = 0
        data.loc[c, "dfpsrp"] = 1
    else:
        data.loc[c, "dfpex"] = 1
        data.loc[c, "dfpsrp"] = 0
    if monetary == "peg":
        data.loc[c, "dmpintay"] = 0
        data.loc[c, "dmpex"] = 1
        data.loc[c, "rfffix"] = data.loc[c, "rff"]
    base = model.init_trac(START, END_LONG, data)
    adds = base.copy()
    s = slice(START, SHOCK_END)
    adds.loc[s, "egfe"] += SIZE * base.loc[s, "xgdp"]
    sim = model.solve(START, END_LONG, adds)
    w = slice(START, END_LONG)
    b, x = base.loc[w], sim.loc[w]
    dx, dg = x["xgdp"] - b["xgdp"], x["egfe"] - b["egfe"]
    return {
        "mode": label(mode),
        "monetary": monetary,
        "fiscal": fiscal,
        "multiplier": {n: year_mean(dx, n) / year_mean(dg, n) for n in (1, 2)},
        "drff_year1_pp": year_mean(x["rff"] - b["rff"], 1),
        "drg10_year1_pp": year_mean(x["rg10"] - b["rg10"], 1),
    }


MATCHED = (("taylor", "exog"), ("peg", "srp"), ("peg", "exog"))


def compute_matched(longbase) -> list[dict]:
    return [
        purchases_closure(longbase, m, mon, fis)
        for mon, fis in MATCHED
        for m in (None, "mcap", "mcap+wp")
    ]


def render_matched(rows: list[dict]) -> str:
    out = [
        "# Purchases multiplier on the matched closures, VAR versus MCE",
        "",
        "Generated by `scripts/expectations_comparison.py --matched`; do not edit by hand. "
        "+1% of baseline real GDP in egfe over 2026Q1-2027Q4; closures over "
        "2026Q1-2030Q4 (docs/benchmarks.md section 4), LONGBASE settings after; "
        "window 2026Q1-2065Q4.",
        "",
        "| monetary | fiscal | expectations | year 1 | year 2 | rff yr 1 (pp) | 10y yr 1 (pp) |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in rows:
        m = x["multiplier"]
        out.append(
            f"| {x['monetary']} | {x['fiscal']} | {x['mode']} | {m[1]:.3f} | {m[2]:.3f} "
            f"| {x['drff_year1_pp']:+.3f} | {x['drg10_year1_pp']:+.3f} |"
        )
    out.append("")
    return "\n".join(out)


def compute(longbase) -> dict:
    laforte = json.loads(LAFORTE_JSON.read_text())
    return {
        "monetary": [monetary(longbase, m, START, END_LONG) for m in MODES],
        "monetary_20q_window": [monetary(longbase, m, START, END_SHORT) for m in MODES[1:]],
        "purchases": [purchases(longbase, m) for m in MODES],
        "laforte_fig11": {
            "published_new_version": laforte["summary"],
            "ours": [
                monetary(longbase, m, PING_START, PING_END, fed_pings=True)
                for m in (None, "mcap+wp")
            ],
        },
    }


def _row(r: dict) -> str:
    return (
        f"| {r['mode']} | {r['window'][0]}-{r['window'][1]} | {r['rg10_impact']:+.3f} "
        f"| {r['xgap2_trough'][0]:+.3f} (q{r['xgap2_trough'][2]}) "
        f"| {r['xgdp_pct_trough'][0]:+.3f} (q{r['xgdp_pct_trough'][2]}) "
        f"| {r['lur_peak'][0]:+.3f} (q{r['lur_peak'][2]}) "
        f"| {r['picxfe_trough'][0]:+.4f} (q{r['picxfe_trough'][2]}) |"
    )


def render(r: dict) -> str:
    head = (
        "| expectations | window | 10y impact (pp) | output gap trough (pp) "
        "| real GDP trough (%) | unemployment peak (pp) | core PCE trough (pp) |"
    )
    out = [
        "# VAR versus model-consistent expectations",
        "",
        "Generated by `scripts/expectations_comparison.py`; do not edit by hand. "
        "LONGBASE April 2026. `mcap`: financial-market expectations model-consistent; "
        "`mcap+wp`: financial and wage-price. MCE solves are stacked over the whole "
        "window with baseline terminal values after it; both MCE modes match the "
        "Board's pyfrbus on the 20-quarter window (tests/test_mce.py).",
        "",
        "## 100bp funds-rate shock (rffintay_aerr +1 in 2026Q1, demo fiscal config)",
        "",
        head,
        "|---|---|---|---|---|---|---|",
    ]
    out += [_row(x) for x in r["monetary"]]
    out += [_row(x) for x in r["monetary_20q_window"]]
    out += [
        "",
        "The 20-quarter rows show how much a short window's terminal condition "
        "(expectations snap back to baseline after 2030Q4) damps the MCE response.",
        "",
        "## Purchases multiplier (+1% of GDP in egfe, 2026Q1-2027Q4, Taylor, dfpsrp=1)",
        "",
        "| expectations | year 1 | year 2 | impact (q1) | rff yr 1 (pp) | 10y yr 1 (pp) |",
        "|---|---|---|---|---|---|",
    ]
    for x in r["purchases"]:
        m = x["multiplier"]
        out.append(
            f"| {x['mode']} | {m[1]:.3f} | {m[2]:.3f} | {x['impact_multiplier_q1']:.3f} "
            f"| {x['drff_year1_pp']:+.3f} | {x['drg10_year1_pp']:+.3f} |"
        )
    lf = r["laforte_fig11"]
    p = lf["published_new_version"]
    out += [
        "",
        "## Against the Board's published MCE ping (Laforte 2018, Figure 11)",
        "",
        "Figure 11 is a 100bp funds-rate shock under model-consistent expectations "
        "for the financial and wage-price sectors (footnote 3), 2018 model vintage. "
        "Ours: same shock from 2040Q1, pings.prg settings, 160-quarter window.",
        "",
        "| | 10y impact | output gap trough | unemployment peak | core PCE trough "
        "| rff q2 | rff q4 |",
        "|---|---|---|---|---|---|---|",
        f"| Laforte 2018, new version | {p['r10_impact']:+.4f} | {p['gap_trough'][0]:+.4f} "
        f"(q{p['gap_trough'][1]}) | {p['lur_peak'][0]:+.4f} (q{p['lur_peak'][1]}) "
        f"| {p['core_trough'][0]:+.4f} (q{p['core_trough'][1]}) | {p['rff_q'][1]:.4f} "
        f"| {p['rff_q'][3]:.4f} |",
    ]
    for x in lf["ours"]:
        rff = x["path_q1_q12"]["rff"]
        out.append(
            f"| ours, {x['mode']} | {x['rg10_impact']:+.4f} | {x['xgap2_trough'][0]:+.4f} "
            f"(q{x['xgap2_trough'][2]}) | {x['lur_peak'][0]:+.4f} (q{x['lur_peak'][2]}) "
            f"| {x['picxfe_trough'][0]:+.4f} (q{x['picxfe_trough'][2]}) | {rff[1]:.4f} "
            f"| {rff[3]:.4f} |"
        )
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=REPO / "results")
    p.add_argument(
        "--matched",
        action="store_true",
        help="only the purchases multiplier on the matched closures; writes "
        "expectations_matched_closures.{json,md}",
    )
    args = p.parse_args(argv)
    if args.matched:
        rows = compute_matched(load_data(str(LONGBASE)))
        args.out.mkdir(parents=True, exist_ok=True)
        stem = args.out / "expectations_matched_closures"
        stem.with_suffix(".json").write_text(json.dumps(rows, indent=2) + "\n")
        md = render_matched(rows)
        stem.with_suffix(".md").write_text(md)
        print(md)
        return 0
    r = compute(load_data(str(LONGBASE)))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "expectations_comparison.json").write_text(json.dumps(r, indent=2) + "\n")
    md = render(r)
    (args.out / "expectations_comparison.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

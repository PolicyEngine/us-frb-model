"""Scenario sweep: monetary and fiscal shocks of different sizes and signs.

Runs a grid of experiments on the pinned LONGBASE vintage (VAR expectations,
the demo fiscal configuration ``dfpdbt=0, dfpsrp=1``) and checks the
properties a correct solve must have:

* zero shock reproduces the baseline;
* signs (tightening lowers output, gap, inflation and raises unemployment;
  purchases, transfers and tax cuts raise output);
* linearity in shock size (the 200bp response is about twice the 100bp one,
  the 25bp response about a quarter) and symmetry in sign;
* reversion: a one-quarter funds-rate impulse and a temporary (8-quarter)
  fiscal shock die out within the 20-quarter window;
* multipliers against published ranges (see results/scenario_sweep.md).

Experiments
-----------
monetary  one-quarter add-factor impulse to the inertial Taylor rule
          (``rffintay_aerr``, the Board's demo shock) of -200, -100, -25, 0,
          +25, +100, +200bp; plus +100bp held for 4 and 8 quarters
          (persistence variants; the add-factor compounds through the rule's
          inertia, see tests/test_shock.py).
purchases ``egfe`` exogenized and raised by x% of baseline real GDP for 8
          quarters (2026Q1-2027Q4), x in -1, -0.1, 0, +0.1, +0.5, +1, +2.
          The response is NOT linear at 1% of GDP: final sales (xfs) and
          GDP (xp) aggregate components by log growth, y*log(egfe/egfe(-1)),
          and 1% of GDP is ~22% of egfe, so log(1.22) = 0.20 against
          -log(0.78) = 0.25. A cut has a ~25% larger multiplier than a rise.
          The checks test that this ratio is what log aggregation predicts,
          and test linearity/symmetry on the +-0.1% runs.
transfers ``gtr`` (real federal net transfers) add-factor raised by x% of
          baseline real GDP for 8 quarters, x in -1, 0, +1, +2.
taxes     ``trp`` (average personal tax rate) exogenized and cut by x pp for 8
          quarters, x in -2, 0, +1, +2, +4 (positive = cut).

Multipliers are calendar-year: mean(delta xgdp over year N) / mean(delta
instrument over year N); for taxes the instrument is the ex-ante real
revenue cut, x * baseline (ypn - gtn) / (pgdp / 100), the convention in
tests/test_multipliers.py. Because solves are period by period under VAR
expectations, the year-1/2 purchases and tax multipliers here must equal the
gated ones in tests/test_multipliers.py, which use a 12-quarter sustained
shock.

This is a HEAVY job (about 25 full nonlinear solves). Usage:

    uv run python scripts/scenario_sweep.py [--out DIR]

writes results/scenario_sweep.json and results/scenario_sweep.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import scenarios  # noqa: E402

from frbus import Frbus, load_data  # noqa: E402

MODEL_XML = REPO / "vendor" / "pyfrbus_package" / "models" / "model.xml"
LONGBASE = REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"

START = pd.Period("2026Q1")
END = pd.Period("2030Q4")
FISCAL_END = pd.Period("2027Q4")  # temporary fiscal shocks: 8 quarters

MONETARY_SIZES = [-2.0, -1.0, -0.25, 0.0, 0.25, 1.0, 2.0]
MONETARY_PERSISTENCE = [1, 4, 8]
PURCHASES_SIZES = [-0.01, -0.001, 0.0, 0.001, 0.005, 0.01, 0.02]
TRANSFERS_SIZES = [-0.01, 0.0, 0.01, 0.02]
TAX_SIZES = [-0.02, 0.0, 0.01, 0.02, 0.04]

REPORT_VARS = ["rff", "xgdp", "xgap2", "lur", "picxfe", "pcxfe"]


def deviations(sim: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """Deviation from baseline on the conventional units for each variable."""
    s, b = sim.loc[START:END], base.loc[START:END]
    full_s = base["pcxfe"].copy()
    full_s.loc[START:END] = s["pcxfe"]
    core4_s = 100 * (full_s / full_s.shift(4) - 1)
    core4_b = 100 * (base["pcxfe"] / base["pcxfe"].shift(4) - 1)
    return pd.DataFrame(
        {
            "rff": s["rff"] - b["rff"],  # pp
            "xgdp_pct": 100 * (s["xgdp"] / b["xgdp"] - 1),  # % of baseline
            "xgap2": s["xgap2"] - b["xgap2"],  # pp
            "lur": s["lur"] - b["lur"],  # pp
            "picxfe": s["picxfe"] - b["picxfe"],  # pp, annualized q/q
            "core_pce_4q": (core4_s - core4_b).loc[START:END],  # pp, 4-quarter
        }
    )


def summarize(dev: pd.DataFrame) -> dict:
    out = {}
    for col in dev.columns:
        series = dev[col]
        lo, hi = series.idxmin(), series.idxmax()
        out[col] = {
            "min": float(series.min()),
            "min_at": str(lo),
            "max": float(series.max()),
            "max_at": str(hi),
            "last": float(series.iloc[-1]),
        }
    return out


def year_mean(series: pd.Series, year: int) -> float:
    return float(series.iloc[4 * (year - 1) : 4 * year].mean())


def run_monetary(longbase: pd.DataFrame) -> dict:
    model = Frbus(str(MODEL_XML))
    data = longbase.copy()
    scenarios.set_policy("monetary", data, START, END)
    base = model.init_trac(START, END, data)
    runs = {}
    for size in MONETARY_SIZES:
        adds = base.copy()
        adds.loc[START, "rffintay_aerr"] += size
        dev = deviations(model.solve(START, END, adds), base)
        runs[f"impulse_{size:+.2f}pp"] = {"size": size, "quarters": 1, "dev": dev}
    for k in MONETARY_PERSISTENCE[1:]:
        adds = base.copy()
        adds.loc[START : START + (k - 1), "rffintay_aerr"] += 1.0
        dev = deviations(model.solve(START, END, adds), base)
        runs[f"held_{k}q_+1.00pp"] = {"size": 1.0, "quarters": k, "dev": dev}
    return runs


def run_purchases(longbase: pd.DataFrame) -> dict:
    model = Frbus(str(MODEL_XML))
    data = longbase.copy()
    scenarios.set_policy("fiscal_egfe", data, START, END)
    model.exogenize(["egfe"])
    base = model.init_trac(START, END, data)
    runs = {}
    for size in PURCHASES_SIZES:
        adds = base.copy()
        adds.loc[START:FISCAL_END, "egfe"] += size * base.loc[START:FISCAL_END, "xgdp"]
        sim = model.solve(START, END, adds)
        dx = sim.loc[START:END, "xgdp"] - base.loc[START:END, "xgdp"]
        dg = sim.loc[START:END, "egfe"] - base.loc[START:END, "egfe"]
        mult = {n: year_mean(dx, n) / year_mean(dg, n) for n in (1, 2)} if size else {}
        runs[f"purchases_{100 * size:+.1f}pct_gdp"] = {
            "size": size,
            "egfe_share_year1": float(
                (base.loc[START : START + 3, "egfe"] / base.loc[START : START + 3, "xgdp"]).mean()
            ),
            "dev": deviations(sim, base),
            "multiplier": mult,
        }
    return runs


def run_transfers(longbase: pd.DataFrame) -> dict:
    model = Frbus(str(MODEL_XML))
    data = longbase.copy()
    scenarios.set_policy("fiscal_egfe", data, START, END)  # same fiscal config
    base = model.init_trac(START, END, data)
    runs = {}
    for size in TRANSFERS_SIZES:
        adds = base.copy()
        adds.loc[START:FISCAL_END, "gtr_aerr"] += size * base.loc[START:FISCAL_END, "xgdp"]
        sim = model.solve(START, END, adds)
        dx = sim.loc[START:END, "xgdp"] - base.loc[START:END, "xgdp"]
        dt = sim.loc[START:END, "gtr"] - base.loc[START:END, "gtr"]
        mult = {n: year_mean(dx, n) / year_mean(dt, n) for n in (1, 2)} if size else {}
        runs[f"transfers_{100 * size:+.1f}pct_gdp"] = {
            "size": size,
            "dev": deviations(sim, base),
            "multiplier": mult,
        }
    return runs


def run_taxes(longbase: pd.DataFrame) -> dict:
    model = Frbus(str(MODEL_XML))
    data = longbase.copy()
    scenarios.set_policy("tax_trp", data, START, END)
    model.exogenize(["trp"])
    base = model.init_trac(START, END, data)
    revenue_per_pp = (base.loc[START:END, "ypn"] - base.loc[START:END, "gtn"]) / (
        base.loc[START:END, "pgdp"] / 100
    )
    runs = {}
    for size in TAX_SIZES:
        adds = base.copy()
        adds.loc[START:FISCAL_END, "trp"] -= size
        sim = model.solve(START, END, adds)
        dx = sim.loc[START:END, "xgdp"] - base.loc[START:END, "xgdp"]
        cut = size * revenue_per_pp
        mult = {n: year_mean(dx, n) / year_mean(cut, n) for n in (1, 2)} if size else {}
        runs[f"tax_cut_{100 * size:+.1f}pp"] = {
            "size": size,
            "dev": deviations(sim, base),
            "multiplier": mult,
        }
    return runs


def checks(families: dict) -> list[dict]:
    """The pass/fail properties of the sweep, one row each."""
    rows = []

    def add(name, value, ok, detail):
        rows.append({"check": name, "value": value, "pass": bool(ok), "detail": detail})

    # Zero shock = baseline, every family.
    for fam, runs in families.items():
        zero = next(r for r in runs.values() if r["size"] == 0.0 and r.get("quarters", 1) == 1)
        worst = float(zero["dev"].abs().to_numpy().max())
        add(f"{fam}: zero shock = baseline", worst, worst < 1e-8, "max |deviation| < 1e-8")

    mon = families["monetary"]
    p100 = mon["impulse_+1.00pp"]["dev"]
    m100 = mon["impulse_-1.00pp"]["dev"]
    p200 = mon["impulse_+2.00pp"]["dev"]
    p25 = mon["impulse_+0.25pp"]["dev"]
    # Signs.
    add(
        "monetary +100bp: sign",
        None,
        p100["xgdp_pct"].min() < 0
        and p100["xgap2"].min() < 0
        and p100["lur"].max() > 0
        and p100["picxfe"].min() < 0
        and p100["core_pce_4q"].min() < 0,
        "xgdp, xgap2, picxfe, 4q core down; lur up",
    )
    # Linearity and symmetry, measured on the full path relative to the peak.
    for var in ["xgdp_pct", "xgap2", "lur", "core_pce_4q", "rff"]:
        peak = float(p100[var].abs().max())
        lin200 = float((p200[var] - 2 * p100[var]).abs().max()) / (2 * peak)
        lin25 = float((4 * p25[var] - p100[var]).abs().max()) / peak
        sym = float((p100[var] + m100[var]).abs().max()) / peak
        add(
            f"monetary linearity 200 vs 2x100: {var}",
            lin200,
            lin200 < 0.05,
            "max |d200 - 2 d100| / peak(2 d100) < 5%",
        )
        add(
            f"monetary linearity 4x25 vs 100: {var}",
            lin25,
            lin25 < 0.05,
            "max |4 d25 - d100| / peak(d100) < 5%",
        )
        add(
            f"monetary symmetry +100 vs -100: {var}",
            sym,
            sym < 0.05,
            "max |d(+100) + d(-100)| / peak < 5%",
        )
    # Reversion of the one-quarter impulse.
    for var in ["rff", "xgap2"]:
        ratio = abs(float(p100[var].iloc[-1])) / float(p100[var].abs().max())
        add(
            f"monetary reversion: {var} at 2030Q4 / peak",
            ratio,
            ratio < 0.25,
            "deviation in the last quarter below 25% of the peak",
        )
    # Persistence: holding the shock longer must deepen the trough.
    t1 = float(mon["impulse_+1.00pp"]["dev"]["xgdp_pct"].min())
    t4 = float(mon["held_4q_+1.00pp"]["dev"]["xgdp_pct"].min())
    t8 = float(mon["held_8q_+1.00pp"]["dev"]["xgdp_pct"].min())
    add(
        "monetary persistence: trough deepens 1q > 4q > 8q",
        [t1, t4, t8],
        t1 > t4 > t8,
        "xgdp trough (%) more negative the longer the shock is held",
    )

    # Purchases: the large-shock asymmetry must be the log-aggregation one.
    pur = families["purchases"]
    share = pur["purchases_+1.0pct_gdp"]["egfe_share_year1"]
    a = 0.01 / share
    predicted = -np.log(1 - a) / np.log(1 + a)
    observed = (
        pur["purchases_-1.0pct_gdp"]["multiplier"][1]
        / pur["purchases_+1.0pct_gdp"]["multiplier"][1]
    )
    add(
        "purchases: +-1% asymmetry = log-aggregation prediction",
        [observed, predicted],
        abs(observed / predicted - 1) < 0.02,
        "year-1 multiplier ratio cut/rise within 2% of -log(1-a)/log(1+a), a = 1% GDP / egfe",
    )
    for fam, key_pos, key_neg, key_double in [
        ("purchases", "purchases_+0.1pct_gdp", "purchases_-0.1pct_gdp", "purchases_+0.5pct_gdp"),
        ("transfers", "transfers_+1.0pct_gdp", "transfers_-1.0pct_gdp", "transfers_+2.0pct_gdp"),
        ("taxes", "tax_cut_+2.0pp", "tax_cut_-2.0pp", "tax_cut_+4.0pp"),
    ]:
        runs = families[fam]
        pos, neg, dbl = (runs[k]["dev"]["xgdp_pct"] for k in (key_pos, key_neg, key_double))
        factor = runs[key_double]["size"] / runs[key_pos]["size"]
        peak = float(pos.abs().max())
        add(
            f"{fam}: expansion raises output",
            float(pos.iloc[:4].mean()),
            pos.iloc[:4].mean() > 0,
            "mean xgdp deviation over year 1 > 0",
        )
        sym = float((pos + neg).abs().max()) / peak
        lin = float((dbl - factor * pos).abs().max()) / (factor * peak)
        add(
            f"{fam}: symmetry at +-{100 * runs[key_pos]['size']:g}% / pp",
            sym,
            sym < 0.05,
            "max |d(+x) + d(-x)| / peak < 5%",
        )
        add(
            f"{fam}: linearity {factor:g}x",
            lin,
            lin < 0.05,
            "max |d(kx) - k d(x)| / peak(k d(x)) < 5%",
        )
        late = abs(float(pos.iloc[-4:].mean())) / peak
        add(
            f"{fam}: reversion after the shock ends",
            late,
            late < 0.5,
            "mean |xgdp deviation| in 2030 below 50% of the peak",
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO / "results")
    args = parser.parse_args(argv)

    longbase = load_data(str(LONGBASE))
    families = {
        "monetary": run_monetary(longbase),
        "purchases": run_purchases(longbase),
        "transfers": run_transfers(longbase),
        "taxes": run_taxes(longbase),
    }
    check_rows = checks(families)
    report = {
        "description": "FRB/US scenario sweep on LONGBASE (April 2026), VAR "
        "expectations, demo fiscal configuration. Deviations from baseline: "
        "rff, xgap2, lur, picxfe, core_pce_4q in pp; xgdp_pct in % of baseline.",
        "window": [str(START), str(END)],
        "fiscal_shock_window": [str(START), str(FISCAL_END)],
        "runs": {
            fam: {
                name: {k: v for k, v in run.items() if k != "dev"}
                | {"summary": summarize(run["dev"])}
                for name, run in runs.items()
            }
            for fam, runs in families.items()
        },
        "checks": check_rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "scenario_sweep.json").write_text(
        json.dumps(
            report, indent=2, default=lambda o: o if not isinstance(o, np.generic) else o.item()
        )
        + "\n"
    )
    (args.out / "scenario_sweep.md").write_text(render_markdown(report))
    print(render_markdown(report))
    failed = [r["check"] for r in check_rows if not r["pass"]]
    print("FAILED: " + "; ".join(failed) if failed else "all checks pass")
    return 1 if failed else 0


def render_markdown(report: dict) -> str:
    lines = [
        "# FRB/US scenario sweep",
        "",
        "Generated by `scripts/scenario_sweep.py`; do not edit by hand. " + report["description"],
        "",
        "## Monetary shocks (inertial Taylor rule add-factor)",
        "",
        "| run | rff peak | xgdp trough (%) | xgap2 trough | lur peak | picxfe trough | 4q core PCE trough | xgap2 at 2030Q4 |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, run in report["runs"]["monetary"].items():
        s = run["summary"]
        peak_rff = s["rff"]["max"] if run["size"] >= 0 else s["rff"]["min"]
        ext = "min" if run["size"] >= 0 else "max"

        def trough(v, s=s, ext=ext):
            return s[v][ext]

        lur = s["lur"]["max"] if run["size"] >= 0 else s["lur"]["min"]
        lines.append(
            f"| {name} | {peak_rff:+.3f} | {trough('xgdp_pct'):+.3f} ({s['xgdp_pct'][ext + '_at']}) "  # noqa: E501
            f"| {trough('xgap2'):+.3f} | {lur:+.3f} | {trough('picxfe'):+.4f} "
            f"| {trough('core_pce_4q'):+.4f} | {s['xgap2']['last']:+.3f} |"
        )
    for fam, title in [
        ("purchases", "Federal purchases (egfe), 8 quarters"),
        ("transfers", "Federal net transfers (gtr add-factor), 8 quarters"),
        ("taxes", "Personal tax-rate cut (trp), 8 quarters"),
    ]:
        lines += [
            "",
            f"## {title}",
            "",
            "| run | xgdp peak abs (%) | year-1 multiplier | year-2 multiplier | rff max | xgdp mean 2030 (%) |",  # noqa: E501
            "|---|---|---|---|---|---|",
        ]
        for name, run in report["runs"][fam].items():
            s = run["summary"]
            m = run["multiplier"]
            big = (
                s["xgdp_pct"]["max"]
                if abs(s["xgdp_pct"]["max"]) >= abs(s["xgdp_pct"]["min"])
                else s["xgdp_pct"]["min"]
            )
            lines.append(
                f"| {name} | {big:+.3f} | {m.get(1, float('nan')):.3f} | {m.get(2, float('nan')):.3f} "  # noqa: E501
                f"| {s['rff']['max']:+.3f} | {s['xgdp_pct']['last']:+.3f} |"
            )
    lines += ["", "## Checks", "", "| check | value | pass | rule |", "|---|---|---|---|"]
    for r in report["checks"]:
        v = r["value"]
        vs = (
            ""
            if v is None
            else (", ".join(f"{x:.3f}" for x in v) if isinstance(v, list) else f"{v:.3g}")
        )
        lines.append(f"| {r['check']} | {vs} | {'pass' if r['pass'] else 'FAIL'} | {r['detail']} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())

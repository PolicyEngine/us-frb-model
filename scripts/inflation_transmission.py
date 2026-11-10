"""Where does the inflation response come from? Channel shut-offs and coefficient vintages.

Two experiments give a small core PCE response in this repo:

* the Board's demo ping, +100bp on ``rffintay_aerr`` in 2026Q1
  (``picxfe`` trough -0.034pp against "as much as 0.08" in the 2014 FEDS Note);
* the 2022-23 tightening counterfactual (``scripts/episode_2022_tightening.py``,
  variant A), core PCE 4q -0.14pp at 2023Q4 with unemployment +1.71pp.

The equations are the Board's ``model.xml`` unchanged and the shocked path
matches the Board's pyfrbus to < 1e-6 (VALIDATION.md, Test 2), so this script
does not look for a coding error. It asks which channel carries the inflation
response and whether the gap to the 2013-14 publications is the coefficient
vintage. Each row re-runs the experiment with one change:

``base``          the model as published.
``ptr_fixed``     long-run expected inflation ``ptr`` exogenous (held at
                  baseline): removes the expectations-drift channel.
``zexp_fixed``    the VAR expectations ``zpicxfe`` and ``zpieci`` exogenous:
                  removes the forward-looking terms of both NKPCs.
``fx_fixed``      real exchange rate ``fpxr`` exogenous: removes the
                  exchange-rate -> import-price -> desired-price channel.
``slope_2013``    wage unemployment slope ``y_pieci(2)`` set to the 2013
                  Bayesian 1985-2012 estimate, -0.024 (current -0.0167).
``bayes_2013``    all five price-wage NKPC parameters set to the 2013
                  Bayesian 1985-2012 column (Table 1, col. 3):
                  y_picxfe(1)=.712, y_picxfe(2)=.0032, y_pieci(1)=1.00,
                  y_pieci(3)=.0016, y_pieci(2)=-.024.
``ml_8507``       the same five set to the 1985-2007 ML column (col. 1):
                  .737, .0035, 1.00, .0018, -.034.

Source for the 2013 values:
vendor/frbus_package/documentation/price_wage_sector_083013.pdf, Table 1,
p. 8. Mapping: gamma_p -> y_picxfe(1), kappa_p -> y_picxfe(2),
gamma_w -> y_pieci(1), alpha_w -> y_pieci(2), kappa_w -> y_pieci(3). The
note restricts kappa_w = .5 kappa_p, and the current model.xml satisfies the
same restriction (0.000957 / 0.001915 = 0.50), which is why the units are
read as identical. The 2013 VAR-expectations auxiliary equations
(zpicxfe, zpieci) are not published, so the vintage rows keep the current
ones: they are approximate, not a reconstruction of the 2013 model.

The script also traces issue #13, transfers -> consumption, with the funds
rate pegged and the trend tax rates exogenous so neither policy rule leans
against the shock: an 8-quarter 1%-of-GDP add-factor on real transfers
(``gtr_aerr``) against the same real amount added to real after-tax labour
income (``yhl_aerr``). It reports consumption per unit of household income
(``ecnia`` over ``yht`` or ``yhl``), and one row with the hand-to-mouth share
``y_eco(4)`` set to 0.40, the share in the 2009-10 model used by Coenen et
al. (2012, Table 1).

About 20 model builds and solves, under a minute; take the heavy-job lock.

    uv run python scripts/inflation_transmission.py [--out DIR]

writes results/inflation_transmission.json and .md.
"""

from __future__ import annotations

import argparse
import atexit
import json
import shutil
import sys
import tempfile
from functools import cache
from pathlib import Path

import pandas as pd
from lxml import etree

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import episode_2022_tightening as ep  # noqa: E402

from frbus import Frbus, load_data  # noqa: E402

MODEL_XML = REPO / "vendor" / "pyfrbus_package" / "models" / "model.xml"
LONGBASE = REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"

START = pd.Period("2026Q1")
END = pd.Period("2030Q4")
SHOCK_END = pd.Period("2027Q4")

COEF_SETS: dict[str, dict[str, float]] = {
    "slope_2013": {"y_pieci(2)": -0.024},
    "bayes_2013": {
        "y_picxfe(1)": 0.712,
        "y_picxfe(2)": 0.0032,
        "y_pieci(1)": 1.00,
        "y_pieci(2)": -0.024,
        "y_pieci(3)": 0.0016,
    },
    "ml_8507": {
        "y_picxfe(1)": 0.737,
        "y_picxfe(2)": 0.0035,
        "y_pieci(1)": 1.00,
        "y_pieci(2)": -0.034,
        "y_pieci(3)": 0.0018,
    },
    "htm_040": {"y_eco(4)": 0.40},
}
EXOG_SETS: dict[str, list[str]] = {
    "ptr_fixed": ["ptr"],
    "zexp_fixed": ["zpicxfe", "zpieci"],
    "fx_fixed": ["fpxr"],
}
PRICE_VARIANTS = [
    "base",
    "ptr_fixed",
    "zexp_fixed",
    "fx_fixed",
    "slope_2013",
    "bayes_2013",
    "ml_8507",
]

_TMP = Path(tempfile.mkdtemp(prefix="frbus_coef_"))
atexit.register(shutil.rmtree, _TMP, ignore_errors=True)


def current_coefs(names: list[str]) -> dict[str, float]:
    root = etree.parse(str(MODEL_XML)).getroot()
    out = {}
    for cf in root.xpath("./variable/standard_equation/coeff"):
        n = cf.findtext("cf_name")
        if n in names:
            out[n] = float(cf.findtext("cf_value"))
    return out


@cache
def model_xml(variant: str) -> str:
    """Path to model.xml, or to a temporary copy with ``variant``'s coefficients."""
    if variant not in COEF_SETS:
        return str(MODEL_XML)
    tree = etree.parse(str(MODEL_XML))
    changes = dict(COEF_SETS[variant])
    for cf in tree.getroot().xpath("./variable/standard_equation/coeff"):
        n = cf.findtext("cf_name")
        if n in changes:
            cf.find("cf_value").text = repr(changes.pop(n))
    if changes:
        raise KeyError(f"coefficients not found in model.xml: {sorted(changes)}")
    path = _TMP / f"model_{variant}.xml"
    tree.write(str(path))
    return str(path)


def build(variant: str) -> Frbus:
    model = Frbus(model_xml(variant))
    if variant in EXOG_SETS:
        model.exogenize(EXOG_SETS[variant])
    return model


def core4(frame: pd.DataFrame, longbase: pd.DataFrame, w: slice) -> pd.Series:
    full = longbase["pcxfe"].copy()
    full.loc[w] = frame.loc[w, "pcxfe"]
    return 100 * (full / full.shift(4) - 1)


def _trough(s: pd.Series, fn: str = "min") -> list:
    q = s.idxmin() if fn == "min" else s.idxmax()
    return [float(s.loc[q]), str(q)]


def ping(longbase: pd.DataFrame, variant: str, start=START, end=END, fed_pings=False) -> dict:
    """The Board's demo ping: +1 on rffintay_aerr in the first quarter."""
    model = build(variant)
    data = longbase.copy()
    w = slice(start, end)
    data.loc[w, "dfpdbt"] = 0
    data.loc[w, "dfpsrp"] = 1
    if fed_pings:  # programs/pings.prg: no ZLB, no thresholds, rstar fixed
        data.loc[:, "rffmin"] = -9999
        data.loc[:, "dmptrsh"] = 0
        data.loc[w, "drstar"] = 0
    base = model.init_trac(start, end, data)
    adds = base.copy()
    adds.loc[start, "rffintay_aerr"] += 1
    sim = model.solve(start, end, adds)
    b, x = base.loc[w], sim.loc[w]
    dev = {
        "picxfe": x["picxfe"] - b["picxfe"],
        "core_pce_4q": (core4(sim, longbase, w) - core4(base, longbase, w)).loc[w],
        "pieci": x["pieci"] - b["pieci"],
        "ptr": x["ptr"] - b["ptr"],
        "xgap2": x["xgap2"] - b["xgap2"],
        "lur": x["lur"] - b["lur"],
        "fpxr_pct": 100 * (x["fpxr"] / b["fpxr"] - 1),
        "pmo_pct": 100 * (x["pmo"] / b["pmo"] - 1),
        "rff": x["rff"] - b["rff"],
    }
    lur_peak = float(dev["lur"].max())
    pic = float(dev["picxfe"].min())
    return {
        "variant": variant,
        "start": str(start),
        "picxfe_trough": _trough(dev["picxfe"]),
        "core_pce_4q_trough": _trough(dev["core_pce_4q"]),
        "pieci_trough": _trough(dev["pieci"]),
        "ptr_trough": _trough(dev["ptr"]),
        "xgap2_trough": _trough(dev["xgap2"]),
        "lur_peak": _trough(dev["lur"], "max"),
        "fpxr_pct_peak": _trough(dev["fpxr_pct"], "max"),
        "pmo_pct_trough": _trough(dev["pmo_pct"]),
        "picxfe_per_pp_lur": pic / lur_peak,
    }


def episode(longbase: pd.DataFrame, variant: str) -> dict:
    """Variant A of scripts/episode_2022_tightening.py under ``variant``."""
    model = build(variant)
    data = ep._frame(longbase, None)
    base = model.init_trac(ep.START, ep.END, data)
    hist = model.solve(ep.START, ep.END, base)
    w = slice(ep.START, ep.END)
    for v in ("rff", "xgdp", "lur", "pcxfe"):
        err = (hist.loc[w, v] - longbase.loc[w, v]).abs().max()
        assert err < 1e-6, f"{variant}: history run misses {v} by {err:.3e}"
    cf_in = base.copy()
    cf_in.loc[w, "rfffix"] = longbase.loc[w, "rffmin"]
    cf = model.solve(ep.START, ep.END, cf_in)
    eff = ep.effects(hist, cf, longbase)
    q = pd.Period("2023Q4")
    return {
        "variant": variant,
        "core_pce_4q_2023q4": float(eff.loc[q, "core_pce_4q"]),
        "core_pce_4q_mean_2022_2024": float(eff.loc["2022Q1":"2024Q4", "core_pce_4q"].mean()),
        "core_pce_level_pct_2023q4": float(eff.loc[q, "core_pce_level_pct"]),
        "lur_2023q4": float(eff.loc[q, "lur"]),
        "xgdp_pct_2023q4": float(eff.loc[q, "xgdp_pct"]),
        "ptr_2023q4": float(hist.loc[q, "ptr"] - cf.loc[q, "ptr"]),
        "pieci_mean_2022_2024": float(
            (hist.loc["2022Q1":"2024Q4", "pieci"] - cf.loc["2022Q1":"2024Q4", "pieci"]).mean()
        ),
        "fpxr_pct_2023q4": float(100 * (hist.loc[q, "fpxr"] / cf.loc[q, "fpxr"] - 1)),
        "pmo_pct_2023q4": float(100 * (hist.loc[q, "pmo"] / cf.loc[q, "pmo"] - 1)),
    }


def year_mean(s: pd.Series, n: int) -> float:
    return float(s.iloc[4 * (n - 1) : 4 * n].mean())


def income_shock(
    longbase: pd.DataFrame, channel: str, variant: str = "base", closure: str = "peg"
) -> dict:
    """1% of GDP for 8 quarters to real transfers or to after-tax labour income."""
    model = build(variant)
    data = longbase.copy()
    w = slice(START, END)
    data.loc[w, "dfpdbt"] = 0
    if closure == "peg":
        data.loc[w, "dfpex"] = 1
        data.loc[w, "dfpsrp"] = 0
        data.loc[w, "dmpintay"] = 0
        data.loc[w, "dmpex"] = 1
        data.loc[w, "rfffix"] = data.loc[w, "rff"]
    else:  # the sweep/benchmark default: inertial Taylor, surplus rule
        data.loc[w, "dfpex"] = 0
        data.loc[w, "dfpsrp"] = 1
    base = model.init_trac(START, END, data)
    adds = base.copy()
    s = slice(START, SHOCK_END)
    aerr = {"transfers": "gtr_aerr", "labour": "yhl_aerr"}[channel]
    adds.loc[s, aerr] += 0.01 * base.loc[s, "xgdp"]
    sim = model.solve(START, END, adds)
    b, x = base.loc[w], sim.loc[w]
    inc = {"transfers": "yht", "labour": "yhl"}[channel]
    dinc = x[inc] - b[inc]
    dc = x["ecnia"] - b["ecnia"]
    dx = x["xgdp"] - b["xgdp"]
    # Impact prediction from the hand-to-mouth term alone: eco moves by
    # y_eco(4) * dlog(yhl + yht), and ecnia by y_ecnia(1) * dlog(eco).
    htm = model_coef(variant, "y_eco(4)")
    w_eco = model_coef(variant, "y_ecnia(1)")
    b0 = b.iloc[0]
    htm_q1 = htm * w_eco * b0["ecnia"] / (b0["yhl"] + b0["yht"])
    out = {
        "channel": channel,
        "variant": variant,
        "closure": closure,
        "dc_per_dincome_q1": float(dc.iloc[0] / dinc.iloc[0]),
        "htm_predicted_q1": float(htm_q1),
        "dc_per_dincome": {n: year_mean(dc, n) / year_mean(dinc, n) for n in (1, 2)},
        "dxgdp_per_dincome": {n: year_mean(dx, n) / year_mean(dinc, n) for n in (1, 2)},
    }
    if channel == "transfers":
        dg = x["gtr"] - b["gtr"]
        out["dyht_per_dgtr_year1"] = year_mean(dinc, 1) / year_mean(dg, 1)
        out["multiplier"] = {n: year_mean(dx, n) / year_mean(dg, n) for n in (1, 2)}
    return out


def model_coef(variant: str, name: str) -> float:
    if variant in COEF_SETS and name in COEF_SETS[variant]:
        return COEF_SETS[variant][name]
    return current_coefs([name])[name]


def compute(longbase: pd.DataFrame) -> dict:
    names = sorted({k for v in COEF_SETS.values() for k in v})
    return {
        "current_coefficients": current_coefs(names),
        "coefficient_sets": COEF_SETS,
        "ping": {v: ping(longbase, v) for v in PRICE_VARIANTS},
        "ping_2040_fed_pings_settings": ping(
            longbase, "base", pd.Period("2040Q1"), pd.Period("2044Q4"), fed_pings=True
        ),
        "episode_A": {v: episode(longbase, v) for v in PRICE_VARIANTS},
        "income": {
            "transfers_peg": income_shock(longbase, "transfers"),
            "labour_peg": income_shock(longbase, "labour"),
            "transfers_taylor_srp": income_shock(longbase, "transfers", closure="taylor"),
            "transfers_taylor_srp_htm040": income_shock(
                longbase, "transfers", "htm_040", closure="taylor"
            ),
            "transfers_peg_htm040": income_shock(longbase, "transfers", "htm_040"),
        },
    }


def render(r: dict) -> str:
    f = lambda v, d=3: f"{v:+.{d}f}"  # noqa: E731
    out = [
        "# Inflation transmission and transfers: channel shut-offs and coefficient vintages",
        "",
        "Generated by `scripts/inflation_transmission.py`; do not edit by hand. "
        "Method, sources and reading: `docs/inflation-transmission.md`.",
        "",
        "## 100bp ping (rffintay_aerr +1 in 2026Q1, demo fiscal config)",
        "",
        "| variant | picxfe trough | core PCE 4q trough | pieci trough | ptr trough | xgap2 trough | lur peak | fpxr peak % | pmo trough % | picxfe per pp lur |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for v, p in r["ping"].items():
        out.append(
            f"| {v} | {f(p['picxfe_trough'][0])} ({p['picxfe_trough'][1]}) "
            f"| {f(p['core_pce_4q_trough'][0])} | {f(p['pieci_trough'][0])} "
            f"| {f(p['ptr_trough'][0], 4)} | {f(p['xgap2_trough'][0])} | {f(p['lur_peak'][0])} "
            f"| {f(p['fpxr_pct_peak'][0], 2)} | {f(p['pmo_pct_trough'][0], 2)} | {f(p['picxfe_per_pp_lur'])} |"  # noqa: E501
        )
    p = r["ping_2040_fed_pings_settings"]
    out += [
        "",
        f"Same ping from 2040Q1 with `programs/pings.prg` settings (rffmin=-9999, dmptrsh=0, drstar=0): "  # noqa: E501
        f"picxfe trough {f(p['picxfe_trough'][0])} ({p['picxfe_trough'][1]}), core PCE 4q trough "
        f"{f(p['core_pce_4q_trough'][0])}, xgap2 trough {f(p['xgap2_trough'][0])}, lur peak {f(p['lur_peak'][0])}.",  # noqa: E501
        "",
        "## 2022-23 tightening, variant A (history minus funds rate at the floor)",
        "",
        "| variant | core PCE 4q, 2023Q4 | mean 2022-24 | core PCE level %, 2023Q4 | lur 2023Q4 | GDP % 2023Q4 | ptr 2023Q4 | pieci mean 2022-24 | fpxr % 2023Q4 | pmo % 2023Q4 |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for v, e in r["episode_A"].items():
        out.append(
            f"| {v} | {f(e['core_pce_4q_2023q4'])} | {f(e['core_pce_4q_mean_2022_2024'])} "
            f"| {f(e['core_pce_level_pct_2023q4'])} | {f(e['lur_2023q4'], 2)} | {f(e['xgdp_pct_2023q4'], 2)} "  # noqa: E501
            f"| {f(e['ptr_2023q4'], 4)} | {f(e['pieci_mean_2022_2024'])} | {f(e['fpxr_pct_2023q4'], 2)} "  # noqa: E501
            f"| {f(e['pmo_pct_2023q4'], 2)} |"
        )
    out += [
        "",
        "## Income shocks (1% of GDP for 8 quarters)",
        "",
        "| run | closure | y_eco(4) | consumption per unit income, q1 | hand-to-mouth prediction, q1 | yr 1 | yr 2 | GDP per unit income yr 1 | yr 2 | transfers multiplier yr 1 | yr 2 |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i in r["income"].values():
        m = i.get("multiplier")
        htm = model_coef(i["variant"], "y_eco(4)")
        out.append(
            f"| {i['channel']} | {i['closure']} | {htm:.4f} | {i['dc_per_dincome_q1']:.3f} | {i['htm_predicted_q1']:.3f} "  # noqa: E501
            f"| {i['dc_per_dincome'][1]:.3f} | {i['dc_per_dincome'][2]:.3f} "
            f"| {i['dxgdp_per_dincome'][1]:.3f} | {i['dxgdp_per_dincome'][2]:.3f} "
            f"| {'' if m is None else f'{m[1]:.3f}'} | {'' if m is None else f'{m[2]:.3f}'} |"
        )
    t = r["income"]["transfers_peg"]
    out += [
        "",
        f"Real household transfer income per unit of real government transfers, year 1: {t['dyht_per_dgtr_year1']:.3f}.",  # noqa: E501
        "",
    ]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "results"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    r = compute(load_data(str(LONGBASE)))
    (out / "inflation_transmission.json").write_text(json.dumps(r, indent=2) + "\n")
    (out / "inflation_transmission.md").write_text(render(r))
    print(render(r))


if __name__ == "__main__":
    main()

"""The 2022-23 tightening: history against a no-tightening counterfactual.

LONGBASE (April 2026 vintage) carries the realised quarterly history through
2025Q4, including the funds rate path: 0.08% in 2021Q4, 0.12% in 2022Q1,
5.33% by 2023Q4. This script asks what FRB/US (VAR expectations) says that
path did to output, unemployment and core PCE inflation.

Method
------
* Window 2022Q1-2025Q4. Before ``init_trac`` the funds rate is put on the
  exogenous-path closure (``dmpintay=0, dmpex=1``, ``rfffix`` = realised
  ``rff``) and federal tax trends are made exogenous (``dfpex=1``) so fiscal
  policy is held at what actually happened. Tracking residuals then make the
  model reproduce history exactly; that is asserted.
* Counterfactual A, "never tighten": ``rfffix`` held at the model's
  lower bound ``rffmin`` (0.125%, the midpoint of the 0-0.25% range the
  FOMC set from March 2020 to March 2022) for all 16 quarters. (Realised
  rff was 0.08% in 2021Q4, below ``rffmin``; the rff equation floors the
  rule at ``rffmin``, so a 0.08% target would come out at 0.125% anyway.)
* Counterfactual B, "no hikes until 2024, then the rule": ``rfffix`` at
  ``rffmin`` through 2023Q4; from 2024Q1 both the history run and the
  counterfactual use the inertial Taylor rule (``dmpintay=1``), so after 2023
  the counterfactual's funds rate responds to its own higher inflation.
* Effect of the tightening = history minus counterfactual: real GDP in % of
  the counterfactual level, unemployment and inflation in pp. Core PCE
  inflation is the four-quarter % change of the ``pcxfe`` index (the same
  index the backtest uses), plus annualised q/q ``picxfe``.

Caveats (also in docs/benchmarks.md): every non-policy shock of 2022-25 is
held at its tracked value; expectations are the model's VAR, so the ~1pp rise
in the 10-year yield in early 2022 that markets priced ahead of the hikes is
treated as a term-premium/residual shock and is NOT removed in the
counterfactual (the counterfactual long rate only moves through the VAR's
response to the counterfactual funds rate); balance-sheet runoff (QT) is not
modelled; and the model is linear-ish around a 2022 state with supply-chain
and energy shocks it attributes to residuals.

Light job (2 x init_trac + 2 x solve over 16 quarters), but take the
heavy-job lock.

    uv run python scripts/episode_2022_tightening.py [--out DIR]

writes results/episode_2022_tightening.{json,md}.
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

START = pd.Period("2022Q1")
END = pd.Period("2025Q4")
RULE_FROM = pd.Period("2024Q1")
REPORT_AT = ["2022Q4", "2023Q4", "2024Q4", "2025Q4"]
# Opt-in MCE run (--mce): the stacked solve reads leads past the window from
# the data, so a 16-quarter window would pin 2026 expectations to LONGBASE.
# The window is extended 40 years, as in scripts/expectations_comparison.py.
END_MCE = pd.Period("2065Q4")


def _frame(longbase: pd.DataFrame, rule_from: pd.Period | None) -> pd.DataFrame:
    # Closures are set over 2022Q1-2025Q4 only. Under MCE the solve window runs
    # on to END_MCE, and from 2026Q1 both runs use LONGBASE's own settings
    # (inertial Taylor rule, fiscal rule), so the counterfactual is "agents
    # know the funds rate path through 2025, then the rule".
    data = longbase.copy()
    w = slice(START, END)
    data.loc[w, "dfpex"] = 1
    data.loc[w, "dfpsrp"] = 0
    data.loc[w, "dfpdbt"] = 0
    data.loc[w, "dmpintay"] = 0
    data.loc[w, "dmpex"] = 1
    data.loc[w, "rfffix"] = data.loc[w, "rff"]
    if rule_from is not None:
        r = slice(rule_from, END)
        data.loc[r, "dmpintay"] = 1
        data.loc[r, "dmpex"] = 0
    return data


def effects(hist: pd.DataFrame, cf: pd.DataFrame, longbase: pd.DataFrame) -> pd.DataFrame:
    w = slice(START, END)

    def core4(frame):
        full = longbase["pcxfe"].copy()
        full.loc[w] = frame.loc[w, "pcxfe"]
        return 100 * (full / full.shift(4) - 1)

    return pd.DataFrame(
        {
            "rff_hist": hist.loc[w, "rff"],
            "rff_cf": cf.loc[w, "rff"],
            "rg10": hist.loc[w, "rg10"] - cf.loc[w, "rg10"],
            "xgdp_pct": 100 * (hist.loc[w, "xgdp"] / cf.loc[w, "xgdp"] - 1),
            "lur": hist.loc[w, "lur"] - cf.loc[w, "lur"],
            "lur_cf": cf.loc[w, "lur"],
            "core_pce_4q": (core4(hist) - core4(cf)).loc[w],
            "picxfe": hist.loc[w, "picxfe"] - cf.loc[w, "picxfe"],
            "core_pce_level_pct": 100 * (hist.loc[w, "pcxfe"] / cf.loc[w, "pcxfe"] - 1),
        }
    )


def run(longbase: pd.DataFrame, variant: str, mce: str | None = None, end: pd.Period = END) -> dict:
    rule_from = RULE_FROM if variant == "B_rule_from_2024" else None
    model = Frbus(str(MODEL_XML), mce=mce)
    data = _frame(longbase, rule_from)
    base = model.init_trac(START, end, data)
    hist = model.solve(START, end, base)
    w = slice(START, END)
    for v in ("rff", "xgdp", "lur", "pcxfe"):
        err = (hist.loc[w, v] - longbase.loc[w, v]).abs().max()
        assert err < 1e-6, f"history run misses {v} by {err:.3e}"
    cf_in = base.copy()
    flat_to = END if rule_from is None else rule_from - 1
    cf_in.loc[START:flat_to, "rfffix"] = longbase.loc[START:flat_to, "rffmin"]
    cf = model.solve(START, end, cf_in)
    # The tracked rff add-factor is ~0 once history is off the floor; in
    # 2022Q1 (realised 0.124 vs floor 0.125) it is -0.0006.
    off = (cf.loc[START:flat_to, "rff"] - longbase.loc[START:flat_to, "rffmin"]).abs().max()
    assert off < 0.01, f"counterfactual funds rate is {off:.3f}pp off the floor"
    eff = effects(hist, cf, longbase)
    return {
        "variant": variant,
        "expectations": mce or "var",
        "window": [str(START), str(end)],
        "path": {q: {k: float(v) for k, v in eff.loc[pd.Period(q)].items()} for q in REPORT_AT},
        "extremes": {
            "xgdp_pct_min": [float(eff["xgdp_pct"].min()), str(eff["xgdp_pct"].idxmin())],
            "lur_max": [float(eff["lur"].max()), str(eff["lur"].idxmax())],
            "core_pce_4q_min": [float(eff["core_pce_4q"].min()), str(eff["core_pce_4q"].idxmin())],
            "lur_cf_min": [float(eff["lur_cf"].min()), str(eff["lur_cf"].idxmin())],
        },
        # comparable to Najjar & Shapiro (FRBSF EL 2025-03): average gap in
        # four-quarter core PCE inflation over 2022-2024
        "core_pce_4q_mean_2022_2024": float(eff.loc["2022Q1":"2024Q4", "core_pce_4q"].mean()),
        "quarterly": {str(q): {k: float(v) for k, v in row.items()} for q, row in eff.iterrows()},
    }


def render(rows: list[dict]) -> str:
    mode = rows[0].get("expectations", "var")
    title = "VAR expectations" if mode == "var" else f"model-consistent expectations, mce={mode}"
    out = [
        f"# The 2022-23 tightening in FRB/US ({title})",
        "",
        "Generated by `scripts/episode_2022_tightening.py`; do not edit by hand. "
        "Effect = history minus counterfactual. A: funds rate held at the "
        "0.125% floor through 2025Q4. B: held at the floor through 2023Q4, inertial "
        "Taylor rule from 2024Q1 in both runs. See docs/benchmarks.md for caveats "
        "and published comparators.",
        "",
    ]
    for r in rows:
        out += [
            f"## {r['variant']}",
            "",
            "| quarter | rff hist | rff cf | real GDP (%) | unemployment (pp) | cf unemployment (%) | core PCE 4q (pp) | core PCE level (%) | 10y yield (pp) |",  # noqa: E501
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for q, e in r["path"].items():
            out.append(
                f"| {q} | {e['rff_hist']:.2f} | {e['rff_cf']:.2f} | {e['xgdp_pct']:+.2f} "
                f"| {e['lur']:+.2f} | {e['lur_cf']:.2f} | {e['core_pce_4q']:+.2f} "
                f"| {e['core_pce_level_pct']:+.2f} "
                f"| {e['rg10']:+.2f} |"
            )
        x = r["extremes"]
        out += [
            "",
            f"Largest effects: real GDP {x['xgdp_pct_min'][0]:+.2f}% ({x['xgdp_pct_min'][1]}), "
            f"unemployment {x['lur_max'][0]:+.2f}pp ({x['lur_max'][1]}), "
            f"core PCE 4q {x['core_pce_4q_min'][0]:+.2f}pp ({x['core_pce_4q_min'][1]}); "
            f"mean core PCE 4q effect 2022-2024 {r['core_pce_4q_mean_2022_2024']:+.2f}pp. "
            f"Lowest counterfactual unemployment rate {x['lur_cf_min'][0]:.2f}% "
            f"({x['lur_cf_min'][1]}).",
            "",
        ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=REPO / "results")
    p.add_argument(
        "--mce",
        default=None,
        help="opt-in MCE mode (mcap, wp, mcap+wp, all); solves over 2022Q1-2065Q4 "
        "and writes episode_2022_tightening_mce_<mode>.{json,md}",
    )
    p.add_argument(
        "--long-window",
        action="store_true",
        help="VAR only: solve over 2022Q1-2065Q4 as the MCE run does (the reported "
        "2022-25 quarters must not change, since VAR does not look forward)",
    )
    args = p.parse_args(argv)
    longbase = load_data(str(LONGBASE))
    end = END_MCE if (args.mce or args.long_window) else END
    rows = [
        run(longbase, v, mce=args.mce, end=end) for v in ("A_never_tighten", "B_rule_from_2024")
    ]
    args.out.mkdir(parents=True, exist_ok=True)
    stem = "episode_2022_tightening"
    if args.mce:
        stem += "_mce_" + args.mce.replace("+", "_")
    elif args.long_window:
        stem += "_var_long_window"
    (args.out / f"{stem}.json").write_text(json.dumps(rows, indent=2) + "\n")
    md = render(rows)
    (args.out / f"{stem}.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

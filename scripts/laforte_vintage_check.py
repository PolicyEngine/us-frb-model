"""Does the model vintage explain the core PCE gap to Laforte (2018) Figure 11?

Under MCE (mcap+wp) the 100bp ping gives a core PCE trough of about -0.011pp
here against -0.0077pp in Laforte (2018) Figure 11 (1.45x; VALIDATION.md,
Test 5). Laforte ran the November 2018 model; this repo vendors the model.xml
of pyfrbus 1.0.0 (sha256 3227f4d2..., identical to the frbus_package.zip the
Board served in April 2022, i.e. the January 2021 release).

The November 2018 package is not vendored. The Internet Archive holds the
copy the Board served on 24 Jan 2019:
https://web.archive.org/web/20190124190801id_/https://www.federalreserve.gov/econres/files/frbus_package.zip
(zip sha1 e743dbe4382a155ddf02cece05a2134922f02824; mods/model.xml sha256
ba01c0cd39380520...). Diffing its mods/model.xml against the vendored one
(every <standard_equation> and <mce_equation>, text and coefficients):

* Wage-price block: picxfe, pieci, ptr, and the VAR and MCE equations for
  zpicxfe and zpieci are identical, equation text and every coefficient.
  The only wage-price differences are y_pmo(1) (0.000267 -> 0) and an
  add-factor added to the pgfl/pgsl identities.
* Elsewhere: rbbbp and reqp (BBB spread, equity premium) re-estimated;
  the January 2021 fiscal changes (gfdbtn, gfdbtnp, gfsrpn, trpt; README_2021JAN);
  the qecd/qeh trend-growth moving averages lengthened; the rffrule floor
  moved from @recode into rff; seven variables dropped.

So the price-wage coefficients cannot explain the gap. This script re-runs
the Laforte ping (scripts/expectations_comparison.py set-up) with the
coefficient changes reversed, and with the shock dated 2020Q1 (Laforte's
dates) and 2030Q1 instead of 2040Q1, to see what does move the core trough.
It reports; it does not tune anything.

    uv run python scripts/laforte_vintage_check.py [--out DIR]

writes results/laforte_vintage_check.json. Five 160-quarter stacked solves;
take the heavy-job lock or run it in CI.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd
from lxml import etree

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import expectations_comparison as ec  # noqa: E402
from frbus import load_data  # noqa: E402

# Coefficients of the November 2018 model (Jan 2019 package) that differ from
# the vendored model.xml. In the 2018 file y_rbbbp(4)=y_rbbbp(1) and
# y_rbbbp(5)=y_rbbbp(2) (same for reqp), so with these values the vendored
# equation form is the 2018 equation.
COEF_2018 = {
    "y_rbbbp(1)": 1.610399308071327,
    "y_rbbbp(2)": -0.2128580203560772,
    "y_rbbbp(3)": 0.8764985839424556,
    "y_reqp(1)": 3.140454174833396,
    "y_reqp(2)": 0.7294217907872275,
    "y_reqp(3)": 0.8044965674905952,
    "y_pmo(1)": 0.0002673018702731515,
}


def patched_xml(changes: dict[str, float], tmp: Path) -> Path:
    tree = etree.parse(str(ec.MODEL_XML))
    left = dict(changes)
    for cf in tree.getroot().xpath("./variable/standard_equation/coeff"):
        n = cf.findtext("cf_name")
        if n in left:
            cf.find("cf_value").text = repr(left.pop(n))
    if left:
        raise KeyError(f"coefficients not found: {sorted(left)}")
    out = tmp / "model_2018coef.xml"
    tree.write(str(out))
    return out


def summary(r: dict) -> dict:
    return {
        "start": r["window"][0],
        "core_trough": r["picxfe_trough"][:2],
        "gap_trough": r["xgap2_trough"][:2],
        "lur_peak": r["lur_peak"][:2],
        "r10_impact": r["rg10_impact"],
        "rff_q1_q4": r["path_q1_q12"]["rff"][:4],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=REPO / "results")
    args = p.parse_args(argv)
    longbase = load_data(str(ec.LONGBASE))
    pub = json.loads(ec.LAFORTE_JSON.read_text())["summary"]
    tmp = Path(tempfile.mkdtemp(prefix="frbus_vintage_"))
    rows = {}
    try:
        for name, start in (("base_2040", "2040Q1"), ("start_2030", "2030Q1"),
                            ("start_2020", "2020Q1")):
            s = pd.Period(start)
            rows[name] = summary(ec.monetary(longbase, "mcap+wp", s, s + 159, fed_pings=True))
        orig = ec.MODEL_XML
        ec.MODEL_XML = patched_xml(COEF_2018, tmp)
        try:
            rows["coef_2018"] = summary(
                ec.monetary(longbase, "mcap+wp", ec.PING_START, ec.PING_END, fed_pings=True)
            )
            rows["coef_2018_var"] = summary(
                ec.monetary(longbase, None, ec.PING_START, ec.PING_END, fed_pings=True)
            )
        finally:
            ec.MODEL_XML = orig
        rows["base_2040_var"] = summary(
            ec.monetary(longbase, None, ec.PING_START, ec.PING_END, fed_pings=True)
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = {"published_fig11": pub, "rows": rows}
    for r in rows.values():
        r["core_ratio_to_published"] = r["core_trough"][0] / pub["core_trough"][0]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "laforte_vintage_check.json").write_text(json.dumps(out, indent=2) + "\n")
    for k, r in rows.items():
        print(f"{k:14s} core {r['core_trough'][0]:+.4f} ({r['core_ratio_to_published']:.2f}x) "
              f"gap {r['gap_trough'][0]:+.3f} lur {r['lur_peak'][0]:+.3f} "
              f"r10 {r['r10_impact']:+.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

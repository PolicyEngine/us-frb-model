"""Evidence for the Laforte (2018) start-date bands, on any LONGBASE vintage.

Prints, as JSON, the ratios to Laforte (2018) of (a) the VAR 100bp ping from
the eight sweep start dates (Figure 2; scripts/inflation_transmission.py) and
(b) the MCE (mcap+wp) 100bp ping from 2020Q1, 2030Q1 and 2040Q1 (Figure 11;
scripts/expectations_comparison.py), all with the Board's pings.prg settings.
The bands in tests/test_inflation_transmission.py and tests/test_mce.py were
set from this output on the October 2026 and April 2026 vintages.

    uv run python scripts/laforte_start_date_evidence.py [--longbase PATH]

The April 2026 LONGBASE is not in the tree (vendor/ holds one vintage); it is
in git history:

    git show 2b62608^:vendor/data_only_package/LONGBASE.TXT > /tmp/longbase_april.txt

Stores nothing, and no CI job runs it routinely. Three 160-quarter stacked
solves per vintage (about two minutes on a GitHub runner): the bands were set
from a temporary job on PR #27 (Actions run 44379823376, both vintages).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import expectations_comparison as ec  # noqa: E402
import inflation_transmission as it  # noqa: E402

from frbus import load_data  # noqa: E402

FIG2 = {"core": -0.0345, "gap": -0.4861, "lur": 0.2189}
MCE_STARTS = ("2020Q1", "2030Q1", "2040Q1")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--longbase", type=Path, default=ec.LONGBASE)
    args = p.parse_args(argv)
    longbase = load_data(str(args.longbase))
    out: dict = {
        "longbase_sha256": hashlib.sha256(args.longbase.read_bytes()).hexdigest(),
        "var_fig2_sweep": {},
        "mce_fig11": {},
    }
    for s, q in it.ping_sweep(longbase, fed_pings=True).items():
        out["var_fig2_sweep"][s] = {
            "core_ratio": q["picxfe_trough"][0] / FIG2["core"],
            "gap_ratio": q["xgap2_trough"][0] / FIG2["gap"],
            "lur_ratio": q["lur_peak"][0] / FIG2["lur"],
            "lur_peak": q["lur_peak"],
        }
    lur = [v["lur_ratio"] for v in out["var_fig2_sweep"].values()]
    later = [v["lur_ratio"] for s, v in out["var_fig2_sweep"].items() if s != "2020Q1"]
    out["var_fig2_sweep_lur_ratio_min_max"] = [min(lur), max(lur)]
    out["var_fig2_sweep_lur_ratio_min_max_excluding_2020Q1"] = [min(later), max(later)]
    pub = json.loads(ec.LAFORTE_JSON.read_text())["summary"]
    for s in MCE_STARTS:
        start = pd.Period(s)
        r = ec.monetary(longbase, "mcap+wp", start, start + 159, fed_pings=True)
        rff = r["path_q1_q12"]["rff"][:8]
        out["mce_fig11"][s] = {
            "core_trough": r["picxfe_trough"],
            "core_ratio": r["picxfe_trough"][0] / pub["core_trough"][0],
            "gap_trough": r["xgap2_trough"],
            "gap_ratio": r["xgap2_trough"][0] / pub["gap_trough"][0],
            "lur_peak": r["lur_peak"],
            "lur_ratio": r["lur_peak"][0] / pub["lur_peak"][0],
            "r10_impact": r["rg10_impact"],
            "r10_impact_minus_published": r["rg10_impact"] - pub["r10_impact"],
            "rff_q1_q8": rff,
            "rff_max_abs_diff_from_published": max(
                abs(a - b) for a, b in zip(rff, pub["rff_q"], strict=True)
            ),
        }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

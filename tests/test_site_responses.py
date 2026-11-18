"""Pin the site export (results/site_responses.json) to the model and to the
other committed artifacts, so the site's GDP, unemployment and inflation
paths cannot drift from the numbers quoted elsewhere in the repo."""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import site_responses  # noqa: E402

from frbus import load_data  # noqa: E402

COMMITTED = json.loads((REPO / "results" / "site_responses.json").read_text())


@pytest.fixture(scope="module")
def fresh(longbase):
    r = site_responses.compute(longbase, load_data(str(site_responses.SHOCK)))
    return json.loads(json.dumps(r))


def test_committed_export_is_current(fresh):
    assert COMMITTED.keys() == fresh.keys()
    assert COMMITTED["quarters"] == fresh["quarters"]
    for name, e in fresh["experiments"].items():
        c = COMMITTED["experiments"][name]
        assert c.keys() == e.keys(), name
        assert c["summary"] == e["summary"], name
        for v in fresh["variables"]:
            assert c["paths"][v] == pytest.approx(e["paths"][v], abs=1e-6), (name, v)
    assert COMMITTED["scorecard"] == fresh["scorecard"]


def test_shape_and_units():
    assert len(COMMITTED["quarters"]) == 20
    assert COMMITTED["quarters"][0] == "2026Q1"
    assert set(COMMITTED["experiments"]) == {"monetary", "purchases", "transfers", "taxes"}
    for e in COMMITTED["experiments"].values():
        assert set(e["paths"]) == set(COMMITTED["variables"])
        assert all(len(p) == 20 for p in e["paths"].values())


def test_monetary_matches_site_numbers():
    """Same pyfrbus path, same numbers as results/site_numbers.json."""
    sn = json.loads((REPO / "results" / "site_numbers.json").read_text())
    s = COMMITTED["experiments"]["monetary"]["summary"]
    assert s["rff_impact"] == sn["rff_impact"]
    assert s["xgdp_pct_peak"] == sn["xgdp_trough_pct"]
    assert s["xgap2_peak"] == sn["xgap2_trough"]
    assert s["lur_peak"] == sn["lur_peak"]
    assert s["picxfe_peak"] == sn["picxfe_trough"]
    assert s["core_pce_4q_peak"] == sn["core_pce_4q_trough"]


def test_fiscal_multipliers_match_benchmark_grid():
    rows = json.loads((REPO / "results" / "benchmark_multipliers.json").read_text())
    grid = {
        r["instrument"]: r["multiplier"]
        for r in rows
        if r["monetary"] == "taylor" and r["fiscal"] == "srp"
    }
    for inst in ("purchases", "transfers", "taxes"):
        m = COMMITTED["experiments"][inst]["multiplier"]
        for year in ("1", "2"):
            assert m[year] == pytest.approx(grid[inst][year], abs=1e-4), (inst, year)


def test_signs_make_sense():
    ex = COMMITTED["experiments"]
    m = ex["monetary"]["summary"]
    assert m["rff_impact"] == pytest.approx(1.0, abs=0.01)
    assert m["xgdp_pct_peak"]["value"] < 0 < m["lur_peak"]["value"]
    assert m["picxfe_peak"]["value"] < 0
    for inst in ("purchases", "transfers", "taxes"):
        s = ex[inst]["summary"]
        assert s["xgdp_pct_peak"]["value"] > 0 > s["lur_peak"]["value"], inst
        assert s["xgdp_pct_year"]["1"] > 0, inst


def test_every_scorecard_row_is_inside_its_band():
    """Published bands, plus two labelled sanity bounds (unemployment by start
    date, transfers below purchases)."""
    outside = [r["check"] for r in COMMITTED["scorecard"] if not r["inside"]]
    assert not outside, outside

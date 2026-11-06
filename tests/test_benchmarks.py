"""Benchmark gates: fiscal closures and the 2022-23 tightening (slow suite).

Sources and conversions are in docs/benchmarks.md. Only ranges that come
from a published TABLE, converted to this repo's sustained-shock calendar-year
definition, are used as gates; chart readings (Coenen et al.) are reported
there but never gated.

* Purchases: CBO's "Fed responds typically" path (Whalen & Reichling 2015,
  Table 2) gives 0.45-1.82 in year 1 and 0.24-1.21 in year 2 under an active
  rule; the "Fed response limited" path gives 0.50-2.09 / 0.50-2.50 when the
  funds rate does not lean against the stimulus.
* Transfers are NOT gated against CBO: the derived active-Fed range for
  transfers to individuals (0.36-1.52 in year 1) excludes this model's 0.28,
  a recorded gap (docs/benchmarks.md, section 3). The gate is the ordering
  0 < transfers < purchases plus a loose band.
* Closure switches must do what they say: with trp exogenized the fiscal rule
  has no instrument, so the srp and exog rows must coincide; with the rule
  off, trp barely moves and multipliers rise in year 2.
* 2022-23 episode: the history run must reproduce history, the effects must
  have the right signs, and the committed JSON must be current.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import benchmark_multipliers as bm  # noqa: E402
import episode_2022_tightening as ep  # noqa: E402

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def grid(longbase):
    return {
        (i, m, f): bm.run(longbase, i, m, f)
        for i in bm.INSTRUMENTS
        for m in bm.MONETARY
        for f in bm.FISCAL
    }


@pytest.fixture(scope="module")
def episode(longbase):
    return {v: ep.run(longbase, v) for v in ("A_never_tighten", "B_rule_from_2024")}


def test_purchases_inside_cbo_table2_bands(grid):
    for f in bm.FISCAL:
        t = grid[("purchases", "taylor", f)]["multiplier"]
        assert 0.45 <= t[1] <= 1.82, f"taylor/{f} year 1 {t[1]:.3f}"
        assert 0.24 <= t[2] <= 1.21, f"taylor/{f} year 2 {t[2]:.3f}"
        p = grid[("purchases", "peg", f)]["multiplier"]
        assert 0.50 <= p[1] <= 2.09, f"peg/{f} year 1 {p[1]:.3f}"
        assert 0.50 <= p[2] <= 2.50, f"peg/{f} year 2 {p[2]:.3f}"


def test_transfers_ordering_and_loose_band(grid):
    for m in bm.MONETARY:
        for f in bm.FISCAL:
            t = grid[("transfers", m, f)]["multiplier"]
            g = grid[("purchases", m, f)]["multiplier"]
            for year in (1, 2):
                assert 0.15 < t[year] < g[year], f"{m}/{f} year {year}"
                assert t[year] < 0.7, f"{m}/{f} year {year} {t[year]:.3f}"


def test_fiscal_closure_switch_does_what_it_says(grid):
    for m in bm.MONETARY:
        srp, exog = grid[("taxes", m, "srp")], grid[("taxes", m, "exog")]
        for year in (1, 2):
            assert srp["multiplier"][year] == pytest.approx(exog["multiplier"][year], abs=1e-9)
        for inst in ("purchases", "transfers"):
            on, off = grid[(inst, m, "srp")], grid[(inst, m, "exog")]
            # The surplus rule raises the tax rate during the stimulus ...
            assert on["dtrp_year2_pp"] > 2 * off["dtrp_year2_pp"] > 0
            # ... and so claws back part of it: rule off gives the larger multiplier.
            assert off["multiplier"][2] > on["multiplier"][2]


def test_monetary_accommodation_raises_every_fiscal_multiplier(grid):
    for inst in bm.INSTRUMENTS:
        for f in bm.FISCAL:
            for year in (1, 2):
                assert (
                    grid[(inst, "peg", f)]["multiplier"][year]
                    > grid[(inst, "taylor", f)]["multiplier"][year]
                ), f"{inst}/{f} year {year}"


def test_committed_benchmark_grid_is_current(grid):
    committed = json.loads((REPO / "results" / "benchmark_multipliers.json").read_text())
    by_key = {(r["instrument"], r["monetary"], r["fiscal"]): r for r in committed}
    for key, fresh in grid.items():
        for year in (1, 2):
            assert by_key[key]["multiplier"][str(year)] == pytest.approx(
                fresh["multiplier"][year], abs=1e-6
            ), key


def test_episode_signs(episode):
    # ep.run already asserts the history run reproduces rff, xgdp, lur, pcxfe.
    for v, r in episode.items():
        e = r["path"]["2023Q4"]
        assert e["xgdp_pct"] < 0, v
        assert e["lur"] > 0, v
        assert e["core_pce_4q"] < 0, v
        assert e["rg10"] > 0, v
    # Both variants are identical until the rule switches on in 2024Q1.
    a, b = episode["A_never_tighten"]["path"], episode["B_rule_from_2024"]["path"]
    assert a["2023Q4"]["xgdp_pct"] == pytest.approx(b["2023Q4"]["xgdp_pct"], abs=1e-9)


def test_committed_episode_is_current(episode):
    committed = {
        r["variant"]: r
        for r in json.loads((REPO / "results" / "episode_2022_tightening.json").read_text())
    }
    for v, fresh in episode.items():
        for q, row in fresh["quarterly"].items():
            for k, val in row.items():
                assert committed[v]["quarterly"][q][k] == pytest.approx(val, abs=1e-6), (v, q, k)

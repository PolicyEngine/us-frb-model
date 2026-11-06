"""Scenario-sweep properties as gates (slow suite; runs in correctness-gates).

scripts/scenario_sweep.py solves monetary shocks of -200..+200bp (and +100bp
held 1/4/8 quarters) and 8-quarter purchases, transfers and tax shocks of
several sizes and both signs. These tests re-run it and assert:

* every family's zero shock reproduces the baseline (< 1e-8);
* linearity in size, symmetry in sign, reversion and persistence ordering
  (scenario_sweep.checks);
* the year-1/2 purchases and tax multipliers equal the gated ones in
  tests/test_multipliers.py -- solves are period by period under VAR
  expectations, so ending the shock after 8 quarters cannot change years 1-2;
* the committed results/scenario_sweep.json is what the code produces.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import scenario_sweep  # noqa: E402

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def families(longbase):
    return {
        "monetary": scenario_sweep.run_monetary(longbase),
        "purchases": scenario_sweep.run_purchases(longbase),
        "transfers": scenario_sweep.run_transfers(longbase),
        "taxes": scenario_sweep.run_taxes(longbase),
    }


def test_sweep_checks_pass(families):
    failed = [
        f"{r['check']} = {r['value']}" for r in scenario_sweep.checks(families) if not r["pass"]
    ]
    assert not failed, "; ".join(failed)


def test_multipliers_match_the_gated_runs(families):
    """Same numbers as tests/test_multipliers.py (0.725/0.643; 0.22/0.32)."""
    purchases = families["purchases"]["purchases_+1.0pct_gdp"]["multiplier"]
    taxes = families["taxes"]["tax_cut_+2.0pp"]["multiplier"]
    assert purchases[1] == pytest.approx(0.725, abs=0.001)
    assert purchases[2] == pytest.approx(0.643, abs=0.001)
    assert taxes[1] == pytest.approx(0.22, abs=0.01)
    assert taxes[2] == pytest.approx(0.32, abs=0.01)


def test_transfers_multiplier_below_purchases(families):
    """Transfers pass through household spending, so per dollar they must
    raise GDP by less than purchases (CBO ARRA tables, Whalen & Reichling
    2015) but still raise it."""
    t = families["transfers"]["transfers_+1.0pct_gdp"]["multiplier"]
    g = families["purchases"]["purchases_+1.0pct_gdp"]["multiplier"]
    for year in (1, 2):
        assert 0 < t[year] < g[year], (
            f"year {year}: transfers {t[year]:.3f}, purchases {g[year]:.3f}"
        )


def test_committed_sweep_is_current(families):
    """Every committed deviation path, quarter by quarter, every variable, is
    what the code produces now (not only the minimum), and so are the
    multipliers and every check value."""
    committed = json.loads((REPO / "results" / "scenario_sweep.json").read_text())
    assert set(committed["runs"]) == set(families)
    for fam, runs in families.items():
        assert set(committed["runs"][fam]) == set(runs), fam
        for name, run in runs.items():
            stored = committed["runs"][fam][name]
            fresh = scenario_sweep.paths(run["dev"])
            assert stored["path"]["quarters"] == fresh["quarters"], f"{fam}/{name}"
            for var in run["dev"].columns:
                assert stored["path"][var] == pytest.approx(fresh[var], abs=1e-6), (
                    f"{fam}/{name}/{var}"
                )
            for year, m in run.get("multiplier", {}).items():
                assert stored["multiplier"][str(year)] == pytest.approx(m, abs=1e-6), (
                    f"{fam}/{name} year {year}"
                )
    fresh_checks = scenario_sweep.checks(families)
    assert [r["check"] for r in committed["checks"]] == [r["check"] for r in fresh_checks]
    for old, new in zip(committed["checks"], fresh_checks, strict=True):
        assert old["pass"] == new["pass"], old["check"]
        if old["value"] is not None:
            assert old["value"] == pytest.approx(new["value"], abs=1e-6), old["check"]

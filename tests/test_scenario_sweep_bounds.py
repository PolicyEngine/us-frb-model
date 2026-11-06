"""Fast, hermetic: the sweep's checks re-evaluated on the committed paths.

``scripts/scenario_sweep.py`` writes every deviation path to
results/scenario_sweep.json; ``families_from_report`` rebuilds the solver
output from it, so ``checks`` runs here without a solve. The perturbation
tests show each kind of gate can fail: scaling one run's path by a few
percent (6% for the 200bp unemployment path, 3% for an asymmetry; sized so the
measured gap cannot cancel it) or by 1% on the 5x purchases run, whose gap is
gated on the log-aggregation prediction, turns the check red.
"""

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import scenario_sweep  # noqa: E402

REPORT = json.loads((REPO / "results" / "scenario_sweep.json").read_text())


def _failed(families):
    return {r["check"] for r in scenario_sweep.checks(families) if not r["pass"]}


@pytest.fixture
def families():
    return scenario_sweep.families_from_report(copy.deepcopy(REPORT))


def test_committed_paths_pass_every_check(families):
    assert _failed(families) == set()


def test_committed_check_values_match_the_paths(families):
    for old, new in zip(REPORT["checks"], scenario_sweep.checks(families), strict=True):
        assert old["check"] == new["check"]
        if old["value"] is not None:
            assert new["value"] == pytest.approx(old["value"], abs=1e-8), old["check"]


def test_a_less_linear_monetary_response_fails(families):
    dev = families["monetary"]["impulse_+2.00pp"]["dev"]
    dev["lur"] = dev["lur"] * 1.06
    assert "monetary linearity 200 vs 2x100: lur" in _failed(families)


def test_a_three_percent_monetary_asymmetry_fails(families):
    dev = families["monetary"]["impulse_-1.00pp"]["dev"]
    dev["rff"] = dev["rff"] * 1.03
    assert "monetary symmetry +100 vs -100: rff" in _failed(families)


@pytest.mark.parametrize("factor", [0.99, 1.01])
def test_purchases_linearity_must_match_log_aggregation(families, factor):
    """Both directions fail: the gap is gated on the prediction, so a model
    that became MORE linear than log aggregation allows is also caught."""
    dev = families["purchases"]["purchases_+0.5pct_gdp"]["dev"]
    dev["xgdp_pct"] = dev["xgdp_pct"] * factor
    assert "purchases: linearity 5x" in _failed(families)


def test_a_tax_asymmetry_fails(families):
    dev = families["taxes"]["tax_cut_-2.0pp"]["dev"]
    dev["xgdp_pct"] = dev["xgdp_pct"] * 1.03
    assert "taxes: symmetry at +-2% / pp" in _failed(families)

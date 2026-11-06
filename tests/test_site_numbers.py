"""Pin the 100bp-shock numbers the Macro site quotes to committed data.

No solve: scripts/site_numbers.py reads the committed pyfrbus reference path
and LONGBASE. The site quotes the output-gap trough (-0.50pp) and the 2027
wage bill (-0.65%), which were not previously reproducible from this repo.
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import site_numbers  # noqa: E402

from frbus import load_data  # noqa: E402


@pytest.fixture(scope="module")
def numbers(longbase):
    return site_numbers.compute(longbase, load_data(str(site_numbers.SHOCK)))


def test_output_gap_trough(numbers):
    assert numbers["xgap2_trough"] == {
        "value": pytest.approx(-0.5012, abs=1e-4),
        "quarter": "2027Q3",
    }


def test_wage_bill_2027(numbers):
    wb = numbers["wage_bill_2027_pct"]
    assert wb["pl_plus_lhp"] == pytest.approx(-0.6453, abs=1e-4)
    # The adapter's additive approximation is within 0.001pp of the product.
    assert abs(wb["pl_plus_lhp"] - wb["exact_product"]) < 1e-3


def test_headline_irf_values(numbers):
    """The VALIDATION.md 100bp table, pinned rather than banded."""
    assert numbers["rff_impact"] == pytest.approx(1.0001, abs=1e-4)
    assert numbers["xgdp_trough_pct"] == {
        "value": pytest.approx(-0.5512, abs=1e-4),
        "quarter": "2027Q4",
    }
    assert numbers["lur_peak"] == {"value": pytest.approx(0.2584, abs=1e-4), "quarter": "2027Q4"}
    assert numbers["picxfe_trough"]["value"] == pytest.approx(-0.0336, abs=1e-4)
    # Four-quarter core inflation (the Fed charts' concept) troughs later.
    assert numbers["core_pce_4q_trough"] == {
        "value": pytest.approx(-0.0341, abs=1e-4),
        "quarter": "2028Q2",
    }


def test_committed_artifact_is_current(numbers):
    committed = json.loads((REPO / "results" / "site_numbers.json").read_text())
    assert committed == json.loads(json.dumps(numbers))

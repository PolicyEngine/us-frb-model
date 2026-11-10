"""Model-consistent expectations (MCE): opt-in stacked-time solve.

The hard gate (slow-marked, run as a CI correctness-gate step) compares the
100bp monetary shock under each of ``mce="mcap"``, ``"wp"``, ``"mcap+wp"`` and
``"all"`` against
committed solutions from the Board's own pyfrbus on the identical experiment
(scripts/generate_vendor_mce_reference.sh), at the same 1e-6 tolerance as the
VAR cross-validation gate; observed agreement is 1e-9 to 1.5e-8.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from frbus import Frbus
from frbus.exceptions import ConvergenceError, FrbusError
from frbus.mce import rsub
from frbus.parse import MCE_TYPES, parse_model
from tests.conftest import MODEL_XML

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import scenarios  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
START, END = pd.Period(scenarios.START), pd.Period(scenarios.END)
TOL = 1e-6


def vendor_csv(mode: str) -> Path:
    return DATA_DIR / f"vendor_shock_mce_{mode.replace('+', '_')}_2026q1_2030q4.csv"


# ------------------------------------------------------------------ fast tests


def test_var_default_unchanged():
    var = Frbus(str(MODEL_XML))
    assert var.mce is None and var.mce_vars == []
    spec = parse_model(str(MODEL_XML))
    i = spec.endo_names.index("zrff10")
    # The VAR equation is a lag polynomial; the MCE one has a lead.
    assert "(1)" not in spec.equations[i]
    assert spec.mce_equations["zrff10"][1].endswith("zrff10(1)")


def test_invalid_mce_type():
    with pytest.raises(ValueError, match="mce must be"):
        Frbus(str(MODEL_XML), mce="rational")


@pytest.mark.parametrize(
    "mode, expected",
    [("mcap", 12), ("wp", 2), ("mcap+wp", 14), ("all", 25)],
)
def test_mce_groups_match_pyfrbus(mode, expected):
    # Counts of <mce_equation> per pyfrbus get_mce_xpath selection.
    model = Frbus(str(MODEL_XML), mce=mode)
    assert len(model.mce_vars) == expected
    assert set(MCE_TYPES) == {"mcap", "wp", "mcap+wp", "all"}


def test_mce_constants_are_per_group():
    # y_zrff10_1 exists in both the VAR and the MCE equation with different
    # values; the MCE value must be used only under MCE.
    spec = parse_model(str(MODEL_XML))
    assert spec.mce_constants["mcap"]["y_zrff10_1"] != spec.constants.get("y_zrff10_1")


def test_rsub_period_relative_refs():
    eq = [("", ("a", -2)), ("*2+", ("b", 1)), ("-", ("c", 0)), ("", None)]
    assert rsub(eq, {"a": 0, "b": 1, "c": 2}) == "V[r-2,0]*2+V[r+1,1]-V[r,2]"


def test_terminal_data_required(longbase):
    model = Frbus(str(MODEL_XML), mce="mcap")
    short = longbase.loc[:"2030Q4"]
    with pytest.raises(ValueError, match="terminal condition"):
        model.init_trac(pd.Period("2030Q1"), pd.Period("2030Q4"), short)


def test_mce_baseline_reproduces_data(longbase):
    model = Frbus(str(MODEL_XML), mce="mcap+wp")
    s, e = pd.Period("2026Q1"), pd.Period("2026Q4")
    with_adds = model.init_trac(s, e, longbase)
    sim = model.solve(s, e, with_adds)
    diff = (sim - with_adds).loc[s:e, model.endo_names].abs().to_numpy()
    assert np.nanmax(diff) < 1e-8


def test_mce_non_convergence_raises(longbase):
    model = Frbus(str(MODEL_XML), mce="mcap")
    s, e = pd.Period("2026Q1"), pd.Period("2027Q4")
    with_adds = model.init_trac(s, e, longbase)
    with_adds.loc[s, "rffintay_aerr"] += 1
    with pytest.raises(ConvergenceError):
        model.solve(s, e, with_adds, options={"maxiter": 1})


def test_mce_missing_terminal_value_raises(longbase):
    model = Frbus(str(MODEL_XML), mce="mcap")
    s, e = pd.Period("2026Q1"), pd.Period("2026Q4")
    with_adds = model.init_trac(s, e, longbase)
    with_adds.loc[e + 1, "zrff10"] = np.nan
    with pytest.raises(FrbusError, match="not finite"):
        model.solve(s, e, with_adds)


# ------------------------------------------------------------- gate (slow)


def _solve_monetary(mode: str, longbase) -> pd.DataFrame:
    model = Frbus(str(MODEL_XML), mce=mode)
    data = longbase.copy()
    scenarios.set_policy("monetary", data, START, END)
    with_adds = model.init_trac(START, END, data)
    scenarios.apply_shock("monetary", with_adds, START, END)
    return model.solve(START, END, with_adds)


@pytest.mark.slow
@pytest.mark.parametrize("mode", ["mcap", "wp", "mcap+wp", "all"])
def test_mce_matches_vendor_pyfrbus(mode, longbase):
    """Hard gate: full 284 x 20 vector against the Board's pyfrbus."""
    fresh = os.environ.get("FRESH_VENDOR_MCE_CSV")
    if fresh and os.environ.get("VENDOR_MCE") == mode:
        path = Path(fresh)
    elif fresh:
        pytest.skip("fresh vendor CSV is for another MCE mode")
    else:
        path = vendor_csv(mode)
    vendor = pd.read_csv(path, index_col=0)
    vendor.index = pd.PeriodIndex(vendor.index, freq="Q")
    ours = _solve_monetary(mode, longbase).loc[START:END, vendor.columns]
    assert ours.shape == vendor.shape == (20, 284)
    abs_diff = (ours - vendor).abs().to_numpy()
    rel_diff = abs_diff / np.maximum(np.abs(vendor.to_numpy()), 1e-8)
    assert np.nanmax(abs_diff) < TOL, f"max abs diff {np.nanmax(abs_diff):.3e}"
    assert np.nanmax(rel_diff) < TOL, f"max rel diff {np.nanmax(rel_diff):.3e}"


def test_mce_differs_from_var(longbase):
    """MCE must actually change the answer: wp makes core inflation jump on impact."""
    var = pd.read_csv(DATA_DIR / "vendor_shock_2026q1_2030q4.csv", index_col=0)
    mcwp = pd.read_csv(vendor_csv("mcap+wp"), index_col=0)
    assert abs(var["zrff10"].iloc[0] - mcwp["zrff10"].iloc[0]) > 1e-3
    base = longbase.loc[str(START), "picxfe"]
    assert mcwp["picxfe"].iloc[0] - base < -1e-3  # forward-looking wage-price block


def test_var_solver_defaults_unchanged():
    # The residual stopping rule is MCE-only; VAR solves keep the step test.
    from frbus import solver

    assert solver.solver_defaults(None)["ftol"] is None
    assert solver.solver_defaults(None)["xtol"] == 1e-8


# Laforte (2018) FEDS Note, Figure 11, "New Version": 100bp funds-rate shock
# under MCE for the financial and wage-price sectors (footnote 3: MCAP+WP).
# docs/data/laforte2018_fig11_mce_ping.json. The model vintage differs (2018
# vs the vendored model), so the bands are wider for the wage-price outcomes
# than for the financial ones; see VALIDATION.md, Test 5.
LAFORTE_JSON = Path(__file__).resolve().parents[1] / "docs" / "data" / (
    "laforte2018_fig11_mce_ping.json"
)


@pytest.mark.slow
def test_mce_ping_matches_laforte_2018(longbase):
    import json

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import expectations_comparison as ec

    pub = json.loads(LAFORTE_JSON.read_text())["summary"]
    ours = ec.monetary(longbase, "mcap+wp", ec.PING_START, ec.PING_END, fed_pings=True)
    path = ours["path_q1_q12"]
    # Financial block: the funds-rate path and the 10-year yield on impact.
    assert np.allclose(path["rff"][:8], pub["rff_q"], atol=0.01)
    assert abs(ours["rg10_impact"] - pub["r10_impact"]) < 0.01
    # Real side: output gap trough within 10%, unemployment peak within 25%.
    assert abs(ours["xgap2_trough"][0] / pub["gap_trough"][0] - 1) < 0.10
    assert abs(ours["lur_peak"][0] / pub["lur_peak"][0] - 1) < 0.25
    # Core inflation: same sign, within a factor of two (observed 1.45x).
    ratio = ours["picxfe_trough"][0] / pub["core_trough"][0]
    assert 0.5 < ratio < 2.0

"""Tests for the public uncertainty surface (frbus.uncertainty)."""

import numpy as np
import pandas as pd
import pytest

from frbus.exceptions import ConvergenceError

START, END = pd.Period("2026Q1"), pd.Period("2026Q3")
RESID = ("2000Q1", "2019Q4")
NREPL = 20


@pytest.fixture(scope="module")
def with_adds(model, longbase):
    data = longbase.copy()
    data.loc[START:END, "dfpdbt"] = 0
    data.loc[START:END, "dfpsrp"] = 1
    return model.init_trac("2000Q1", END, data)


@pytest.fixture(scope="module")
def result(model, with_adds):
    return model.stochsim_bands(NREPL, with_adds, START, END, *RESID, seed=42)


def test_bands_bracket_deterministic_path(result):
    """The demeaned bootstrap perturbs symmetrically around the scenario, so
    the deterministic path must lie inside the 90% band, and band columns must
    be correctly ordered."""
    assert result.n_success == NREPL and result.n_failed == 0
    assert result.failures == []
    for name in result.series:
        det = result.deterministic[name].to_numpy()
        lo90 = result.bands[(name, "lower90")].to_numpy()
        lo68 = result.bands[(name, "lower68")].to_numpy()
        med = result.bands[(name, "median")].to_numpy()
        up68 = result.bands[(name, "upper68")].to_numpy()
        up90 = result.bands[(name, "upper90")].to_numpy()
        assert np.all(lo90 <= lo68), name
        assert np.all(lo68 <= med), name
        assert np.all(med <= up68), name
        assert np.all(up68 <= up90), name
        assert np.all((lo90 <= det) & (det <= up90)), name
        # Bands must have real width: this is a stochastic, not degenerate, fan
        assert np.all(up90 > lo90), name


def test_bands_reproducible_under_fixed_seed(model, with_adds, result):
    again = model.stochsim_bands(NREPL, with_adds, START, END, *RESID, seed=42)
    pd.testing.assert_frame_equal(result.bands, again.bands)
    other = model.stochsim_bands(NREPL, with_adds, START, END, *RESID, seed=43)
    assert not result.bands.equals(other.bands)


def test_band_shape_and_labels(result):
    periods = pd.period_range(START, END, freq="Q")
    assert list(result.bands.index) == list(periods)
    assert result.deterministic.shape == (len(periods), len(result.series))
    labels = {b for _, b in result.bands.columns}
    assert labels == {"median", "lower68", "upper68", "lower90", "upper90"}
    assert result.failure_rate == 0.0


def test_failures_are_counted_not_swallowed(model, with_adds, monkeypatch):
    real_solve = model.solve
    calls = {"n": 0}

    def flaky_solve(simstart, simend, scenario, options=None):
        calls["n"] += 1
        # Call 1 is the deterministic solve; fail stochastic draws 2 and 4.
        if calls["n"] in (2, 4):
            raise ConvergenceError("deliberate failed replication")
        return real_solve(simstart, simend, scenario, options=options)

    monkeypatch.setattr(model, "solve", flaky_solve)
    res = model.stochsim_bands(5, with_adds, START, END, *RESID, seed=42)
    assert res.nrepl == 5
    assert res.n_success == 3
    assert res.n_failed == 2
    assert res.failure_rate == pytest.approx(0.4)
    assert all(f.startswith("ConvergenceError:") for f in res.failures)
    assert not res.bands.isna().any().any()


def test_all_failures_raise(model, with_adds, monkeypatch):
    real_solve = model.solve
    calls = {"n": 0}

    def failing_solve(simstart, simend, scenario, options=None):
        calls["n"] += 1
        if calls["n"] > 1:  # let the deterministic solve through
            raise ConvergenceError("no replication converges")
        return real_solve(simstart, simend, scenario, options=options)

    monkeypatch.setattr(model, "solve", failing_solve)
    with pytest.raises(ConvergenceError, match="all 3 stochastic replications"):
        model.stochsim_bands(3, with_adds, START, END, *RESID, seed=42)


def test_input_validation(model, with_adds):
    with pytest.raises(ValueError, match="not among endogenous"):
        model.stochsim_bands(
            2, with_adds, START, END, *RESID, series=["not_a_var"]
        )
    with pytest.raises(ValueError, match="coverage"):
        model.stochsim_bands(
            2, with_adds, START, END, *RESID, coverage=(68.0, 120.0)
        )

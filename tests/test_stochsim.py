import pandas as pd
import pytest

from frbus.exceptions import ConvergenceError


def test_stochastic_shock_inventory_is_parsed(model):
    assert model.stoch_shocks
    assert set(model.stoch_shocks) <= set(model.endo_names)


def test_stochsim_is_seeded_and_preserves_failed_draws(model, longbase, monkeypatch):
    start, end = pd.Period("2026Q1"), pd.Period("2026Q2")
    with_adds = model.init_trac("2000Q1", end, longbase)
    calls = []

    def fake_solve(simstart, simend, scenario, options=None):
        calls.append(scenario.loc[start:end, [f"{model.stoch_shocks[0]}_trac"]].copy())
        if len(calls) == 2:
            raise ConvergenceError("deliberate failed replication")
        return scenario

    monkeypatch.setattr(model, "solve", fake_solve)
    out = model.stochsim(
        3, with_adds, start, end, "2000Q1", "2019Q4", seed=7
    )

    assert len(out) == 3
    assert isinstance(out[0], pd.DataFrame)
    assert out[1].startswith("ConvergenceError:")
    assert isinstance(out[2], pd.DataFrame)


def test_stochsim_propagates_programming_errors(model, longbase, monkeypatch):
    """Only model errors (FrbusError) become failed-draw strings; a bug in
    user or library code must surface, not be swallowed into the output."""
    start, end = pd.Period("2026Q1"), pd.Period("2026Q2")
    with_adds = model.init_trac("2000Q1", end, longbase)

    def broken_solve(simstart, simend, scenario, options=None):
        raise TypeError("programming error, must propagate")

    monkeypatch.setattr(model, "solve", broken_solve)
    with pytest.raises(TypeError, match="must propagate"):
        model.stochsim(2, with_adds, start, end, "2000Q1", "2019Q4", seed=7)


def test_stochsim_validates_arguments(model, longbase):
    with pytest.raises(ValueError, match="positive"):
        model.stochsim(0, longbase, "2026Q1", "2026Q2", "2000Q1", "2019Q4")

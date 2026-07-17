"""Test 1 (hard gate): the tracking invariant.

After ``init_trac``, solving the baseline over 2026Q1-2030Q4 must reproduce
LONGBASE for every endogenous variable to tight tolerance.
"""

import numpy as np
import pandas as pd

START = pd.Period("2026Q1")
END = pd.Period("2030Q4")


def test_tracking_invariant(model, longbase):
    with_adds = model.init_trac(START, END, longbase)
    sim = model.solve(START, END, with_adds)

    base = with_adds.loc[START:END, model.endo_names]
    solved = sim.loc[START:END, model.endo_names]
    abs_err = (solved - base).abs().to_numpy()
    rel_err = abs_err / np.maximum(np.abs(base.to_numpy()), 1.0)

    assert np.nanmax(abs_err) < 1e-8
    assert np.nanmax(rel_err) < 1e-10


def test_init_trac_zero_residuals(model, longbase):
    """With computed tracs, model residuals at the baseline are exactly zero."""
    with_adds = model.init_trac(START, END, longbase)
    data = model._setup(with_adds)
    vals = data.to_numpy(copy=True)
    i = list(data.index).index(START)
    x = vals[i][model._endo_idxs]
    resid = model._feqs(x, vals[: i + 1])
    assert np.max(np.abs(resid)) < 1e-12

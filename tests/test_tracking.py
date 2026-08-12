"""Test 1: the tracking invariant.

After ``init_trac``, solving the baseline over 2026Q1-2030Q4 reproduces
LONGBASE for every endogenous variable to float64 round-off.

READ THIS BEFORE QUOTING THE NUMBER. This is a *software* invariant, not
evidence that the model agrees with the Fed's data. ``init_trac`` defines each
equation's add-factor as minus that equation's residual evaluated at the input
data, so ``solve`` is algebraically the identity on whatever it was tracked to.
The residual left over is pure floating-point non-associativity of
``A - (A - B) - B``, and the Newton solver is additionally warm-started from
the data row it is about to reproduce, so it converges without moving.

``test_tracking_invariant_holds_for_arbitrary_data`` pins this: the identical
gate passes on a scrambled baseline in which every accounting identity and
behavioural relation has been destroyed. Any claim of the form "matches
LONGBASE to 5.6e-17, therefore the economics are right" is unsupported.

The real cross-implementation evidence is Test 2 (tests/test_shock.py):
agreement with the Federal Reserve's own pyfrbus on *shocked* paths, where the
add-factors are held fixed and the solver has genuine work to do.
"""

import numpy as np
import pandas as pd

from frbus import Frbus

from .conftest import MODEL_XML

START = pd.Period("2026Q1")
END = pd.Period("2030Q4")

# The gate as CI asserts it.
ABS_GATE = 1e-8
REL_GATE = 1e-10


def tracking_errors(model, data):
    """Max abs/rel deviation of a tracked baseline solve from its input."""
    with_adds = model.init_trac(START, END, data)
    sim = model.solve(START, END, with_adds)
    base = with_adds.loc[START:END, model.endo_names]
    solved = sim.loc[START:END, model.endo_names]
    abs_err = (solved - base).abs().to_numpy()
    rel_err = abs_err / np.maximum(np.abs(base.to_numpy()), 1.0)
    return np.nanmax(abs_err), np.nanmax(rel_err)


def test_tracking_invariant(model, longbase):
    max_abs, max_rel = tracking_errors(model, longbase)
    assert max_abs < ABS_GATE
    assert max_rel < REL_GATE


def test_tracking_invariant_holds_for_arbitrary_data(longbase):
    """The tracking gate carries no economic information -- pin that.

    Every endogenous series is multiplied by an independent random factor in
    [0.5, 1.5], which destroys every accounting identity (C + I + G + NX no
    longer sums to GDP) and every estimated behavioural relation in the model.
    The tracking gate still passes, because ``init_trac`` simply absorbs the
    resulting residuals into the add-factors.

    If this test ever fails while ``test_tracking_invariant`` passes, the
    invariant has become data-dependent and the add-factor construction has
    changed -- which is worth knowing. It must never be deleted on the grounds
    that "the baseline should not be scrambled": scrambling is the point.
    """
    model = Frbus(str(MODEL_XML))
    rng = np.random.default_rng(0)
    scrambled = longbase.copy()
    endos = model.endo_names
    factors = rng.uniform(0.5, 1.5, size=len(endos))
    scrambled[endos] = scrambled[endos].to_numpy() * factors

    max_abs, max_rel = tracking_errors(model, scrambled)
    assert max_abs < ABS_GATE, (
        f"scrambled-baseline tracking error {max_abs:.3e} exceeded the gate; "
        "the tracking invariant is no longer purely an add-factor identity"
    )
    assert max_rel < REL_GATE


def test_init_trac_zero_residuals(model, longbase):
    """With computed tracs, model residuals at the baseline are exactly zero."""
    with_adds = model.init_trac(START, END, longbase)
    data = model._setup(with_adds)
    vals = data.to_numpy(copy=True)
    i = list(data.index).index(START)
    x = vals[i][model._endo_idxs]
    resid = model._feqs(x, vals[: i + 1])
    assert np.max(np.abs(resid)) < 1e-12


def test_baseline_solve_is_warm_started_at_the_answer(model, longbase):
    """Why the tracked solve costs nothing: the initial guess IS the solution.

    ``solve_periods`` seeds Newton with the current row of the input data, and
    after ``init_trac`` that row already satisfies every equation. So the
    reported 5.6e-17 measures re-evaluation round-off, not solver accuracy.
    """
    with_adds = model.init_trac(START, END, longbase)
    data = model._setup(with_adds)
    vals = data.to_numpy(copy=True)
    i = list(data.index).index(START)
    guess = vals[i][model._endo_idxs].astype(float)  # what solve() starts from
    resid_at_guess = model._feqs(guess, vals[: i + 1])
    # Almost every equation is satisfied bit-exactly before Newton runs at all.
    assert np.sum(resid_at_guess == 0.0) > 0.95 * resid_at_guess.size
    assert np.max(np.abs(resid_at_guess)) < 1e-15

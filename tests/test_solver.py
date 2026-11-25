"""Unit tests for solver and public-API robustness guards."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.sparse import csr_matrix

from frbus import Frbus
from frbus.exceptions import (
    ComputationError,
    ConvergenceError,
    FrbusError,
    MissingDataError,
)
from frbus.solver import _preconditioner, compute_tracs, newton, solver_defaults

REPO = Path(__file__).resolve().parents[1]
MODEL_XML = REPO / "vendor" / "pyfrbus_package" / "models" / "model.xml"


def test_preconditioner_scales_rows():
    jac = csr_matrix(np.array([[2.0, 0.0], [0.0, -4.0]]))
    scale = _preconditioner(jac).toarray()
    assert np.allclose(np.diag(scale), [0.5, 0.25])


def test_preconditioner_rejects_zero_rows():
    jac = csr_matrix(np.array([[1.0, 2.0], [0.0, 0.0]]))
    with pytest.raises(ComputationError, match=r"all-zero rows .* \[1\]"):
        _preconditioner(jac)


def test_reversed_simulation_window_is_rejected(model, longbase):
    """start > end used to surface as 'index 0 is out of bounds ... size 0'."""
    with pytest.raises(ValueError, match="precedes start"):
        model.init_trac(pd.Period("2027Q1"), pd.Period("2026Q1"), longbase)


def test_window_outside_the_data_index_names_the_argument(model, longbase):
    """Out-of-range endpoints used to leak 'Period(...) is not in list'."""
    with pytest.raises(ValueError, match=r"end .* is outside the data index"):
        model.init_trac(pd.Period("2026Q1"), pd.Period("2200Q4"), longbase)
    with pytest.raises(ValueError, match=r"start .* is outside the data index"):
        model.init_trac(pd.Period("1900Q1"), pd.Period("2026Q4"), longbase)


def test_non_numeric_input_is_rejected(model, longbase):
    """An object column silently produced an object-dtype solution frame.

    to_numpy() on a frame with one object column returns an object array, so
    the whole solve runs on Python objects and the caller gets back a frame
    whose comparisons and .abs() no longer behave numerically -- a wrong
    answer that looks like a right one.
    """
    data = longbase.copy()
    data["dfpsrp"] = data["dfpsrp"].astype(object)
    with pytest.raises(FrbusError, match="must be entirely numeric"):
        model.init_trac(pd.Period("2026Q1"), pd.Period("2026Q4"), data)


# --- Newton failure modes, on systems small enough to reason about ----------
#
# The model solves never reach these branches (a FRB/US solve from a tracked
# baseline converges in a few steps), so each is exercised here directly. A
# failure mode that returned a number instead of raising would be a wrong
# answer that looks like a right one.

_EMPTY = np.zeros((1, 1))


def _jac(matrix):
    return lambda x, data: csr_matrix(np.atleast_2d(np.asarray(matrix(x), dtype=float)))


def test_newton_solves_a_small_nonlinear_system():
    """x0**2 = 4 and x0*x1 = 6 from (1, 1): the root is (2, 3)."""
    feqs = lambda x, data: np.array([x[0] ** 2 - 4.0, x[0] * x[1] - 6.0])  # noqa: E731
    fjac = _jac(lambda x: [[2 * x[0], 0.0], [x[1], x[0]]])
    root = newton(feqs, fjac, np.array([1.0, 1.0]), _EMPTY, solver_defaults(None))
    assert root == pytest.approx([2.0, 3.0], abs=1e-10)


def test_newton_raises_when_there_is_no_root():
    """x**2 + 1 has no real root: the iteration must stop at maxiter, loudly."""
    feqs = lambda x, data: np.array([x[0] ** 2 + 1.0])  # noqa: E731
    fjac = _jac(lambda x: [[2 * x[0]]])
    with pytest.raises(ConvergenceError, match="Exceeded maxiter = 7"):
        newton(feqs, fjac, np.array([0.5]), _EMPTY, solver_defaults({"maxiter": 7}))


def test_newton_rejects_a_tiny_step_with_a_large_residual():
    """A step below xtol is not convergence if the equations are not solved.

    The Jacobian here is deliberately wrong (1e12 against a true slope of 0),
    so the first step is 1e-12 while the residual is still 1.
    """
    feqs = lambda x, data: np.array([1.0])  # noqa: E731
    fjac = _jac(lambda x: [[1e12]])
    with pytest.raises(ConvergenceError, match="reached xtol but residual is large"):
        newton(feqs, fjac, np.array([0.0]), _EMPTY, solver_defaults(None))


def test_newton_reports_a_singular_jacobian():
    feqs = lambda x, data: np.array([x[0] + x[1] - 1.0, x[0] + x[1] - 2.0])  # noqa: E731
    fjac = _jac(lambda x: [[1.0, 1.0], [1.0, 1.0]])
    with pytest.raises(ConvergenceError, match="linear solve failed"):
        newton(feqs, fjac, np.array([0.0, 0.0]), _EMPTY, solver_defaults(None))


def test_newton_raises_when_every_damped_step_is_nan():
    """The line search halves the step until it evaluates; it must give up."""

    def feqs(x, data):
        return np.array([1.0]) if x[0] == 0.0 else np.array([np.nan])

    fjac = _jac(lambda x: [[1.0]])
    with pytest.raises(ConvergenceError, match="diverged"):
        newton(feqs, fjac, np.array([0.0]), _EMPTY, solver_defaults(None))


def test_newton_damps_a_step_that_leaves_the_domain():
    """log(x) = 0 from x = 3.5: the full step lands at x = -0.88 and is halved."""
    feqs = lambda x, data: np.array([np.log(x[0])])  # noqa: E731
    fjac = _jac(lambda x: [[1.0 / x[0]]])
    root = newton(feqs, fjac, np.array([3.5]), _EMPTY, solver_defaults(None))
    assert root == pytest.approx([1.0], abs=1e-10)


def test_newton_ftol_stop_takes_one_more_step():
    """With ftol set, the solve stops on the residual and polishes once."""
    feqs = lambda x, data: np.array([x[0] ** 2 - 4.0])  # noqa: E731
    fjac = _jac(lambda x: [[2 * x[0]]])
    loose = solver_defaults({"ftol": 1e-2, "xtol": 1e-300})
    root = newton(feqs, fjac, np.array([3.0]), _EMPTY, loose)
    # The first iterate with |f| < 1e-2 is 2.0006; the polish step lands
    # within 1e-7 of the root, which the residual test alone would not.
    assert abs(root[0] - 2.0) < 1e-6


def test_init_trac_names_a_numerical_failure():
    """A log of a negative number in the data is an error, not a NaN add-factor."""
    vals = np.array([[-1.0, 0.0]])
    feqs = lambda x, data: np.array([np.log(x[0])])  # noqa: E731
    with pytest.raises(ComputationError, match="init_trac"):
        compute_tracs([0], vals, [0], [1], feqs)


# --- public-API guards ------------------------------------------------------


def test_exogenize_rejects_a_name_that_is_not_endogenous(model):
    with pytest.raises(ValueError, match="non-endogenous variables: \\['not_a_variable'\\]"):
        model.exogenize(["not_a_variable"])
    # Nothing was changed by the refused call.
    assert model.endo_names == model._orig_endo_names


def test_missing_model_variable_is_named(longbase):
    """A data frame without a model variable fails with that variable's name."""
    fresh = Frbus(str(MODEL_XML))  # not the shared fixture: setup state changes
    with pytest.raises(MissingDataError, match="xgdp"):
        fresh.init_trac(pd.Period("2026Q1"), pd.Period("2026Q2"), longbase.drop(columns=["xgdp"]))

"""Per-period Newton solver for the stacked nonlinear system."""

from __future__ import annotations

import warnings
from collections.abc import Callable

import numpy as np
from scipy.sparse import csc_matrix, csr_matrix
from scipy.sparse.linalg import splu

from frbus.exceptions import ComputationError, ConvergenceError

DEFAULT_OPTIONS = {
    "xtol": 1e-8,
    "rtol": 5e-4,
    "maxiter": 100,
    "precond": True,
    "debug": False,
}


def solver_defaults(options: dict | None) -> dict:
    out = dict(DEFAULT_OPTIONS)
    if options:
        out.update(options)
    return out


def _preconditioner(jac: csr_matrix) -> csr_matrix:
    """Diagonal row scaling by max abs entry, to improve conditioning."""
    scale = 1.0 / np.ravel(abs(jac).max(axis=1).todense())
    n = jac.shape[0]
    return csr_matrix((scale, (range(n), range(n))), shape=(n, n))


def newton(
    feqs: Callable[[np.ndarray, np.ndarray], np.ndarray],
    fjac: Callable[[np.ndarray, np.ndarray], csr_matrix],
    guess: np.ndarray,
    data: np.ndarray,
    options: dict,
) -> np.ndarray:
    """Damped Newton's method with sparse LU (scipy splu) linear solves."""
    xtol: float = options["xtol"]
    rtol: float = options["rtol"]
    maxiter: int = options["maxiter"]
    precond: bool = options["precond"]
    debug: bool = options["debug"]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fun_val = feqs(guess, data)
        jac = fjac(guess, data)

    for _ in range(maxiter):
        if debug:
            print(f"resid={np.linalg.norm(fun_val)}")

        scale = _preconditioner(jac) if precond else None
        lhs = scale @ jac if scale is not None else jac
        rhs = scale @ -fun_val if scale is not None else -fun_val
        try:
            delta = splu(csc_matrix(lhs)).solve(rhs)
        except RuntimeError as err:  # singular matrix
            raise ConvergenceError(f"Newton solver: linear solve failed ({err})") from None

        # Damped line search: halve the step until the model evaluates cleanly
        alpha = 1.0
        while True:
            guess_tmp = guess + alpha * delta
            with warnings.catch_warnings():
                warnings.filterwarnings("error")
                try:
                    fun_tmp = feqs(guess_tmp, data)
                    jac_tmp = fjac(guess_tmp, data)
                    if not np.any(np.isnan(fun_tmp)) and not np.any(np.isnan(jac_tmp.data)):
                        delta = alpha * delta
                        guess = guess_tmp
                        fun_val = fun_tmp
                        jac = jac_tmp
                        break
                except (RuntimeWarning, FloatingPointError):
                    pass
            alpha /= 2
            if alpha < 1e-5:
                raise ConvergenceError("Newton solver has diverged, no solution found.")

        step = np.linalg.norm(delta)
        if np.isnan(step):
            raise ConvergenceError("Newton solver has diverged, no solution found.")
        if step < xtol:
            resid = np.linalg.norm(fun_val)
            if resid < rtol:
                return guess
            raise ConvergenceError(
                f"Newton solver reached xtol but residual is large; resid = {resid}"
            )

    raise ConvergenceError(f"Exceeded maxiter = {maxiter} in Newton solver")


def solve_periods(
    period_idxs: list[int],
    vals: np.ndarray,
    endo_idxs: list[int],
    feqs: Callable,
    fjac: Callable,
    options: dict,
) -> np.ndarray:
    """Solve the model in-place for each period index in ``period_idxs``."""
    for i in period_idxs:
        current = vals[: i + 1]
        guess = current[-1][endo_idxs].astype(float)
        vals[i, endo_idxs] = newton(feqs, fjac, guess, current, options)
    return vals


def compute_tracs(
    period_idxs: list[int],
    vals: np.ndarray,
    endo_idxs: list[int],
    trac_idxs: list[int],
    feqs: Callable,
) -> np.ndarray:
    """Set tracking residuals so each equation solves to the data (in-place)."""
    vals[np.ix_(period_idxs, trac_idxs)] = 0.0
    for i in period_idxs:
        x = vals[i][endo_idxs]
        data = vals[: i + 1]
        with warnings.catch_warnings():
            warnings.filterwarnings("error")
            try:
                errs = feqs(x, data)
            except RuntimeWarning as war:
                raise ComputationError(f"init_trac: {war.args[0]}") from None
        vals[i, trac_idxs] = -errs
    return vals

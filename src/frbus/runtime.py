"""Compilation of equation and Jacobian strings into fast numeric callables."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.sparse import csr_matrix


def _vmax(*args):
    return max(args)


def _vmin(*args):
    return min(args)


def _ind_ltezero(x):
    return 0 if x > 0 else 1


def _heaviside(x):
    return np.heaviside(x, 0)


def _piecewise(*args):
    for val, cond in args:
        if cond:
            return val
    return np.nan


# Namespace for evaluating model equations and sympy-printed derivatives.
NUMERIC_NS: dict = {
    "__builtins__": {},
    "log": np.log,
    "exp": np.exp,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "sign": np.sign,
    "max": _vmax,
    "min": _vmin,
    "ind_ltezero": _ind_ltezero,
    # sympy-printed names appearing in derivatives
    "Max": _vmax,
    "Min": _vmin,
    "Abs": np.abs,
    "Heaviside": _heaviside,
    "Piecewise": _piecewise,
    "DiracDelta": lambda x: 0.0,
    "nan": np.nan,
}


def compile_equations(xsub_eqs: list[str]) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
    """Compile equations into a single function f(x, data) -> residual array."""
    src = "lambda x, data: np.array([" + ", ".join(xsub_eqs) + "])"
    ns = dict(NUMERIC_NS)
    ns["np"] = np
    return eval(src, ns)  # noqa: S307


def compile_jacobian(
    jac: list[tuple[int, int, str]], size: int
) -> Callable[[np.ndarray, np.ndarray], csr_matrix]:
    """Compile a symbolic Jacobian into a function returning a csr_matrix."""
    ns = dict(NUMERIC_NS)
    rows = np.array([e[0] for e in jac])
    cols = np.array([e[1] for e in jac])
    funs = [eval("lambda x, data: " + e[2], ns) for e in jac]  # noqa: S307

    def eval_jac(x: np.ndarray, data: np.ndarray) -> csr_matrix:
        vals = np.array([f(x, data) for f in funs], dtype=float)
        return csr_matrix((vals, (rows, cols)), shape=(size, size))

    return eval_jac

"""Symbolic differentiation of substituted model equations with sympy.

Equations arrive as python strings in terms of ``x[i]`` and ``data[p,j]``.
We evaluate them in a namespace where ``x`` and ``data`` are containers
returning sympy Symbols named literally ``x[i]`` / ``data[p,j]``; the string
form of any derivative is then directly executable python again.
"""

from __future__ import annotations

import sympy


class _SymVec:
    """1-D container returning symbols named ``name[i]``."""

    def __init__(self, name: str):
        self._name = name

    def __getitem__(self, i: int) -> sympy.Symbol:
        return sympy.Symbol(f"{self._name}[{i}]", real=True)


class _SymMat:
    """2-D container returning symbols named ``name[i,j]``."""

    def __init__(self, name: str):
        self._name = name

    def __getitem__(self, key: tuple[int, int]) -> sympy.Symbol:
        i, j = key
        return sympy.Symbol(f"{self._name}[{i},{j}]", real=True)


def _ind_ltezero(x):
    """Symbolic indicator: 1 if x <= 0 else 0."""
    return sympy.Piecewise((0, x > 0), (1, True))


_SYMBOLIC_NS = {
    "__builtins__": {},
    "x": _SymVec("x"),
    "data": _SymMat("data"),
    "log": sympy.log,
    "exp": sympy.exp,
    "max": sympy.Max,
    "min": sympy.Min,
    "abs": sympy.Abs,
    "ind_ltezero": _ind_ltezero,
}


def to_sympy(xsub_eqs: list[str]) -> list[sympy.Expr]:
    """Convert substituted equation strings to sympy expressions."""
    return [eval(eq, dict(_SYMBOLIC_NS)) for eq in xsub_eqs]  # noqa: S307


def create_jacobian(
    exprs: list[sympy.Expr], rhs: list[set[int]]
) -> list[tuple[int, int, str]]:
    """Analytic Jacobian as a sparse list of (row, col, derivative-string).

    Row i is equation i; columns are the x-indices appearing in it (always
    including i itself, matching pyfrbus, so the diagonal is structurally
    present even when the derivative is zero).
    """
    jac: list[tuple[int, int, str]] = []
    for i, expr in enumerate(exprs):
        for j in sorted(rhs[i] | {i}):
            deriv = sympy.diff(expr, sympy.Symbol(f"x[{j}]", real=True))
            deriv_str = sympy.sstr(deriv)
            if "Derivative" in deriv_str:
                raise RuntimeError(f"Unresolved derivative d(eq {i})/d(x[{j}]): {deriv_str}")
            jac.append((i, j, deriv_str))
    return jac

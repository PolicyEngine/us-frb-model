"""Model-consistent expectations (MCE): a stacked-time Newton solve.

Under MCE some expectation equations contain leads, e.g.
``zrff10 = c1*rff + c2*zrff10(1)``, so period t cannot be solved before
period t+1. Following pyfrbus (User Guide, "MCE Solver Algorithm"), the
model is stacked over the whole simulation window: every equation is
written once per period, all ``n_endo * T`` unknowns are solved together by
one damped Newton iteration with a sparse LU, and leads that run past the
end of the window take their values from the input data (the terminal
condition: ``xgdp(2)`` in the final period reads ``xgdp`` two quarters after
``end``).

The stacked system here is mathematically the one pyfrbus builds, but it is
assembled differently. pyfrbus duplicates the equation text T times
(``rff_1``, ``rff_2``, ...) and differentiates the copies. Here each equation
is compiled once in a period-relative form, ``V[r+o, j]`` = column ``j`` of
the data array at period ``r`` offset by ``o`` (negative = lag, positive =
lead), and evaluated for all periods at once with ``r`` a vector of row
indices. Each Jacobian entry ``d eq_i / d V[r+o, col(k)]`` is differentiated
once and placed in the (t, t+o) block of the stacked Jacobian for every t
with t+o inside the window; references outside the window (history before
``start``, terminal values after ``end``) are data. The compile cost does not
depend on the horizon.
"""

from __future__ import annotations

import functools
import re
import warnings
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import sympy
from scipy.sparse import csr_matrix

from frbus.exceptions import ComputationError, FrbusError
from frbus.lexing import LexedEq

_REF_RE = re.compile(r"V\[r([+-]\d+)?,(\d+)\]")


def _ref(offset: int, col: int) -> str:
    return f"V[r{offset:+d},{col}]" if offset else f"V[r,{col}]"


def rsub(lexed_eq: LexedEq, data_col: dict[str, int]) -> str:
    """Rewrite a lexed equation in period-relative form ``V[r+o, j]``."""
    parts: list[str] = []
    for text, token in lexed_eq:
        parts.append(text)
        if token is not None:
            name, lag = token
            parts.append(_ref(lag, data_col[name]))
    return "".join(parts)


# ----------------------------------------------------------- numeric namespace


def _vmax(*args):
    return functools.reduce(np.maximum, args)


def _vmin(*args):
    return functools.reduce(np.minimum, args)


def _vpiecewise(*args):
    conds = [np.asarray(c, dtype=bool) for _, c in args]
    vals = [np.asarray(v, dtype=float) for v, _ in args]
    conds, vals = list(np.broadcast_arrays(*conds)), list(np.broadcast_arrays(*vals))
    return np.select(conds, vals, default=np.nan)


VECTOR_NS: dict = {
    "__builtins__": {},
    "np": np,
    "log": np.log,
    "exp": np.exp,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "sign": np.sign,
    "max": _vmax,
    "min": _vmin,
    "ind_ltezero": lambda x: np.where(x > 0, 0.0, 1.0),
    "Max": _vmax,
    "Min": _vmin,
    "Abs": np.abs,
    "Heaviside": lambda x, *_: np.heaviside(x, 0.0),
    "Piecewise": _vpiecewise,
    "DiracDelta": lambda *_: 0.0,
    "nan": np.nan,
    "True": True,
    "False": False,
}


# ---------------------------------------------------------- symbolic namespace


class _Row:
    """Stand-in for the row index ``r`` during symbolic evaluation."""

    def __init__(self, offset: int = 0):
        self.offset = offset

    def __add__(self, k: int) -> _Row:
        return _Row(self.offset + k)

    def __sub__(self, k: int) -> _Row:
        return _Row(self.offset - k)


class _SymData:
    def __getitem__(self, key: tuple[_Row, int]) -> sympy.Symbol:
        row, col = key
        return sympy.Symbol(_ref(row.offset, col), real=True)


def _ind_ltezero(x):
    return sympy.Piecewise((0, x > 0), (1, True))


_SYMBOLIC_NS = {
    "__builtins__": {},
    "V": _SymData(),
    "r": _Row(),
    "log": sympy.log,
    "exp": sympy.exp,
    "max": sympy.Max,
    "min": sympy.Min,
    "abs": sympy.Abs,
    "ind_ltezero": _ind_ltezero,
}


@dataclass
class _Partial:
    eq: int  # equation (= residual) index
    offset: int  # period offset of the differentiated reference
    unknown: int  # index of the endogenous variable referenced
    fn: Callable[[np.ndarray, np.ndarray], np.ndarray]


class StackedSystem:
    """Period-relative equations and Jacobian for a stacked-time solve.

    Parameters
    ----------
    lexed_eqs:
        One lexed equation per endogenous variable, in ``endo_names`` order,
        already in residual form with coefficients filled in.
    endo_names:
        Endogenous variables (the unknowns, one per equation).
    data_columns:
        Column names of the data frame the system is evaluated on.
    """

    def __init__(self, lexed_eqs: list[LexedEq], endo_names: list[str], data_columns: list[str]):
        data_col = {name: i for i, name in enumerate(data_columns)}
        self.endo_cols = np.array([data_col[name] for name in endo_names])
        col_to_endo = {int(c): k for k, c in enumerate(self.endo_cols)}
        self.n = len(endo_names)

        eqs = [rsub(eq, data_col) for eq in lexed_eqs]
        offsets = [int(o) for eq in eqs for o, _ in _REF_RE.findall(eq) if o]
        self.max_lag = max([0] + [-o for o in offsets])
        self.max_lead = max([0] + offsets)

        src = "lambda V, r: [" + ", ".join(eqs) + "]"
        self._feqs = eval(src, dict(VECTOR_NS))  # noqa: S307

        self._partials: list[_Partial] = []
        for i, eq in enumerate(eqs):
            expr = eval(eq, dict(_SYMBOLIC_NS))  # noqa: S307
            refs = {(int(o) if o else 0, int(c)) for o, c in _REF_RE.findall(eq)}
            # Unknowns are endogenous references; always keep the diagonal so
            # the stacked Jacobian is structurally non-singular, as in pyfrbus.
            targets = {(o, col_to_endo[c]) for o, c in refs if c in col_to_endo}
            targets.add((0, i))
            for o, k in sorted(targets):
                sym = sympy.Symbol(_ref(o, int(self.endo_cols[k])), real=True)
                deriv = sympy.sstr(sympy.diff(expr, sym))
                if "Derivative" in deriv:
                    raise ComputationError(
                        f"Unresolved derivative of equation {i} by {sym}: {deriv}"
                    )
                fn = eval("lambda V, r: " + deriv, dict(VECTOR_NS))  # noqa: S307
                self._partials.append(_Partial(i, o, k, fn))

    # ------------------------------------------------------------- evaluation

    def residuals(self, vals: np.ndarray, rows: np.ndarray) -> np.ndarray:
        """Residuals at ``rows``, shape (T, n): row t holds period rows[t]."""
        out = self._feqs(vals, rows)
        return np.stack([np.broadcast_to(np.asarray(e, dtype=float), rows.shape) for e in out], 1)

    def jacobian(self, vals: np.ndarray, rows: np.ndarray) -> csr_matrix:
        """Stacked Jacobian; unknown (t, k) and equation (t, i) map to t*n + k / t*n + i."""
        T, n = len(rows), self.n
        t = np.arange(T)
        r_idx, c_idx, v_all = [], [], []
        for p in self._partials:
            ok = (t + p.offset >= 0) & (t + p.offset < T)
            if not ok.any():
                continue
            v = np.broadcast_to(np.asarray(p.fn(vals, rows), dtype=float), rows.shape)
            r_idx.append(t[ok] * n + p.eq)
            c_idx.append((t[ok] + p.offset) * n + p.unknown)
            v_all.append(v[ok])
        size = T * n
        return csr_matrix(
            (np.concatenate(v_all), (np.concatenate(r_idx), np.concatenate(c_idx))),
            shape=(size, size),
        )

    # ---------------------------------------------------------------- drivers

    def check_window(self, rows: np.ndarray, n_rows: int) -> None:
        if rows[0] - self.max_lag < 0:
            raise ValueError(f"MCE solve needs {self.max_lag} quarters of history before start")
        if rows[-1] + self.max_lead >= n_rows:
            raise ValueError(
                f"MCE terminal condition needs {self.max_lead} quarters of data after end; "
                "the input data ends too early"
            )

    def compute_tracs(self, vals: np.ndarray, rows: np.ndarray, trac_cols: np.ndarray):
        """Tracking residuals with leads at their data values (in-place)."""
        self.check_window(rows, vals.shape[0])
        vals[np.ix_(rows, trac_cols)] = 0.0
        with warnings.catch_warnings():
            warnings.filterwarnings("error")
            try:
                errs = self.residuals(vals, rows)
            except (RuntimeWarning, FloatingPointError) as war:
                raise ComputationError(f"init_trac (MCE): {war}") from None
        vals[np.ix_(rows, trac_cols)] = -errs
        return vals

    def solve(self, vals: np.ndarray, rows: np.ndarray, newton: Callable, options: dict):
        """Solve all periods in ``rows`` simultaneously (in-place)."""
        self.check_window(rows, vals.shape[0])
        T, n = len(rows), self.n
        block = np.ix_(rows, self.endo_cols)
        work = vals.copy()

        def feqs(x, _):
            work[block] = x.reshape(T, n)
            return self.residuals(work, rows).ravel()

        def fjac(x, _):
            work[block] = x.reshape(T, n)
            return self.jacobian(work, rows)

        guess = vals[block].astype(float).ravel()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            start_resid = feqs(guess, None)
        if not np.all(np.isfinite(start_resid)):
            bad = np.flatnonzero(~np.isfinite(start_resid.reshape(T, n)).all(axis=0))
            raise FrbusError(
                "MCE solve: residuals are not finite at the starting guess for "
                f"equation indices {bad.tolist()[:20]} (missing data or terminal values?)"
            )
        x = newton(feqs, fjac, guess, None, options)
        vals[block] = x.reshape(T, n)
        return vals

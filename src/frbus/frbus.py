"""The Frbus model class: parse, track, and solve the FRB/US model."""

from __future__ import annotations

import pandas as pd

from frbus import equations, lexing, runtime, solver, symbolic
from frbus.exceptions import MissingDataError
from frbus.parse import ModelSpec, parse_model


class Frbus:
    """FRB/US model with VAR (backward-looking) expectations.

    Parameters
    ----------
    filepath:
        Path to a FRB/US ``model.xml`` file.
    mce:
        MCE (rational expectations) variant selector. Not implemented; must
        be None.
    """

    def __init__(self, filepath: str, mce: str | None = None):
        if mce is not None:
            raise NotImplementedError(
                "MCE (model-consistent expectations) equations are not implemented; "
                "only VAR (backward-looking) expectations are supported"
            )
        spec: ModelSpec = parse_model(filepath)
        self.spec = spec
        self.endo_names: list[str] = list(spec.endo_names)

        # Append tracking residual (add-factor) to every equation: lhs = rhs + <endo>_trac
        eqs = [
            eq + f"+{endo}_trac"
            for eq, endo in zip(spec.equations, self.endo_names, strict=True)
        ]

        # Exogenous variables: those used in equations, plus _aerr and _trac terms
        used_exos = [exo for exo in spec.exo_names if any(exo in eq for eq in eqs)]
        self.exo_names: list[str] = (
            used_exos
            + [f"{endo}_aerr" for endo in self.endo_names]
            + [f"{endo}_trac" for endo in self.endo_names]
        )

        # Flip to residual form and substitute coefficient values
        flipped = [equations.flip_equals(eq) for eq in eqs]
        filled = equations.fill_constants(flipped, spec.constants)
        self._lexed_eqs = lexing.lex_eqs(filled)
        self._orig_lexed_eqs = list(self._lexed_eqs)
        self._orig_endo_names = list(self.endo_names)
        self._orig_exo_names = list(self.exo_names)

        # Solve-time state (depends on DataFrame column layout)
        self._data_varnames: list[str] = []
        self._exoglist: set[str] = set()
        self._stale = True

    # ------------------------------------------------------------------ setup

    def exogenize(self, exoglist: list[str]) -> None:
        """Turn the listed endogenous variables into exogenous variables.

        The full set of desired exogenized variables must be passed at once;
        each call replaces the previous list.
        """
        unknown = set(exoglist) - set(self._orig_endo_names)
        if unknown:
            raise ValueError(f"Cannot exogenize non-endogenous variables: {sorted(unknown)}")
        self._exoglist = set(exoglist)
        self.endo_names = [e for e in self._orig_endo_names if e not in self._exoglist]
        self._lexed_eqs = [
            eq
            for eq, endo in zip(self._orig_lexed_eqs, self._orig_endo_names, strict=False)
            if endo not in self._exoglist
        ]
        self.exo_names = self._orig_exo_names + sorted(self._exoglist)
        self._stale = True

    def _ensure_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of ``data`` with zero-filled _aerr/_trac columns added."""
        data = data.copy()
        missing = [
            name
            for endo in self.endo_names
            for name in (f"{endo}_aerr", f"{endo}_trac")
            if name not in data.columns
        ]
        if missing:
            zeros = pd.DataFrame(0.0, index=data.index, columns=missing)
            data = pd.concat([data, zeros], axis=1)
        return data

    def _setup(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data and (re)compile equations/Jacobian if the layout changed."""
        data = self._ensure_columns(data)
        if not self._stale and self._data_varnames == list(data.columns):
            return data

        self._data_varnames = list(data.columns)
        data_col = {name: i for i, name in enumerate(data.columns)}
        endo_idx = {name: i for i, name in enumerate(self.endo_names)}
        is_exo = {name: False for name in self.endo_names}
        is_exo.update({name: True for name in self.exo_names})
        try:
            self._endo_idxs = [data_col[name] for name in self.endo_names]
            self._trac_idxs = [data_col[f"{endo}_trac"] for endo in self.endo_names]
            xsub_eqs = [
                lexing.xsub(eq, is_exo, data_col, endo_idx) for eq in self._lexed_eqs
            ]
        except KeyError as err:
            raise MissingDataError(err.args[0]) from None

        self._feqs = runtime.compile_equations(xsub_eqs)
        exprs = symbolic.to_sympy(xsub_eqs)
        jac = symbolic.create_jacobian(exprs, equations.rhs_endos(xsub_eqs))
        self._fjac = runtime.compile_jacobian(jac, len(xsub_eqs))
        self._stale = False
        return data

    @staticmethod
    def _period_idxs(start, end, data: pd.DataFrame) -> list[int]:
        periods = pd.period_range(start, end, freq="Q")
        index = list(data.index)
        return list(range(index.index(periods[0]), index.index(periods[-1]) + 1))

    # ------------------------------------------------------------------- api

    def init_trac(self, start, end, input_data: pd.DataFrame) -> pd.DataFrame:
        """Compute tracking residuals so the model solves to ``input_data``.

        Returns a copy of ``input_data`` with ``<endo>_trac`` columns filled
        over ``start``..``end`` (inclusive) such that ``solve`` reproduces the
        input trajectories.
        """
        data = self._setup(input_data)
        idxs = self._period_idxs(start, end, data)
        vals = data.to_numpy(copy=True)
        vals = solver.compute_tracs(idxs, vals, self._endo_idxs, self._trac_idxs, self._feqs)
        return pd.DataFrame(vals, index=data.index, columns=data.columns)

    def solve(
        self, start, end, input_data: pd.DataFrame, options: dict | None = None
    ) -> pd.DataFrame:
        """Solve the model per-period over ``start``..``end`` (inclusive)."""
        opts = solver.solver_defaults(options)
        data = self._setup(input_data)
        idxs = self._period_idxs(start, end, data)
        vals = data.to_numpy(copy=True)
        vals = solver.solve_periods(idxs, vals, self._endo_idxs, self._feqs, self._fjac, opts)
        return pd.DataFrame(vals, index=data.index, columns=data.columns)

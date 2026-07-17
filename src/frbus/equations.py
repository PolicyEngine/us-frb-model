"""Equation string transformations."""

from __future__ import annotations

import re

from frbus.exceptions import InvalidModelError

_CONST_RE = re.compile(r"\by_\w+_\d+\b")


def flip_equals(eq: str) -> str:
    """Turn ``lhs = rhs`` into an expression ``rhs - (lhs)`` that equals zero."""
    lhs, rhs = eq.split("=", 1)
    return f"{rhs}-({lhs})"


def fill_constants(eqs: list[str], constants: dict[str, float]) -> list[str]:
    """Replace coefficient names (``y_xgdp_3``) with their numeric values."""

    def repl(m: re.Match) -> str:
        try:
            return repr(constants[m.group(0)])
        except KeyError:
            raise InvalidModelError(f"Constant not found: {m.group(0)}") from None

    return [_CONST_RE.sub(repl, eq) for eq in eqs]


def rhs_endos(xsub_eqs: list[str]) -> list[set[int]]:
    """For each substituted equation, the set of x-indices appearing in it."""
    return [{int(i) for i in re.findall(r"x\[(\d+)\]", eq)} for eq in xsub_eqs]

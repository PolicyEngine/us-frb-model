"""Lexing of model equations.

Equations are split into alternating (text, token) pairs where a token is a
variable reference ``(name, lag)`` -- e.g. ``rff(-1)`` lexes to ``("rff", -1)``.
Supported function names (log, exp, ...) are kept as plain text.

The substitution step (:func:`xsub`) rewrites each equation in terms of

- ``x[i]``: contemporaneous endogenous variable i (the solver unknowns), and
- ``data[p, j]``: column j of the historical data array, where the data array
  passed at runtime ends at the period being solved (so ``data[-1, j]`` is the
  current period and a lag of k periods is ``data[-1 - k, j]``).
"""

from __future__ import annotations

import re

from frbus.parse import SUPPORTED_FUNCTIONS

Token = tuple[str, int] | None
LexedEq = list[tuple[str, Token]]

# Matches identifiers like rff, rff(-1), rff(1); groups: prefix, name, lag, rest
_IDENT_RE = re.compile(r"(.*?)\b([a-z]\w+)(?:\((-?\d+)\))?(?!\w)(.*)")


def lex_eq(eq: str) -> LexedEq:
    """Lex one equation into (text, token) pairs; the final pair has token None."""
    output: LexedEq = []
    fn_text = ""  # accumulates text when the identifier is a function name
    m = _IDENT_RE.match(eq)
    while m:
        prefix, name, lag, rest = m.group(1), m.group(2), m.group(3), m.group(4)
        if name in SUPPORTED_FUNCTIONS:
            # Not a variable: keep as text (a lag here would be a parenthesized arg)
            fn_text += prefix + (f"{name}({lag})" if lag else name)
        else:
            output.append((fn_text + prefix, (name, int(lag) if lag else 0)))
            fn_text = ""
        m = _IDENT_RE.match(rest)
    output.append((fn_text + rest, None))
    return output


def lex_eqs(eqs: list[str]) -> list[LexedEq]:
    return [lex_eq(eq) for eq in eqs]


def xsub(
    lexed_eq: LexedEq,
    is_exo: dict[str, bool],
    data_col: dict[str, int],
    endo_idx: dict[str, int],
) -> str:
    """Rewrite a lexed equation in terms of ``x[i]`` and ``data[p, j]``."""
    parts: list[str] = []
    for text, token in lexed_eq:
        parts.append(text)
        if token is None:
            continue
        name, lag = token
        if lag < 0:
            parts.append(f"data[{lag - 1},{data_col[name]}]")
        elif lag > 0:
            raise NotImplementedError(
                f"Lead {name}({lag}): MCE (forward-looking) equations are not supported"
            )
        elif is_exo[name]:
            parts.append(f"data[-1,{data_col[name]}]")
        else:
            parts.append(f"x[{endo_idx[name]}]")
    return "".join(parts)

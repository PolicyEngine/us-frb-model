#!/usr/bin/env bash
# Regenerate tests/data/vendor_shock_2026q1_2030q4.csv by running the Fed's own
# pyfrbus (vendor/pyfrbus_package) on the standard monetary-policy shock.
#
# The vendor package targets Python 3.9-era dependencies (sympy==1.3,
# scikit-umfpack). This script installs a PATCHED COPY in a throwaway venv:
#   1. setup.py: drop the scikit-umfpack dependency and the sympy==1.3 pin;
#      declare packages=["pyfrbus"] for modern setuptools.
#   2. newton.py: replace `from scikits import umfpack` with a shim whose
#      spsolve uses scipy.sparse.linalg.splu (identical results; umfpack is
#      just a faster LU).
#   3. symbolic.py: in the sympy fallback of take_symengine_partial, convert
#      the symengine expression via `._sympy_()` first. Modern symengine
#      (>=0.9) returns unresolved `Derivative(max(...))` for Max/Min and the
#      vendor's plain `sympy.diff(eq, ...)` no longer converts the expression,
#      leaving `Derivative` in Jacobian entries. With `._sympy_()` sympy
#      differentiates Max itself (yielding Heaviside), which is exactly what
#      the vendor code obtained under sympy 1.3.
#   4. pandas is pinned <2 (vendor writes into read-only DataFrame buffers).
# vendor/ itself is never modified.
#
# Usage: generate_vendor_reference.sh [OUTPUT_CSV]
#   OUTPUT_CSV defaults to tests/data/vendor_shock_2026q1_2030q4.csv (the
#   committed reference). CI passes a scratch path instead so it can compare a
#   FRESHLY generated vendor solution against this implementation without
#   touching the committed anchor.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$REPO/tests/data/vendor_shock_2026q1_2030q4.csv}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

cp -R "$REPO/vendor/pyfrbus_package" "$WORK/pyfrbus_ref"
chmod -R u+w "$WORK/pyfrbus_ref"
cd "$WORK/pyfrbus_ref"

python3 - <<'EOF'
# Patch 1: setup.py
s = open('setup.py').read()
s = s.replace('"scikit-umfpack",', '').replace('"sympy==1.3"', '"sympy"')
s = s.replace('setup(', 'setup(\n    packages=["pyfrbus"],', 1)
open('setup.py', 'w').write(s)

# Patch 2: newton.py umfpack shim
s = open('pyfrbus/newton.py').read()
s = s.replace(
    "from scikits import umfpack",
    "from scipy.sparse import csc_matrix as _csc\n"
    "from scipy.sparse.linalg import splu as _splu\n\n\n"
    "class _Umfpack:\n"
    "    @staticmethod\n"
    "    def spsolve(A, b):\n"
    "        return _splu(_csc(A)).solve(b)\n\n\n"
    "umfpack = _Umfpack()",
)
open('pyfrbus/newton.py', 'w').write(s)

# Patch 3: symbolic.py sympy fallback via ._sympy_()
s = open('pyfrbus/symbolic.py').read()
s = s.replace(
    "deriv = str(sympy.diff(eq, w_resp_to))",
    "deriv = str(sympy.diff(eq._sympy_(), sympy.Symbol(str(w_resp_to))))",
)
s = s.replace(
    "deriv = str(sympy.diff(eq, sympy.symbols(str(w_resp_to), real=True)))",
    "deriv = str(sympy.diff(eq._sympy_(), sympy.symbols(str(w_resp_to), real=True)))",
)
open('pyfrbus/symbolic.py', 'w').write(s)
EOF

uv venv "$WORK/venv" -p 3.11
uv pip install -p "$WORK/venv/bin/python" "$WORK/pyfrbus_ref" "pandas==1.5.3" "numpy<2"

cd "$REPO"
OUT="$OUT" "$WORK/venv/bin/python" - <<'EOF'
import os

import pandas as pd
from pyfrbus.frbus import Frbus
from pyfrbus.load_data import load_data

data = load_data("vendor/data_only_package/LONGBASE.TXT")
model = Frbus("vendor/pyfrbus_package/models/model.xml")
start, end = pd.Period("2026Q1"), pd.Period("2030Q4")
data.loc[start:end, "dfpdbt"] = 0
data.loc[start:end, "dfpsrp"] = 1
with_adds = model.init_trac(start, end, data)
with_adds.loc[start, "rffintay_aerr"] += 1
sim = model.solve(start, end, with_adds, options={"newton": "newton", "xtol": 1e-8})
out = os.environ["OUT"]
sim.loc[start:end, model.endo_names].to_csv(out)
print(f"wrote {out}")
EOF

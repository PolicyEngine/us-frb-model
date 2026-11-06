#!/usr/bin/env bash
# Regenerate the vendor reference for the 2022-23 tightening episode
# (scripts/episode_2022_tightening.py, counterfactual A) by running the
# Board's pyfrbus from vendor/pyfrbus_package, patched exactly as in
# scripts/generate_vendor_reference.sh (that file documents the patches).
#
# Writes all endogenous variables over 2022Q1-2025Q4 to
#   <outdir>/vendor_episode_2022_hist.csv  history run (rff on realised path)
#   <outdir>/vendor_episode_2022_cf.csv    funds rate held at rffmin
# Default outdir: tests/data. Gated by
# tests/test_inflation_transmission.py::test_episode_matches_vendor_pyfrbus.
#
# Usage: generate_vendor_episode_reference.sh [OUTDIR]
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="${1:-$REPO/tests/data}"
mkdir -p "$OUTDIR"
OUTDIR="$(cd "$OUTDIR" && pwd)"
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
OUTDIR="$OUTDIR" "$WORK/venv/bin/python" - <<'EOF'
import os

import pandas as pd
from pyfrbus.frbus import Frbus
from pyfrbus.load_data import load_data

# Same closure as scripts/episode_2022_tightening.py::_frame (variant A).
START, END = pd.Period("2022Q1"), pd.Period("2025Q4")
longbase = load_data("vendor/data_only_package/LONGBASE.TXT")
data = longbase.copy()
w = slice(START, END)
for name, value in {"dfpex": 1, "dfpsrp": 0, "dfpdbt": 0, "dmpintay": 0, "dmpex": 1}.items():
    data.loc[w, name] = value
data.loc[w, "rfffix"] = data.loc[w, "rff"]
model = Frbus("vendor/pyfrbus_package/models/model.xml")
base = model.init_trac(START, END, data)
opts = {"newton": "newton", "xtol": 1e-8}
hist = model.solve(START, END, base, options=opts)
cf_in = base.copy()
cf_in.loc[w, "rfffix"] = longbase.loc[w, "rffmin"]
cf = model.solve(START, END, cf_in, options=opts)
out = os.environ["OUTDIR"]
hist.loc[w, model.endo_names].to_csv(f"{out}/vendor_episode_2022_hist.csv")
cf.loc[w, model.endo_names].to_csv(f"{out}/vendor_episode_2022_cf.csv")
print(f"wrote vendor episode reference to {out}")
EOF

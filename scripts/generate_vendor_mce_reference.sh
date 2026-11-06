#!/usr/bin/env bash
# Generate a vendor reference for the MCE (model-consistent expectations)
# solve by running the Board's own pyfrbus (vendor/pyfrbus_package) with
# Frbus(model.xml, mce=MCE) on the standard 100bp monetary shock of
# scripts/scenarios.py over 2026Q1-2030Q4, Newton at xtol=1e-8.
#
# The vendor copy is patched exactly as in scripts/generate_vendor_reference.sh
# (that file documents the four patches); vendor/ itself is never modified.
# The vendor bakes MCE terminal values (leads past END) from the input data
# when the stacked system is first set up; a fresh Frbus is built per run, so
# the terminals are LONGBASE after END, which is what this implementation reads.
#
# Usage: generate_vendor_mce_reference.sh OUTPUT_CSV MCE [XTOL] [MAXITER]
#   MCE is one of mcap, wp, mcap+wp, all. XTOL (Newton step tolerance)
#   defaults to 1e-8 and MAXITER to pyfrbus's 50. Under mce="wp" the vendor's
#   Newton steps crawl at ~1.3e-8 and it raises after 50 iterations; with
#   MAXITER=2000 it converges at xtol=1e-8 in ~50s (stacked residual 2.4e-10),
#   so CI passes 2000 for wp. The committed wp reference uses 1e-8 / 2000;
#   stopping it at 3e-8 or 1e-7 moves it by < 1e-8.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$1"
MCE="$2"
XTOL="${3:-1e-8}"
MAXITER="${4:-50}"
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
OUT="$OUT" MCE="$MCE" XTOL="$XTOL" MAXITER="$MAXITER" "$WORK/venv/bin/python" - <<'EOF'
import os
import sys
import time

import pandas as pd
from pyfrbus.frbus import Frbus
from pyfrbus.load_data import load_data

sys.path.insert(0, "scripts")
from scenarios import END, START, apply_shock, set_policy  # noqa: E402

mce = os.environ["MCE"]
data = load_data("vendor/data_only_package/LONGBASE.TXT")
model = Frbus("vendor/pyfrbus_package/models/model.xml", mce=mce)
start, end = pd.Period(START), pd.Period(END)
set_policy("monetary", data, start, end)
t0 = time.time()
with_adds = model.init_trac(start, end, data)
apply_shock("monetary", with_adds, start, end)
sim = model.solve(
    start,
    end,
    with_adds,
    options={
        "newton": "newton",
        "xtol": float(os.environ["XTOL"]),
        "maxiter": int(os.environ["MAXITER"]),
    },
)
out = os.environ["OUT"]
sim.loc[start:end, model.orig_endo_names].to_csv(out)
print(f"wrote {out} (mce={mce}, xtol={os.environ['XTOL']}, maxiter={os.environ['MAXITER']}, {time.time() - t0:.0f}s)")
EOF

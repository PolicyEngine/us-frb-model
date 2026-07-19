"""Gate: the committed vendor reference has not drifted from the vendor package.

``tests/data/vendor_shock_2026q1_2030q4.csv`` is a fixed anchor for the
cross-validation gate (VALIDATION.md, Test 2). Because it is committed, it
could in principle go stale relative to what ``vendor/pyfrbus_package``
actually produces. This script compares the committed anchor against a
solution generated *now* by the vendor package (path in ``FRESH_VENDOR_CSV``,
written by ``scripts/generate_vendor_reference.sh``).

Tolerances
----------
The two solutions come from the same vendor source but different dependency
builds (BLAS, scipy, symengine), so they agree only at solver-tolerance scale
rather than bit-for-bit. VALIDATION.md records that even the Fed's own
pyfrbus 1.0.0 and 1.1.1 releases differ from each other by 1.3e-8 abs /
1.3e-7 rel on this experiment; a regeneration on a different machine was
observed at 1.0e-8 abs / 1.0e-7 rel. The gates below sit an order of
magnitude above that noise floor, so they catch a semantic change in the
vendor solution while tolerating build-to-build jitter.

Do not loosen these to make a build pass -- a failure here means the committed
reference no longer represents the vendor package.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

COMMITTED = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "data"
    / "vendor_shock_2026q1_2030q4.csv"
)

ABS_TOL = 1e-6
REL_TOL = 1e-5


def main() -> int:
    fresh_path = os.environ.get("FRESH_VENDOR_CSV")
    if not fresh_path:
        print("FRESH_VENDOR_CSV is not set; run generate_vendor_reference.sh first")
        return 2

    committed = pd.read_csv(COMMITTED, index_col=0)
    fresh = pd.read_csv(fresh_path, index_col=0)

    if list(committed.columns) != list(fresh.columns):
        missing = set(committed.columns) ^ set(fresh.columns)
        print(f"FAIL: endogenous variable set changed; symmetric difference {missing}")
        return 1
    if committed.shape != fresh.shape:
        print(f"FAIL: shape {committed.shape} (committed) vs {fresh.shape} (fresh)")
        return 1

    abs_diff = (committed - fresh).abs().to_numpy()
    rel_diff = abs_diff / np.maximum(np.abs(committed.to_numpy()), 1e-8)
    max_abs = float(np.nanmax(abs_diff))
    max_rel = float(np.nanmax(rel_diff))

    worst = committed.columns[np.nanargmax(np.nanmax(abs_diff, axis=0))]
    print(f"committed vs freshly generated vendor solution ({committed.shape})")
    print(f"  max abs diff: {max_abs:.3e}  (gate < {ABS_TOL:.0e}), worst var {worst}")
    print(f"  max rel diff: {max_rel:.3e}  (gate < {REL_TOL:.0e})")

    if max_abs >= ABS_TOL or max_rel >= REL_TOL:
        print("FAIL: committed reference has drifted from vendor/pyfrbus_package.")
        print("Regenerate it with scripts/generate_vendor_reference.sh and review")
        print("the diff -- do NOT raise these tolerances.")
        return 1

    print("OK: committed reference still matches the vendor package.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

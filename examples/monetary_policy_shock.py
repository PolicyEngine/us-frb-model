"""Demo: 100bp federal funds rate shock (mirrors vendor pyfrbus demos/example1.py).

Run from the repo root:  python examples/monetary_policy_shock.py
"""

from pathlib import Path

import pandas as pd

from frbus import Frbus, load_data

REPO = Path(__file__).resolve().parents[1]

data = load_data(str(REPO / "vendor" / "data_only_package" / "LONGBASE.TXT"))
model = Frbus(str(REPO / "vendor" / "pyfrbus_package" / "models" / "model.xml"))

start, end = pd.Period("2026Q1"), pd.Period("2030Q4")

# Standard configuration: surplus-ratio targeting for fiscal policy
data.loc[start:end, "dfpdbt"] = 0
data.loc[start:end, "dfpsrp"] = 1

# Add-factor the model so the baseline solves to itself
with_adds = model.init_trac(start, end, data)

# 100 basis point monetary policy shock
with_adds.loc[start, "rffintay_aerr"] += 1
sim = model.solve(start, end, with_adds)

print("Deviation from baseline after a 100bp funds rate shock:")
out = pd.DataFrame(
    {
        "rff (pp)": sim.loc[start:end, "rff"] - with_adds.loc[start:end, "rff"],
        "xgdp (%)": 100 * (sim.loc[start:end, "xgdp"] / with_adds.loc[start:end, "xgdp"] - 1),
        "lur (pp)": sim.loc[start:end, "lur"] - with_adds.loc[start:end, "lur"],
        "picxfe (pp)": sim.loc[start:end, "picxfe"] - with_adds.loc[start:end, "picxfe"],
    }
)
print(out.round(4).to_string())

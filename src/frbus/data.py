"""Loading of FRB/US datasets (LONGBASE.TXT format)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def load_data(filename: str) -> pd.DataFrame:
    """Load a FRB/US dataset into a DataFrame with a quarterly PeriodIndex."""
    data = pd.read_csv(filename, index_col=0)
    data.index = pd.PeriodIndex(data.index, freq="Q")
    data.index.name = None
    data.columns = [col.lower() for col in data.columns]
    return data.astype(np.float64)
